# 🚀 Project Name: MediKiosk
**Problem Statement Code:** SIH26047 (Patient Case-Taking Software)
**Ministry:** Ministry of Ayush / All India Institute of Ayurveda

## 📝 1. Overview & Working Mechanism
**MediKiosk** is an autonomous, AI-powered conversational kiosk designed for Indian government hospitals and AYUSH centers. It acts as a digital junior doctor, conducting a dynamic clinical interview before the patient enters the doctor's cabin, thereby saving 70% of the consultation time.

### How it Works (End-to-End Flow):
1. **Patient Check-in:** Patient logs in using their ABHA ID on the kiosk and grants consent.
2. **Multilingual Voice Interface:** Patient speaks their symptoms naturally (Hindi/English). 
3. **Adaptive AI Interview:** The AI doesn't ask rigid forms. It uses adaptive branching:
   - *For Allopathic Cases:* Uses the **SOCRATES** framework (Site, Onset, Character, Radiation, etc.).
   - *For AYUSH Cases:* Automatically switches to **Dashavidha Pariksha** (Prakriti, Vikriti, Sara, etc.) upon detecting Ayurvedic keywords.
4. **Document Digitization (OCR):** Patients can hold up old prescriptions or lab reports to the kiosk camera. The Multimodal AI extracts medical data and injects it into the context.
5. **Zero-Latency Emergency Triage:** If red flags (e.g., chest pain + sweating) are detected, the AI halts the interview and triggers an immediate emergency alert, bypassing the queue.
6. **Doctor Dashboard:** The conversation is synthesized into a structured **S-O-A-P Clinical Note** and sent to the Doctor’s Dashboard in real-time. The doctor reviews the "AI Analysis" and approves the case with a single click.

---

## 💻 2. Tech Stack Used

To ensure ultra-low latency and maximum reliability in a hospital environment, we used a **Multi-Provider AI Architecture**:

*   **Frontend UI:** HTML5, Vanilla JavaScript, TailwindCSS *(Lightweight, browser-native, zero-build setup for fast kiosk execution).*
*   **Voice Engine (ASR/TTS):** Web Speech API *(Native browser support for Hindi and English without external API delays).*
*   **Backend API:** Python 3.9+, FastAPI, Uvicorn *(Asynchronous, high-concurrency handling).*
*   **AI Engine (Multi-Provider Strategy):**
    *   **Groq (Llama-3):** Primary engine for conversational logic and text generation. Used for its Lightning-fast LPU inference (near zero latency).
    *   **Google Gemini (3.5 Flash):** Acts as the **Multimodal Engine** for Medical Document OCR, and as an automated fallback if Groq hits rate limits.
*   **Real-time Communication:** Server-Sent Events (SSE) via FastAPI `StreamingResponse` *(Instantly updates the doctor's queue without heavy database polling).*
*   **Prompt Engineering:** Externalized System Prompts (`agent.md`) for easy tuning of medical guidelines without touching code.

---

## 🔄 3. Development Pipeline (How We Built It)

We followed an iterative, modular approach to build MediKiosk:

1. **Phase 1: Architecture & Backend Foundation**
   - Designed the data flow using FastAPI.
   - Implemented a dual-LLM routing system (Groq primary + Gemini fallback) to ensure 100% uptime and bypass free-tier rate limits.
   
2. **Phase 2: Prompt Engineering & Clinical Guardrails**
   - Developed strict System Prompts (`agent.md`) to restrict the AI from giving medical advice.
   - Programmed the **SOCRATES** (Allopathic) and **Dashavidha Pariksha** (AYUSH) frameworks into the AI's logic.
   - Added strict **Red-Flag Emergency rules** to instantly halt the bot if a patient describes life-threatening symptoms.

3. **Phase 3: Frontend Kiosk & Voice Integration**
   - Built a distraction-free, accessible UI for the kiosk (`chat.html`).
   - Integrated the Web Speech API so patients can speak naturally in Hindi or English, accompanied by a dynamic progress bar.

4. **Phase 4: Multimodal OCR Module**
   - Added a "Scan Document" feature where physical patient reports are processed by Gemini Vision. 
   - The extracted text is injected into the AI’s memory silently via a `[SYSTEM NOTE]`.

5. **Phase 5: Doctor Dashboard & Real-Time Sync**
   - Built `doctor_panel.html` with real-time SSE syncing.
   - Created the LLM Summary Generator module that converts raw chat transcripts into professional structured JSON (Subjective, Objective, Assessment, Plan) along with AI Confidence Flags.
   
6. **Phase 6: Testing & Edge-Case Handling**
   - Implemented LocalStorage clearing for proper patient session closure.
   - Added a "View Analysis" safeguard so doctors must review the AI's summary and scanned reports before clicking "Approve".

---

### 🌟 Unique Selling Points (USPs) for the Pitch:
- **AYUSH Native:** It doesn't just do generic symptom checking; it specifically executes Ayurvedic parameters (Dashavidha Pariksha), directly solving the Ministry of Ayush's core problem.
- **Fail-Safe AI Architecture:** If one LLM provider goes down or hits a limit, the system automatically falls back to another, ensuring the kiosk never crashes.
- **No-App Required:** Runs entirely in a browser, perfect for public hospital kiosks where downloading apps is impossible.
