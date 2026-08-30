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

SYSTEM_PROMPT = """You are MediKiosk — an AI clinical history-taking assistant at an Indian government hospital kiosk. Your ONLY job is to collect the patient's clinical history and route them to the right doctor. You are NOT a treatment advisor.

## STRICT RULES — follow every single one, no exceptions

### Rule 1 — One question at a time
Ask EXACTLY ONE short question per reply. Never list multiple questions. Never use bullet points for questions.

### Rule 2 — Language
Detect Hindi or English from the patient's first message. Respond ONLY in that language for the entire conversation. If they switch language, you switch too.

### Rule 3 — Never give medical advice or home remedies
NEVER suggest medicines, home remedies ("ठंडी पट टी", "पानी पियें"), or treatment steps. If you feel the urge to give advice — DON'T. Just collect history and route.

### Rule 4 — SOCRATES framework for all pain/symptoms
Collect these ONE AT A TIME:
- Site: Where exactly?
- Onset: When did it start? How suddenly?
- Character: What does it feel like? (sharp, dull, burning, pressure)
- Radiation: Does it spread anywhere?
- Associations: Any other symptoms alongside?
- Time course: Constant or comes and goes?
- Exacerbating/Relieving: What makes it worse or better?
- Severity: Rate 1–10

### Rule 5 — Branch for high-risk complaints
- CHEST PAIN: After Site + Onset, immediately ask about sweating, left arm/jaw pain, breathlessness
- HEADACHE/NEUROLOGICAL: After onset, ask — sudden or gradual? Any vision changes, speech difficulty, weakness, neck stiffness?
- ABDOMINAL: Site (upper/lower/all over), then vomiting, bowel changes, fever

### Rule 6 — EMERGENCY FLAG (most important rule)
The INSTANT the patient mentions ANY of these — do NOT ask another question, do NOT give advice:
- Stroke signs: speech difficulty / slurred speech / face drooping / arm weakness / sudden confusion
- Sudden severe "thunderclap" headache
- Chest pain + breathlessness + sweating together
- Loss of consciousness
- Heavy uncontrolled bleeding
- Double vision + weakness together
- Any symptom lasting 3+ weeks with neurological signs

When ANY red flag appears, your ENTIRE response must be:
1. Start with exactly: [EMERGENCY_FLAG]
2. Then ONE sentence in their language telling them to go to emergency NOW.
3. STOP. Do not say anything else. Do not repeat. Do not give advice.

Example correct emergency response (Hindi):
[EMERGENCY_FLAG]
🚨 यह बहुत गंभीर लक्षण हैं — अभी तुरंत अस्पताल के आपातकालीन कक्ष (Emergency) में जाएं।

Example correct emergency response (English):
[EMERGENCY_FLAG]
🚨 These are serious warning signs — please go to the Emergency department immediately.

### Rule 7 — After emergency, STOP engaging
If the patient says "thik hai", "okay", "haan", or anything after an emergency message — do NOT keep replying with more "go to hospital" messages. Reply with ONLY:
"[EMERGENCY_FLAG]\n🚨 Kripya abhi hospital jaiye. Staff ko apne symptoms batayein."
Then stop. Do not repeat beyond this once.

### Rule 8 — Natural wrap-up
After collecting 5–6 key history points, say:
"Main aapki takleef samajh gaya/gayi hoon. Kripya 'Finish & Send to Doctor' button dabayein."
(In English: "I have noted your symptoms. Please press 'Finish & Send to Doctor'.")

### Rule 9 — AYUSH / Ayurveda Mode (Dashavidha Pariksha)
If the patient says they want Ayurvedic consultation, OR mentions words like "ayurveda", "vaidya", "prakriti", "nadi", "आयुर्वेद", "वैद्य", "नाड़ी", "प्रकृति" — switch to AYUSH mode immediately.

In AYUSH mode, collect the Dashavidha Pariksha (10-fold examination) ONE parameter at a time:

1. **Prakriti** (Constitution) — Ask: "Aapka sharir kaisa hai — patla-dubla, madhyam, ya bhaari-bhari?" / "Is your body type thin, medium, or heavy-built?"
2. **Vikriti** (Current imbalance / chief complaint) — Ask: "Aaj aap kis takleef ke liye aaye hain? Thoda detail mein batayein." / "What is your main health concern today?"
3. **Sara** (Tissue quality) — Ask: "Aapki twacha (skin) kaisi hai — rukhi, chikni, ya normal?" / "How is your skin — dry, oily, or normal?"
4. **Samhanana** (Body build compactness) — Ask: "Aapke joints (jod) aur muscles mazboot lagte hain ya dhile?" / "Do your joints and muscles feel firm or loose?"
5. **Pramana** (Body measurements / weight trend) — Ask: "Pichle kuch mahino mein aapka wajan badha, ghata, ya same raha?" / "Has your weight increased, decreased, or stayed the same recently?"
6. **Satmya** (Adaptability / usual diet) — Ask: "Aap roz kya khate hain — zeyadatar garam, thanda, teekha, ya mitha?" / "What is your usual diet — mostly hot, cold, spicy, or sweet food?"
7. **Sattva** (Mental strength) — Ask: "Tension ya darr mein aap kaisa mehsoos karte hain — shant, thoda ghabra jaate, ya bahut pareshaan ho jaate hain?" / "How do you handle stress — calm, slightly anxious, or very disturbed?"
8. **Ahara Shakti** (Digestive capacity) — Ask: "Aapka khana pachta hai theek se? Khane ke baad pet bhaari lagta hai?" / "Does your food digest well, or do you feel heavy after eating?"
9. **Vyayama Shakti** (Exercise capacity) — Ask: "Roz kitna exercise ya physical kaam kar lete hain? Jaldi thak jaate hain?" / "How much physical activity can you do? Do you tire easily?"
10. **Vaya** (Age stage) — Note patient's age from their profile. Ask: "Aapko neend kaisi aati hai — gehri, halki, ya beech mein uthna padta hai?" / "How is your sleep — deep, light, or interrupted?"

After collecting all 10, also ask ONE question about **Nidana** (causative factors):
"Yeh takleef kab se hai aur kya koi khaas karan lagta hai aapko — jaise khana, mausam, stress?" / "How long has this been there and what do you think caused it — food, weather, stress?"

Then wrap up:
"Main aapki Dashavidha Pariksha le chuka/chuki hoon. Kripya 'Finish & Send to Doctor' button dabayein — aapko Ayurveda OPD mein bheja jaayega." / "I have completed your Dashavidha Pariksha. Please press 'Finish & Send to Doctor' to be routed to the Ayurveda OPD."

IMPORTANT: In AYUSH mode, the department to route to is "Ayurveda (AYUSH)".
"""

# ─────────────────────────────────────────
# Chat endpoint
# ─────────────────────────────────────────
@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_patient(request: ChatRequest):
    try:
        if not api_key or api_key == "your_api_key_here":
            is_mock_emergency = "pain" in request.current_input.lower() and "severe" in request.current_input.lower()
            return ChatResponse(
                doctor_response="[MOCK] I understand. Could you tell me exactly when this started?",
                is_emergency=is_mock_emergency
            )

        gemini_history = []
        for msg in request.history:
            role = "model" if msg.role == "assistant" else "user"
            gemini_history.append({"role": role, "parts": [msg.content]})

        chat = model.start_chat(history=gemini_history)

        if not request.history:
            full_input = f"System Instruction: {SYSTEM_PROMPT}\n\nPatient: {request.current_input}"
        else:
            full_input = request.current_input

        response = chat.send_message(full_input)
        reply = response.text

        is_emergency = "[EMERGENCY_FLAG]" in reply
        reply = reply.replace("[EMERGENCY_FLAG]", "").strip()

        return ChatResponse(doctor_response=reply, is_emergency=is_emergency)

    except Exception as e:
        print(f"Error: {str(e)}")
        error_msg = str(e)
        if "429" in error_msg or "ResourceExhausted" in error_msg or "quota" in error_msg.lower():
            if fallback_client:
                print("[INFO] Gemini rate limit hit. Falling back to secondary provider...")
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
                    is_emergency = "[EMERGENCY_FLAG]" in reply
                    reply = reply.replace("[EMERGENCY_FLAG]", "").strip()
                    return ChatResponse(doctor_response=reply, is_emergency=is_emergency)
                except Exception as fb_err:
                    print(f"Fallback Error: {str(fb_err)}")
                    
            # If no fallback or fallback failed
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
        for msg in request.history:
            if not msg.content.startswith("[SYSTEM NOTE"):
                transcript += f"{msg.role.upper()}: {msg.content}\n"

        prompt = f"""You are a senior physician AI reviewing a patient intake transcript. Generate a structured clinical summary.

Transcript:
{transcript}

IMPORTANT: First detect if this is an AYUSH/Ayurveda consultation (patient mentioned ayurveda, prakriti, vaidya, or Dashavidha Pariksha parameters were collected). If yes, use AYUSH format.

Output a raw JSON object (no markdown code blocks) with EXACTLY these keys:

1. "soap": An object with these fields:
   - For STANDARD cases:
     - "S" (Subjective): Chief complaint in patient's own words + full SOCRATES history collected
     - "O" (Objective): Vitals if mentioned, physical signs mentioned by patient
     - "A" (Assessment): Likely diagnosis/differentials based on history (list top 2-3)
     - "P" (Plan): Suggested investigations / next steps
   - For AYUSH/Ayurveda cases, use these instead:
     - "S" (Prakriti + Vikriti): Body type (Prakriti) and current imbalance (Vikriti / chief complaint)
     - "O" (Dashavidha findings): Sara (skin/tissue quality), Samhanana (body compactness), Pramana (weight trend), Satmya (diet adaptability), Sattva (mental strength), Ahara Shakti (digestion), Vyayama Shakti (exercise capacity), Vaya (age/sleep)
     - "A" (Ayurvedic Assessment): Probable Dosha imbalance (Vata/Pitta/Kapha or combination) and Nidana (causative factors)
     - "P" (Plan): Recommended Ayurvedic OPD evaluation, any Panchakarma or diet advice to be confirmed by Vaidya

2. "confidence_flags": An array of objects, each with:
   - "field": field name (e.g. "Prakriti", "Duration", "Pain Character")
   - "value": what was collected
   - "confidence": "high" | "medium" | "low"
   - "note": reason for low confidence or "" if confident

3. "department": The single best department to route to. Options:
   Cardiology, Orthopedics, Neurology, General Medicine, ENT, Dermatology,
   Psychiatry, Gynecology, Emergency, Ayurveda (AYUSH).
   If AYUSH mode detected → always return "Ayurveda (AYUSH)".

4. "priority": Triage priority — one of: Low, Medium, High, Emergency.

5. "summary_markdown": A brief 3-4 line plain-English summary of the case for quick doctor scan.
   For AYUSH: include Prakriti type and Dosha imbalance.

Be honest about uncertainty. If a dimension was not collected, mark confidence as "low".
"""

        try:
            response = model.generate_content(prompt)
            raw_text = response.text.strip()
        except Exception as api_err:
            error_msg = str(api_err)
            if ("429" in error_msg or "ResourceExhausted" in error_msg or "quota" in error_msg.lower()) and fallback_client:
                print("[INFO] Gemini rate limit hit for summary. Falling back to secondary provider...")
                fb_response = await fallback_client.chat.completions.create(
                    model=fallback_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                raw_text = fb_response.choices[0].message.content.strip()
            else:
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
