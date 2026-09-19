# MediKiosk — Detailed Project Draft
## Smart AI-Powered Patient Intake & Triage Kiosk
### Smart India Hackathon 2026 · Team Submission

---

> **One-line pitch:** MediKiosk replaces the paper token + waiting-room confusion at government hospitals with a conversational AI kiosk that takes the patient's full clinical history, scans their documents, generates a SOAP note, and routes them to the right department — before they ever sit in front of the doctor.

---

## 1. Problem Statement

Indian government hospitals face three interconnected bottlenecks at OPD:

| Problem | Impact |
|---|---|
| Doctors spend 3–5 min per patient re-taking basic history | 30–40 patient slots wasted per doctor per day |
| Patients routed to wrong department at registration | Double waiting time, frustrated patients |
| Paper reports and lab results not seen before consultation | Doctor makes decisions without full context |
| No triage — all patients wait the same queue regardless of severity | Emergency cases not fast-tracked |

MediKiosk addresses all four simultaneously through a single kiosk touchpoint placed before the OPD consultation.

---

## 2. What MediKiosk Does — End-to-End Flow

```
Patient arrives at hospital
        │
        ▼
┌─────────────────────────────┐
│  STEP 1: ABHA Authentication│  → Patient enters 14-digit ABHA ID
│  (index.html)               │  → Past medical history auto-loaded from ABDM (simulated)
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  STEP 2: AI Intake Chat     │  → ARIA (AI nurse) asks one question at a time
│  (chat.html)                │  → SOCRATES framework for symptom collection
│                             │  → Voice input (Web Speech API) in Hi/En/Ta/Bn
│                             │  → TTS reads AI replies aloud
│                             │  → Patient can upload reports/prescriptions (OCR)
│                             │  → Emergency red-flag detection → instant alert
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  STEP 3: AI Summary         │  → Groq LLM (primary) generates SOAP note JSON
│  Generation                 │  → Gemini (fallback) if Groq fails
│  (/api/generate_summary)    │  → Department routing + triage priority assigned
│                             │  → Token created, saved to session + disk
└────────────┬────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────────┐
│  STEP 4: Dual-panel waiting                            │
│  Patient → status.html  │  Doctor → doctor_panel.html  │
│  Sees: token #, dept,   │  Sees: live queue, priority  │
│  priority, live update  │  sorted, SOAP + OCR reports  │
│  via Server-Sent Events │  forced to "View Analysis"   │
│                         │  before approving            │
└─────────────────────────┬──────────────────────────────┘
                          │ Doctor clicks Approve
                          ▼
┌─────────────────────────────┐
│  STEP 5: Patient Notified   │  → SSE pushes "Approved" in real-time
│  (status.html)              │  → Green screen flash, large queue number
│                             │  → Instructions: go to [Department] counter
└─────────────────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  STEP 6: Dashboard Review   │  → Doctor/staff reviews full SOAP note
│  (dashboard.html)           │  → Can edit fields (contenteditable)
│                             │  → Confidence flags highlight missing data
│                             │  → "Push to ABDM" writes to patient's ABHA locker (mock FHIR)
└─────────────────────────────┘
```

---

## 3. Technology Stack

### Backend
| Component | Technology | Why |
|---|---|---|
| Web Framework | **FastAPI** (Python) | Async-first, auto OpenAPI docs, SSE support built-in |
| AI Provider (Primary) | **Groq Cloud — `llama-3.1-8b-instant`** | Ultra-low latency (~200ms), free tier, multilingual |
| AI Provider (Vision/Fallback) | **Google Gemini — `gemini-3.5-flash-lite`** | Only model with multimodal (OCR) capability on free tier |
| Data Persistence | **JSON file (`session_data.json`)** | Lightweight, no DB setup needed for hackathon; easily swappable to PostgreSQL |
| Real-time Push | **Server-Sent Events (SSE)** | Native browser support, no WebSocket library needed |
| Environment Config | **python-dotenv** | API keys in `.env`, never committed |
| OCR Pipeline | **Gemini Vision API** | Extracts clinical data from uploaded images/PDFs |
| ABHA/ABDM Mock | **In-memory simulation** | Real ABDM requires production credentials; mock replicates the data model |

### Frontend
| Component | Technology | Why |
|---|---|---|
| Styling | **Tailwind CSS (CDN)** | Utility-first, zero build step — perfect for hackathon speed |
| Typography | **Google Fonts — Inter + JetBrains Mono** | Professional medical-grade look |
| Markdown Rendering | **marked.js** | Renders AI-generated SOAP notes with proper formatting |
| TTS | **Web Speech API (SpeechSynthesis)** | Browser-native, zero cost, multilingual (Hi/En/Ta/Bn) |
| STT (Voice Input) | **Web Speech API (SpeechRecognition)** | Browser-native voice → text → auto-send |
| Real-time Updates | **EventSource (SSE client)** | Patient status page updates without polling |
| No framework | Vanilla JS + HTML | Runs on any device including government kiosk hardware |

---

## 4. AI Pipeline — Detailed

### 4.1 Chat Pipeline (`/api/chat`)

```
Patient message
      │
      ▼
Build message array:
  [SYSTEM PROMPT from agent.md]
+ [Past medical history injection]
+ [Full chatHistory from frontend]
+ [Current user message]
      │
      ▼
Try Groq (llama-3.1-8b-instant)
  → response.choices[0].message.content
      │
  Fails? ──► Try Gemini
            → Build synthetic history format
            → [{"role":"user","parts":[system+history]}, {"role":"model","parts":["Understood"]}, {"role":"user","parts":[current_msg]}]
            → model.generate_content(messages)
      │
      ▼
Check for [EMERGENCY_FLAG] in response
  → If found: is_emergency=True returned to frontend
  → Frontend: red pulsing button + full-screen siren overlay
      │
      ▼
Return {doctor_response, is_emergency} to frontend
```

### 4.2 OCR Pipeline (`/api/scan_document`)

```
Patient uploads image/PDF
      │
      ▼
Backend validation:
  - File type whitelist: jpg, jpeg, png, webp, pdf
  - Size limit: 10MB
  - model not None check
      │
      ▼
Read file bytes → base64 encode
      │
      ▼
Gemini multimodal call:
  prompt = "You are a clinical document reader..."
  model.generate_content([prompt, {"mime_type": ..., "data": base64}])
      │
      ▼
Return extracted_data (OCR text) to frontend
      │
      ▼
Frontend:
  - Displays OCR result as system message
  - Injects into chatHistory as:
    "[SYSTEM NOTE: The patient uploaded a medical document. Extracted details: {text}]"
  - This context flows into ALL future AI responses + the final summary
```

### 4.3 Summary + Triage Pipeline (`/api/generate_summary`)

```
Patient clicks "Finish & Send to Doctor"
      │
      ▼
Backend receives full chatHistory
      │
      ▼
Transcript builder:
  - Regular messages → "USER: ...\nASSISTANT: ..."
  - OCR messages → "SYSTEM (DOCUMENT OCR): ..."
  - Other SYSTEM NOTEs → filtered out
  - report_analysis[] → extracted OCR texts for storage
      │
      ▼
Validate: transcript not empty → else 400
      │
      ▼
Inject transcript into SUMMARY_AGENT_PROMPT template
  (from agent.md, {transcript} placeholder replaced)
      │
      ▼
Try Groq (structured JSON request, temperature=0.2)
  → Expects raw JSON back
      │
  Fails? ──► Try Gemini
            → Same prompt, same JSON expectation
      │
      ▼
JSON parsing:
  - Strip markdown code fences (``` or ```json)
  - json.loads()
  - Except JSONDecodeError → fallback {summary_markdown: raw_text}
      │
      ▼
Department validation:
  - Against VALID_DEPTS whitelist
  - Unknown dept → "General Medicine"
      │
      ▼
Build token_data dict:
  {token_id, abha_id, department, priority, queue_number,
   summary_markdown, soap{S,O,A,P}, confidence_flags[], reports[],
   status:"Pending", approved_by:null, timestamp}
      │
      ▼
PATIENT_QUEUE[token_id] = token_data
DEPT_COUNTERS[dept] += 1
_save_session() → write to session_data.json
      │
      ▼
Return token_data to patient (shown in modal)
```

### 4.4 Doctor Approval Pipeline (`/api/approve`)

```
Doctor opens modal (forced to read SOAP + reports)
      │
      ▼
Clicks "Approve Patient"
      │
      ▼
POST /api/approve {token_id, doctor_name}
      │
      ▼
token_data.status = "Approved"
token_data.approved_by = doctor_name
_save_session()
      │
      ▼
SSE stream for patient's token_id returns:
  data: {"status":"Approved", "approved_by":"Dr. Sharma", ...}
      │
      ▼
Patient's status.html receives SSE event:
  - Green full-screen flash
  - "You're Approved!" card with queue number
  - Instructions to go to department counter
```

### 4.5 Real-time SSE Stream (`/api/stream/{token_id}`)

```python
async def event_stream():
    while True:
        token = PATIENT_QUEUE.get(token_id)
        if not token:
            yield 'data: {"error": "Token not found"}\n\n'; return
        yield f'data: {json.dumps(token)}\n\n'
        if token["status"] == "Approved":
            return  # close stream
        await asyncio.sleep(1)  # poll every 1 second
```

---

## 5. Prompt Architecture (`agent.md`)

The entire AI behavior is controlled by a single `agent.md` file — editable without touching Python code.

### Structure
```
# CHAT_AGENT_PROMPT
[Chat agent instructions]
---
# SUMMARY_AGENT_PROMPT
[Summary/triage agent instructions with {transcript} placeholder]
```

### Chat Agent Design Philosophy (ARIA)
- **Identity**: "Think like a detective, not a receptionist"
- **Core framework**: SOCRATES (Site, Onset, Character, Radiation, Associations, Timing, Exacerbating/Relieving, Severity)
- **Branching logic**: Chest pain → mandatory cardiac questions; Headache → neuro screen; Abdominal → bowel/fever
- **Red-flag interruption**: Instantly halts interview, outputs `[EMERGENCY_FLAG]`, refuses further engagement
- **AYUSH mode**: Switches to Dashavidha Pariksha (10-fold Ayurvedic examination) on trigger words
- **Language lock**: Detects from first message, stays locked — plus 4-language panel support

### Summary Agent Design Philosophy
- **Reader**: Senior consultant physician reviewing in under 30 seconds
- **S**: Verbatim chief complaint + SOCRATES data, explicitly notes uncollected fields
- **O**: Only what was actually observed/mentioned — never fabricated
- **A**: Ranked differentials with reasoning ("1. ACS — rationale. 2. GERD — rationale")
- **P**: Specific investigations ("ECG, Troponin I, CXR PA view") — NOT vague ("cardiac workup")
- **confidence_flags**: Every SOCRATES dimension flagged with high/medium/low + reason for low confidence
- **priority**: Defined logic — Emergency > High (severity ≥8/10 or rapid worsening) > Medium > Low

---

## 6. Frontend Pages & Their Roles

| Page | File | Role |
|---|---|---|
| Login | `index.html` | ABHA ID entry with 14-digit validation, consent checkbox |
| Chat | `chat.html` | ARIA AI interview, voice I/O, OCR upload, TTS, language picker |
| Dashboard | `dashboard.html` | Patient-facing SOAP summary review before doctor sees them |
| Status | `status.html` | Patient waiting screen — live SSE token status |
| Doctor Panel | `doctor_panel.html` | Doctor queue view — priority-sorted cards, full analysis modal, approve |

---

## 7. Data Model

### `token_data` (in-memory + JSON)
```json
{
  "token_id": "A1B2C3D4",
  "abha_id": "12345678901234",
  "department": "Cardiology",
  "priority": "High",
  "queue_number": 3,
  "summary_markdown": "**55-year-old male** presenting with...",
  "soap": {
    "S": "Crushing chest pain radiating to left arm, onset 2 hours ago...",
    "O": "No objective data from kiosk. Requires clinical examination.",
    "A": "1. ACS — substernal pain + radiation + diaphoresis. 2. GERD — less likely.",
    "P": "ECG, Troponin I, CXR PA view — urgent."
  },
  "confidence_flags": [
    {"field": "Radiation", "confidence": "high", "value": "Left arm", "note": ""},
    {"field": "Severity", "confidence": "medium", "value": "8/10", "note": "Patient seemed to underreport"}
  ],
  "reports": ["Report OCR text from uploaded prescription..."],
  "status": "Pending",
  "approved_by": null,
  "timestamp": "2026-09-19T20:00:00"
}
```

### Session File (`session_data.json`)
```json
{
  "queue": { "A1B2C3D4": { ...token_data... } },
  "counters": { "Cardiology": 3, "General Medicine": 12 }
}
```

---

## 8. Security & Reliability Choices

| Concern | Approach |
|---|---|
| API Key exposure | `.env` file, never committed (`.gitignore`) |
| File upload abuse | Whitelist: jpg/png/webp/pdf only, 10MB max |
| AI hallucination of dept | VALID_DEPTS whitelist, unknown → General Medicine |
| Both AI providers failing | Raises HTTP 500 with friendly patient-facing message |
| Empty transcript | Validated before LLM call → HTTP 400 |
| JSON parse failure | Graceful fallback — stores raw text as summary_markdown |
| Session loss on restart | `_save_session()` called on every queue mutation |
| Doctor skipping review | "View Analysis" button is `pointer-events-none`, card click = only entry to modal |

---

## 9. AYUSH Integration

MediKiosk has first-class support for Ayurvedic/AYUSH consultations:

- **Trigger words**: "ayurveda", "vaidya", "prakriti", "nadi", "पंचकर्म", etc.
- **Mode switch**: Full Dashavidha Pariksha (10-parameter Ayurvedic intake)
- **Parameters collected**: Prakriti, Vikriti, Sara, Samhanana, Pramana, Satmya, Sattva, Ahara Shakti, Vyayama Shakti, Vaya + Nidana
- **SOAP relabeling**: S → Prakriti + Vikriti, O → Dashavidha Pariksha, A → Dosha Assessment (Vata/Pitta/Kapha), P → Vaidya Plan
- **Routing**: Always routes to `Ayurveda (AYUSH)` department
- **UI**: Green AYUSH badge shows on doctor panel and dashboard

---

## 10. Multi-language Support

| Language | Voice Input | TTS Output | AI Response | Trigger |
|---|---|---|---|---|
| Hindi | ✅ `hi-IN` | ✅ | ✅ (Devanagari) | Default |
| English | ✅ `en-IN` | ✅ | ✅ | Panel select / `en-IN` |
| Tamil | ✅ `ta-IN` | ✅ (if browser supports) | ✅ (Tamil script) | Panel select |
| Bengali | ✅ `bn-IN` | ✅ (if browser supports) | ✅ (Bengali script) | Panel select |

Language switching injects a `[SYSTEM NOTE]` into `chatHistory` — the AI is instructed to lock to the new language from that point.

---

## 11. Limitations & Future Roadmap

### Current Limitations (Hackathon Scope)
| Limitation | Reason |
|---|---|
| ABDM push is mocked | Real ABDM requires NHA production credentials |
| Session storage is JSON file | No multi-server, no concurrent write safety |
| TTS works best on Chrome/Edge | Web Speech API support varies by browser |
| OCR only via Gemini Vision | Groq doesn't support multimodal yet |
| No authentication for doctor panel | Assumed intranet deployment |

### Roadmap
- [ ] Replace JSON session with PostgreSQL + Redis
- [ ] Real ABDM FHIR integration (PHR app linking)
- [ ] Add NLP intent detection to skip redundant questions
- [ ] Kiosk hardware integration (camera-based document scan, fingerprint for ABHA)
- [ ] Vitals capture via IoT (BP cuff, SpO2 — inject into SOAP-O automatically)
- [ ] LLM fine-tuning on Indian medical corpus (ICD-10 aware)
- [ ] RTL support for Urdu

---

## 12. Repository Structure

```
medikiosk-sih26047/
├── backend/
│   ├── main.py               ← FastAPI app (444 lines)
│   ├── agent.md              ← All AI prompts (ARIA + Summary agent)
│   ├── session_data.json     ← Runtime queue persistence
│   ├── .env                  ← GEMINI_API_KEY, GROQ_API_KEY (gitignored)
│   ├── requirements.txt      ← Python dependencies
│   └── static/
│       ├── index.html        ← ABHA login
│       ├── chat.html         ← AI intake interview + TTS
│       ├── dashboard.html    ← Patient SOAP summary review
│       ├── status.html       ← Patient live token status
│       └── doctor_panel.html ← Doctor queue + approval panel
├── README.md
├── ARCHITECTURE.md
├── medikiosk_architecture_modules.md
└── MediKiosk_Project_Draft.md   ← This file
```

---

## 13. How to Run

```bash
# 1. Clone
git clone https://github.com/MihirMaurya-dev/medikiosk-sih26047.git
cd medikiosk-sih26047/backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set API keys
echo "GEMINI_API_KEY=your_key_here" > .env
echo "GROQ_API_KEY=your_groq_key_here" >> .env

# 4. Run
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# 5. Open browser
# Patient: http://127.0.0.1:8000
# Doctor:  http://127.0.0.1:8000/doctor-panel
```

---

## 14. Key Differentiators vs Existing Solutions

| Feature | MediKiosk | Traditional OPD System |
|---|---|---|
| History taking | AI does it before doctor | Doctor does it during consultation |
| Language support | 4 Indian languages + voice | Usually English forms |
| Document scanning | Instant OCR via AI vision | Manual reading by doctor |
| Triage priority | Auto-assigned by AI (Low/Medium/High/Emergency) | Manual — first come first served |
| AYUSH support | Built-in Dashavidha Pariksha | Not supported |
| Real-time status | Live SSE — no refresh needed | Token display boards |
| ABDM integration | FHIR-ready mock | Usually none |
| Emergency detection | Instant red-flag → siren overlay | Patient waits in queue |

---

*Generated: 2026-09-19 | Version: 2.0 | Team: MediKiosk SIH-26047*
