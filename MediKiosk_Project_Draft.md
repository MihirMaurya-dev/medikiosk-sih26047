# MediKiosk — Detailed Project Draft
## Smart AI-Powered Patient Intake & Triage Kiosk
### Smart India Hackathon 2026 · Team Submission

---

> **One-line pitch:** MediKiosk replaces the paper token + waiting-room confusion at government hospitals with a conversational AI kiosk that takes the patient's full clinical history, scans their documents, generates a SOAP note, and routes them to the right department — before they ever sit in front of the doctor.

---

## 1. Problem Statement

Indian government hospitals face a massive patient load, leading to four interconnected bottlenecks at the Outpatient Department (OPD):

1. **Wasted Doctor Time (History Taking):**
    * **The Issue:** Doctors spend 3 to 5 minutes per patient simply asking basic questions (e.g., *"Kab se dard hai? Kahan dard hai? Puraani dawai kya le rahe ho?"*).
    * **The Impact:** If a doctor sees 100 patients a day, they waste up to **6 hours** just taking basic history. That is time that should be spent on diagnosis and treatment.
2. **Incorrect Department Routing:**
    * **The Issue:** At the registration counter, non-medical staff (or confused patients) often select the wrong department (e.g., sending a patient with chest pain caused by acid reflux to Cardiology instead of General Medicine).
    * **The Impact:** The patient waits 2 hours to see a doctor, only to be told, *"Yeh mera department nahi hai, wahan jao."* This doubles their waiting time and frustrates everyone.
3. **Hidden Context (Paper Reports):**
    * **The Issue:** Patients bring old, crumpled paper reports and lab results. The doctor has to spend time reading them on the spot.
    * **The Impact:** Doctors are forced to make rapid decisions without a clean, organized view of the patient's past medical history and current lab values.
4. **No Intelligent Triage (First-Come, First-Served):**
    * **The Issue:** A patient with a minor headache and a patient having a mild heart attack are put in the same queue.
    * **The Impact:** Critical emergency cases are not fast-tracked, leading to severe risks.

**The MediKiosk Solution:** A single, multilingual, voice-enabled kiosk placed *before* the consultation room that solves all four problems automatically.

---

## 2. What MediKiosk Does — End-to-End Flow

MediKiosk streamlines the entire OPD intake process through a structured 6-step journey:

1. **Patient Authentication & Discovery (`index.html`)**
   * The patient inputs their 14-digit ABHA (Ayushman Bharat Health Account) ID on the kiosk screen.
   * The system authenticates the user and fetches their past medical history, existing conditions, and known allergies securely from the ABDM network.

2. **AI-Driven Clinical Interview (`chat.html`)**
   * The patient interacts with **ARIA**, the multilingual AI triage nurse, using natural voice or text (supported in Hindi, English, Tamil, and Bengali).
   * ARIA systematically collects symptoms using the SOCRATES medical framework.
   * Patients can hold up physical documents to the camera; the kiosk performs OCR to extract vital medical data.
   * **Emergency Safety Net:** If red-flag symptoms are detected, ARIA instantly halts the interview and triggers an immediate triage alert.

3. **Intelligent Triage & Summary Generation (Backend)**
   * Once the patient finishes, the entire transcript and OCR data are processed by the Groq `llama-3.1-8b` model (with Gemini fallback).
   * The AI generates a structured SOAP note, assigns a triage priority (Low/Medium/High/Emergency), and routes the patient to the correct specialist department.

4. **Synchronized Waiting Experience (`status.html` & `doctor_panel.html`)**
   * **Patient View:** The kiosk switches to a live status board showing their queue number and department.
   * **Doctor View:** The physician's dashboard updates in real-time. Patients are sorted strictly by clinical priority, not chronologically.

5. **Physician Review & Approval**
   * Before the patient even enters the room, the doctor reviews the AI-generated SOAP note and differential diagnoses.
   * The doctor clicks "Approve Patient" to call them in.

6. **Patient Notification & EMR Push**
   * Server-Sent Events (SSE) instantly flash a green "Approved" signal on the patient's screen, instructing them to proceed to the cabin.
   * The final clinical note can be updated by the doctor and pushed back to the patient's ABHA locker.

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

## 4. Data Flow Diagram

```mermaid
graph TD
    %% Patient Kiosk Interactions
    subgraph Kiosk UI
        A[index.html<br>ABHA Auth] -->|Start Session| B[chat.html<br>Conversational Interface]
        B -->|Speech-to-Text| STT(Web Speech API)
        B -->|Upload Doc| Cam(File/Camera Scan)
    end

    %% Backend Services
    subgraph FastAPI Backend
        STT -->|POST /api/chat| ChatE[Chat Endpoint]
        Cam -->|POST /api/scan_document| OCRE[OCR Endpoint]
        
        ChatE -->|Inference| Groq((Groq API<br>Llama-3.1-8b))
        Groq -.->|On Failure Fallback| Gemini((Gemini API<br>3.5-Flash-Lite))
        OCRE -->|Vision Task| Gemini
        
        ChatE -->|Check Response| EFlag{"Has [EMERGENCY_FLAG]?"}
        EFlag -->|Yes| Siren[🚨 Instant UI Siren]
        EFlag -->|No| B
    end

    %% Summary & Triage Generation
    subgraph Triage Engine
        B -->|Finish & Send| SumE[POST /api/generate_summary]
        SumE -->|Transcript + OCR Context| Groq
        SumE -.->|On Failure Fallback| Gemini
        SumE -->|Parse Result| Struct[Extract SOAP JSON, Assign Dept & Priority]
        Struct -->|Save Token| DB[(session_data.json)]
    end

    %% Synchronized Status & Doctor Approval
    subgraph Waiting & Approval
        DB -->|Server-Sent Events| SSE[status.html<br>Live Patient Status]
        DB -->|GET /api/queue| Doc[doctor_panel.html<br>Doctor Queue]
        Doc -->|Review & Approve| App[POST /api/approve]
        App -->|Update Record| DB
    end
```

---

## 5. AI Pipeline — Detailed

Our backend utilizes a multi-model fallback architecture to ensure 100% uptime and speed.

### 5.1 Chat Pipeline (`/api/chat`)
* **Input:** Patient's ABHA ID, previous chat history, and the current message.
* **Process:** The system builds a prompt containing the ARIA persona, past medical history, and user input. It calls Groq's `llama-3.1-8b` for ultra-fast inference. If rate-limited, it automatically falls back to `gemini-3.5-flash-lite`.
* **Output:** Returns the AI's response text and an `is_emergency` boolean (triggered if the AI outputs `[EMERGENCY_FLAG]`).

### 5.2 Document Vision Pipeline (`/api/scan_document`)
* **Input:** Uploaded images or PDFs (max 10MB).
* **Process:** The file is converted to base64 and sent to Gemini Vision. The model acts as a clinical document reader, extracting key lab values, current medications, and past diagnoses.
* **Output:** The extracted text is returned to the frontend and injected invisibly into the chat history as a `[SYSTEM NOTE]`, ensuring the LLM considers this data for all subsequent questions.

### 5.3 Clinical Summary Pipeline (`/api/generate_summary`)
* **Input:** The complete patient interview transcript.
* **Process:** The transcript is validated and injected into a strict JSON-enforced prompt. The LLM extracts the subjective history, proposes objective next steps, generates differential diagnoses (Assessment), and formulates an investigation plan.
* **Output:** A structured JSON object containing the SOAP note, assigned department, priority level, and confidence flags.

### 5.4 Doctor Approval Pipeline (`/api/approve`)
* **Input:** The unique `token_id` and the doctor's name.
* **Process:** The token's status in the central queue is updated from "Pending" to "Approved".
* **Output:** Triggers an event on the SSE stream to notify the waiting patient instantly.

### 5.5 Real-time Notification Stream (`/api/stream/{token_id}`)
* **Architecture:** Uses Server-Sent Events (SSE) via FastAPI's `StreamingResponse`.
* **Process:** Maintains an open HTTP connection with the kiosk. It polls the in-memory queue every second. Once the token status changes to "Approved", it pushes the update and cleanly closes the connection.

---

## 6. Prompt Architecture (`agent.md`)

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

## 7. Frontend Pages & Their Roles

| Page | File | Role |
|---|---|---|
| Login | `index.html` | ABHA ID entry with 14-digit validation, consent checkbox |
| Chat | `chat.html` | ARIA AI interview, voice I/O, OCR upload, TTS, language picker |
| Dashboard | `dashboard.html` | Patient-facing SOAP summary review before doctor sees them |
| Status | `status.html` | Patient waiting screen — live SSE token status |
| Doctor Panel | `doctor_panel.html` | Doctor queue view — priority-sorted cards, full analysis modal, approve |

---

## 8. Data Model

MediKiosk uses a highly structured schema to maintain state between the patient kiosk and the doctor's terminal. 

### 8.1 Patient Token Schema (`token_data`)
Every intake session generates a Token Object with the following fields:

* **Identity & Routing:**
  * `token_id`: Unique alphanumeric identifier (e.g., "A1B2C3D4").
  * `abha_id`: The patient's 14-digit national health ID.
  * `department`: The AI-assigned specialist department (e.g., "Cardiology").
  * `queue_number`: The sequential token number for that specific department.
* **Clinical Data:**
  * `priority`: Triage urgency (`Low`, `Medium`, `High`, `Emergency`).
  * `soap`: A nested object containing `S` (Subjective), `O` (Objective), `A` (Assessment), and `P` (Plan).
  * `reports`: An array of text extracted from physical documents via OCR.
* **Metadata & State:**
  * `confidence_flags`: An array of AI self-evaluations highlighting missing or low-confidence data points (e.g., if the patient was vague about pain severity).
  * `status`: Current state in the queue (`Pending` or `Approved`).
  * `timestamp`: ISO-8601 creation time for chronological sorting.

### 8.2 Database Architecture (`session_data.json`)
For the hackathon scope, state is persisted in a lightweight JSON file (easily swappable to PostgreSQL/Redis). It contains two primary keys:
1. `queue`: A dictionary mapping `token_id` to the full `token_data` object.
2. `counters`: A dictionary tracking the next available queue number for each specific department.

---

## 9. Security & Reliability Choices

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

## 10. AYUSH Integration

MediKiosk has first-class support for Ayurvedic/AYUSH consultations:

- **Trigger words**: "ayurveda", "vaidya", "prakriti", "nadi", "पंचकर्म", etc.
- **Mode switch**: Full Dashavidha Pariksha (10-parameter Ayurvedic intake)
- **Parameters collected**: Prakriti, Vikriti, Sara, Samhanana, Pramana, Satmya, Sattva, Ahara Shakti, Vyayama Shakti, Vaya + Nidana
- **SOAP relabeling**: S → Prakriti + Vikriti, O → Dashavidha Pariksha, A → Dosha Assessment (Vata/Pitta/Kapha), P → Vaidya Plan
- **Routing**: Always routes to `Ayurveda (AYUSH)` department
- **UI**: Green AYUSH badge shows on doctor panel and dashboard

---

## 11. Multi-language Support

| Language | Voice Input | TTS Output | AI Response | Trigger |
|---|---|---|---|---|
| Hindi | ✅ `hi-IN` | ✅ | ✅ (Devanagari) | Default |
| English | ✅ `en-IN` | ✅ | ✅ | Panel select / `en-IN` |
| Tamil | ✅ `ta-IN` | ✅ (if browser supports) | ✅ (Tamil script) | Panel select |
| Bengali | ✅ `bn-IN` | ✅ (if browser supports) | ✅ (Bengali script) | Panel select |

Language switching injects a `[SYSTEM NOTE]` into `chatHistory` — the AI is instructed to lock to the new language from that point.

---

## 12. Limitations & Future Roadmap

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

## 13. Repository Structure

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

## 14. How to Run & Deploy

Follow these steps to spin up the MediKiosk platform locally.

### Prerequisites
* Python 3.9 or higher
* Valid API keys for Groq and Google Gemini

### Step-by-Step Installation

1. **Clone the Repository**
   Download the source code to your local machine:
   ```bash
   git clone https://github.com/MihirMaurya-dev/medikiosk-sih26047.git
   cd medikiosk-sih26047/backend
   ```

2. **Install Dependencies**
   It is recommended to use a virtual environment. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**
   Create a `.env` file in the `backend` directory and add your API keys. *Do not commit this file to version control.*
   ```env
   GEMINI_API_KEY=your_gemini_key_here
   GROQ_API_KEY=your_groq_key_here
   ```

4. **Start the FastAPI Server**
   Launch the backend server with Uvicorn (hot-reloading enabled):
   ```bash
   uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

5. **Access the Interfaces**
   Open your web browser and navigate to:
   * **Patient Kiosk (Start Here):** `http://127.0.0.1:8000/`
   * **Doctor's Dashboard:** `http://127.0.0.1:8000/doctor-panel`

---

## 15. Key Differentiators vs Existing Solutions

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
