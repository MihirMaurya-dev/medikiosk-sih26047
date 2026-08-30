# MediKiosk: AI Clinical History Software Platform
**SIH 2026 Problem Statement: SIH26047**

This document outlines the core architecture and development modules required to build the MediKiosk solution. You can share this with your team to divide tasks and understand the technical requirements.

## 🏗️ Architecture Overview

The platform consists of four primary modules that take a patient from check-in to generating a structured clinical summary for the physician.

---

### Module A: Conversational Multimodal History Engine
**Goal:** Conduct a structured clinical history interview through voice and touch.

*   **Responsibilities:**
    *   Capture patient input via voice (microphone) or touch (UI buttons).
    *   Convert regional language speech to text (ASR).
    *   Use an LLM to dynamically determine the next best clinical question based on previous answers (Adaptive Questioning).
    *   Convert the LLM's text response back to regional language audio (TTS).
    *   **AYUSH Mode:** Incorporate questions for *Dashavidha Pariksha* (Prakriti, Vikriti, etc.) and *Ahara-Vihara* (Diet and Lifestyle).
    *   **Red-Flag Detection:** Detect emergency keywords (e.g., "severe chest pain") and trigger alerts.
*   **Recommended Tech Stack:**
    *   **Frontend:** HTML5, Vanilla JS (Lightweight Kiosk).
    *   **Backend:** Python (FastAPI).
    *   **AI/ML:** Web Speech API (for ASR/TTS), Groq Llama-3 (for lightning-fast conversation logic), Google Gemini 3.5 Flash (for Text generation fallback).

---

### Module B: Medical Document Digitization & Intelligence
**Goal:** Digitize physical medical records brought by the patient and extract structured data.

*   **Responsibilities:**
    *   Provide a UI to capture images of prior prescriptions, lab reports, and discharge summaries.
    *   Perform Optical Character Recognition (OCR) on both printed and handwritten documents using Multimodal LLMs.
    *   Extract specific medical entities: Diagnoses, Medications, Dosages, Lab test names, and values.
    *   Chronologically organize the extracted data and supply it to the Doctor Dashboard and Chat Engine.
*   **Recommended Tech Stack:**
    *   **OCR Engine:** Google Gemini 3.5 Flash (Multimodal capabilities).
    *   **Entity Extraction:** Direct JSON extraction via Prompt Engineering.

---

### Module C: Structured History Summary Generator
**Goal:** Synthesize the conversational history and digitized documents into a single, concise summary for the doctor.

*   **Responsibilities:**
    *   Aggregate data from Module A (Conversation) and Module B (Documents).
    *   Format the data into standard clinical structures:
        *   Chief Complaint
        *   History of Present Illness (HPI)
        *   Past Medical / Surgical History
        *   Drug & Allergy History
        *   Review of Systems (ROS)
    *   Display the summary on a separate **Physician Dashboard**.
    *   Allow the physician to edit, confirm, or reject the summary.
*   **Recommended Tech Stack:**
    *   **AI/ML:** Prompt Engineering with an LLM to format raw data into clinical terminology.
    *   **Frontend (Doctor UI):** React.js dashboard.
    *   **Database:** PostgreSQL or MongoDB to temporarily store the draft summary.

---

### Module D: Consent, Privacy & ABDM Integration
**Goal:** Ensure data security, obtain patient consent, and integrate with India's digital health ecosystem.

*   **Responsibilities:**
    *   Authenticate patients using their ABHA (Ayushman Bharat Health Account) ID via OTP.
    *   Obtain granular, revocable consent from the patient (with audio explanations).
    *   Convert the finalized clinical summary (from Module C) into FHIR (Fast Healthcare Interoperability Resources) standard format.
    *   Push the FHIR data to the hospital's HIS/EMR and link it to the patient's ABHA Personal Health Record.
    *   Ensure all temporary session data is cleared from the kiosk after submission.
*   **Recommended Tech Stack:**
    *   **Integration:** ABDM Sandbox APIs (for ABHA login and data transfer).
    *   **Standards:** FHIR / HL7 standard libraries for Python.
    *   **Security:** JWT authentication, encrypted database fields, secure session management.
