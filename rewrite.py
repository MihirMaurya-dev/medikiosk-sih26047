import re

with open('MediKiosk_Project_Draft.md', 'r', encoding='utf-8') as f:
    text = f.read()

# --- Section 2 Rewrite ---
sec2_new = """## 2. What MediKiosk Does — End-to-End Flow

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
"""
text = re.sub(r'## 2\. What MediKiosk Does — End-to-End Flow.*?---', sec2_new + '\n---', text, flags=re.DOTALL)


# --- Section 5 Rewrite ---
sec5_new = """## 5. AI Pipeline — Detailed

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
"""
text = re.sub(r'## 5\. AI Pipeline — Detailed.*?---', sec5_new + '\n---', text, flags=re.DOTALL)


# --- Section 8 Rewrite ---
sec8_new = """## 8. Data Model

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
"""
text = re.sub(r'## 8\. Data Model.*?---', sec8_new + '\n---', text, flags=re.DOTALL)


# --- Section 14 Rewrite ---
sec14_new = """## 14. How to Run & Deploy

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
"""
text = re.sub(r'## 14\. How to Run.*?---', sec14_new + '\n---', text, flags=re.DOTALL)


with open('MediKiosk_Project_Draft.md', 'w', encoding='utf-8') as f:
    f.write(text)
