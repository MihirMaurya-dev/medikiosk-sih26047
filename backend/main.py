from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import asyncio
import google.generativeai as genai
from openai import AsyncOpenAI
from dotenv import load_dotenv
import json
import uuid
from datetime import datetime
from pathlib import Path

load_dotenv()

app = FastAPI(title="MediKiosk API")

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Gemini (Primary)
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-3.5-flash-lite')

# Configure Fallback (Groq or OpenAI)
fallback_client = None
fallback_model = "llama3-8b-8192" # Default Groq model
if os.getenv("GROQ_API_KEY"):
    fallback_client = AsyncOpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1")
elif os.getenv("OPENAI_API_KEY"):
    fallback_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    fallback_model = "gpt-4o-mini"


# ─────────────────────────────────────────
# Persistent session store — survives server restarts
# Backed by session_data.json in the backend folder
# ─────────────────────────────────────────
SESSION_FILE = Path("session_data.json")

def _load_session() -> dict:
    """Load queue from disk on startup."""
    if SESSION_FILE.exists():
        try:
            data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            return data
        except Exception:
            pass
    return {"queue": {}, "counters": {}}

def _save_session():
    """Write queue to disk after every change."""
    try:
        SESSION_FILE.write_text(
            json.dumps({"queue": PATIENT_QUEUE, "counters": DEPT_COUNTERS}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"[WARN] Could not save session: {e}")

_session = _load_session()
PATIENT_QUEUE: dict = _session["queue"]
DEPT_COUNTERS: dict = _session["counters"]

print(f"[MediKiosk] Session loaded — {len(PATIENT_QUEUE)} patient(s) in queue.")

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    patient_id: str
    history: List[Message]
    current_input: str

class ChatResponse(BaseModel):
    doctor_response: str
    is_emergency: bool

class SummaryRequest(BaseModel):
    patient_id: str
    history: List[Message]

class ApproveRequest(BaseModel):
    token_id: str
    doctor_name: str

import os

def load_prompts():
    prompt_file = os.path.join(os.path.dirname(__file__), "agent.md")
    with open(prompt_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    parts = content.split("---")
    chat_prompt = parts[0].replace("# CHAT_AGENT_PROMPT", "").strip()
    summary_prompt = parts[1].replace("# SUMMARY_AGENT_PROMPT", "").strip()
    return chat_prompt, summary_prompt

SYSTEM_PROMPT, SUMMARY_PROMPT_TEMPLATE = load_prompts()


# ─────────────────────────────────────────
# Chat endpoint
# ─────────────────────────────────────────
@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_patient(request: ChatRequest):
    try:
        if not api_key and not fallback_client:
            is_mock_emergency = "pain" in request.current_input.lower() and "severe" in request.current_input.lower()
            return ChatResponse(
                doctor_response="[MOCK] I understand. Could you tell me exactly when this started?",
                is_emergency=is_mock_emergency
            )

        reply = ""
        # ── Primary: Groq (for fast text) ──
        if fallback_client:
            try:
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                for msg in request.history:
                    messages.append({"role": msg.role, "content": msg.content})
                messages.append({"role": "user", "content": request.current_input})
                
                fb_response = await fallback_client.chat.completions.create(
                    model=fallback_model,
                    messages=messages,
                    temperature=0.3
                )
                reply = fb_response.choices[0].message.content
            except Exception as e:
                print(f"[WARN] Groq failed, falling back to Gemini: {e}")
                reply = ""
        
        # ── Fallback: Gemini (if Groq fails or not configured) ──
        if not reply:
            gemini_history = []
            for msg in request.history:
                role = "model" if msg.role == "assistant" else "user"
                gemini_history.append({"role": role, "parts": [msg.content]})
            
            chat = model.start_chat(history=gemini_history)
            full_input = f"System Instruction: {SYSTEM_PROMPT}\n\nPatient: {request.current_input}" if not request.history else request.current_input
            
            response = chat.send_message(full_input)
            reply = response.text

        is_emergency = "[EMERGENCY_FLAG]" in reply
        reply = reply.replace("[EMERGENCY_FLAG]", "").strip()

        return ChatResponse(doctor_response=reply, is_emergency=is_emergency)

    except Exception as e:
        print(f"Error: {str(e)}")
        error_msg = str(e)
        if "429" in error_msg or "ResourceExhausted" in error_msg or "quota" in error_msg.lower():
            return ChatResponse(
                doctor_response="⏳ Server is very busy right now (API rate limit). Please wait about 30 seconds and try again.",
                is_emergency=False
            )
        raise HTTPException(status_code=500, detail=error_msg)



# ─────────────────────────────────────────
# Document scan endpoint
# ─────────────────────────────────────────
@app.post("/api/scan_document")
async def scan_document(file: UploadFile = File(...)):
    try:
        if not api_key or api_key == "your_api_key_here":
            return {"extracted_data": "Mock data: Paracetamol 500mg, 1 tablet twice a day."}

        contents = await file.read()
        image_parts = [{"mime_type": file.content_type, "data": contents}]

        prompt = """You are an expert medical document parser. Read this document and extract key medical information:
        - Document Type
        - Key Diagnoses or Findings
        - Medications (with dosages)
        - Abnormal lab values
        Format as clean bullet points."""

        response = model.generate_content([prompt, image_parts[0]])
        return {"extracted_data": response.text}

    except Exception as e:
        print(f"Error scanning document: {str(e)}")
        error_msg = str(e)
        if "429" in error_msg or "ResourceExhausted" in error_msg or "quota" in error_msg.lower():
            return {"extracted_data": "⏳ OCR Server is currently busy (Rate Limit). Please wait 30 seconds and try scanning again."}
        raise HTTPException(status_code=500, detail=error_msg)


# ─────────────────────────────────────────
# Generate summary + add to queue
# ─────────────────────────────────────────
@app.post("/api/generate_summary")
async def generate_summary(request: SummaryRequest):
    try:
        if not api_key or api_key == "your_api_key_here":
            dept = "Orthopedics"
            DEPT_COUNTERS[dept] = DEPT_COUNTERS.get(dept, 0) + 1
            token_id = str(uuid.uuid4())[:8].upper()
            token_data = {
                "token_id": token_id,
                "abha_id": request.patient_id,
                "department": dept,
                "priority": "High",
                "queue_number": DEPT_COUNTERS[dept],
                "summary_markdown": "## Chief Complaint\nSevere bone pain in left leg.\n\n## HPI\nPain for 3 days, rating 8/10.",
                "status": "Pending",
                "approved_by": None,
                "timestamp": datetime.now().isoformat()
            }
            PATIENT_QUEUE[token_id] = token_data
            return token_data

        transcript = ""
        report_analysis = []
        for msg in request.history:
            if msg.content.startswith("[SYSTEM NOTE: The patient uploaded a medical document"):
                transcript += f"SYSTEM (DOCUMENT OCR): {msg.content}\n"
                report_analysis.append(msg.content.replace("[SYSTEM NOTE: The patient uploaded a medical document. Extracted details: ", "").rstrip("]"))
            elif not msg.content.startswith("[SYSTEM NOTE"):
                transcript += f"{msg.role.upper()}: {msg.content}\n"

        prompt = SUMMARY_PROMPT_TEMPLATE.replace("{transcript}", transcript)

        raw_text = ""
        if fallback_client:
            try:
                fb_response = await fallback_client.chat.completions.create(
                    model=fallback_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                raw_text = fb_response.choices[0].message.content.strip()
            except Exception as e:
                print(f"[WARN] Groq summary failed, falling back to Gemini: {e}")
                
        if not raw_text:
            try:
                response = model.generate_content(prompt)
                raw_text = response.text.strip()
            except Exception as api_err:
                error_msg = str(api_err)
                if ("429" in error_msg or "ResourceExhausted" in error_msg or "quota" in error_msg.lower()) and fallback_client:
                    raise HTTPException(status_code=500, detail="⏳ Both Groq and Gemini failed/busy. Please try again.")
                raise api_err


        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]

        try:
            data = json.loads(raw_text.strip())
        except:
            data = {
                "summary_markdown": raw_text,
                "department": "General Medicine",
                "priority": "Medium"
            }

        # Assign queue number per department
        dept = data.get("department", "General Medicine")
        DEPT_COUNTERS[dept] = DEPT_COUNTERS.get(dept, 0) + 1

        token_id = str(uuid.uuid4())[:8].upper()
        token_data = {
            "token_id": token_id,
            "abha_id": request.patient_id,
            "department": dept,
            "priority": data.get("priority", "Medium"),
            "queue_number": DEPT_COUNTERS[dept],
            "summary_markdown": data.get("summary_markdown", ""),
            "soap": data.get("soap", {}),
            "confidence_flags": data.get("confidence_flags", []),
            "reports": report_analysis,
            "status": "Pending",    # Pending / Approved
            "approved_by": None,
            "timestamp": datetime.now().isoformat()
        }
        PATIENT_QUEUE[token_id] = token_data
        _save_session()   # persist to disk immediately
        return token_data

    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────
# Queue API — used by doctor panel
# ─────────────────────────────────────────
@app.get("/api/queue")
async def get_queue(department: Optional[str] = None):
    """Return all patients in queue, optionally filtered by department."""
    patients = list(PATIENT_QUEUE.values())
    if department:
        patients = [p for p in patients if p["department"].lower() == department.lower()]
    # Sort: Emergency first, then High, then by timestamp
    priority_order = {"Emergency": 0, "High": 1, "Medium": 2, "Low": 3}
    patients.sort(key=lambda x: (priority_order.get(x["priority"], 99), x["timestamp"]))
    return {"queue": patients}


@app.get("/api/token/{token_id}")
async def get_token_status(token_id: str):
    """Patient polls this to check their approval status."""
    token = PATIENT_QUEUE.get(token_id.upper())
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    return token


@app.get("/api/stream/{token_id}")
async def stream_token_status(token_id: str):
    """
    Server-Sent Events endpoint.
    Pushes a JSON update every second until status = Approved, then closes.
    Frontend uses EventSource — no polling delay.
    """
    tid = token_id.upper()

    async def event_generator():
        try:
            while True:
                token = PATIENT_QUEUE.get(tid)
                if not token:
                    yield f"data: {json.dumps({'error': 'not_found'})}\n\n"
                    break
                yield f"data: {json.dumps(token)}\n\n"
                if token.get("status") == "Approved":
                    break          # close the stream — no more events needed
                await asyncio.sleep(1)   # check every 1 second server-side
        except asyncio.CancelledError:
            pass  # client disconnected — clean exit

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disables nginx buffering
        }
    )


@app.post("/api/approve")
async def approve_patient(request: ApproveRequest):
    """Doctor approves a patient. Status changes to Approved."""
    token = PATIENT_QUEUE.get(request.token_id.upper())
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    token["status"] = "Approved"
    token["approved_by"] = request.doctor_name
    _save_session()   # persist approval to disk immediately
    return {"message": "Patient approved", "token": token}


# ─────────────────────────────────────────
# Page routes
# ─────────────────────────────────────────
@app.get("/")
def read_root():
    return FileResponse('static/index.html')

@app.get("/chat")
def read_chat():
    return FileResponse('static/chat.html')

@app.get("/status")
def read_status():
    return FileResponse('static/status.html')

@app.get("/doctor-panel")
def read_doctor_panel():
    return FileResponse('static/doctor_panel.html')

@app.get("/dashboard")
def read_dashboard():
    return FileResponse('static/dashboard.html')
