# MediKiosk — AI-Powered Clinical History & Triage Platform

MediKiosk is an autonomous, conversational patient intake kiosk built for **SIH 2026 (Problem Statement SIH26047)**. It uses AI to conduct dynamic clinical interviews (both Allopathic SOCRATES and Ayurvedic Dashavidha Pariksha) and generates structured SOAP notes for doctors to save consultation time.

## 🚀 How to Run Locally

Follow these steps to set up and run the project on your machine.

### Prerequisites
- **Python 3.9+** installed
- **Git** installed
- A **Google Gemini API Key** (Get it free from [Google AI Studio](https://aistudio.google.com/))

---

### Step 1: Clone the Repository
Open your terminal and clone the repository:
```bash
git clone https://github.com/MihirMaurya-dev/medikiosk-sih26047.git
cd medikiosk-sih26047
```

### Step 2: Set Up the Backend Environment
Navigate into the `backend` folder and create a virtual environment:

**For Windows:**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
```

**For Mac/Linux:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
Install all the required Python packages:
```bash
pip install -r requirements.txt
```

### Step 4: Configure API Key
Create a `.env` file inside the `backend` folder. You can do this manually or via terminal.

Inside `.env`, add your Gemini API key:
```ini
GEMINI_API_KEY=your_actual_api_key_here
```

### Step 5: Start the Server
Run the FastAPI application using Uvicorn:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
You should see a message saying the server has started successfully.

---

## 🖥️ How to Test & Demo the Project

Once the server is running, the app is fully accessible via your browser.

1. **Patient Interface (The Kiosk):**
   Open your browser and go to: `http://127.0.0.1:8000/`
   - Enter a 14-digit ABHA ID (e.g., `12345678901234`) and check the consent box.
   - Start chatting (type or speak via mic).
   - *Test AYUSH mode:* Say "I want ayurveda consultation" to trigger the Dashavidha Pariksha.
   - *Test Emergency mode:* Say "I have severe chest pain and breathlessness" to see the red flag triage.
   - Click "Finish & Send to Doctor" to generate the summary.

2. **Doctor Interface (The Dashboard):**
   Open a *second tab* and go to: `http://127.0.0.1:8000/doctor-panel`
   - View the patient in the queue.
   - Click "View Details" to see the generated SOAP note and Confidence Flags.
   - Click "Approve". 
   - Notice how the patient's status tab instantly updates to ✅ green without refreshing (powered by Server-Sent Events).

---

## 📂 Project Structure
- `/backend/main.py` — Core FastAPI logic, AI prompts, and API routes.
- `/backend/static/` — Frontend HTML, JS, and CSS files.
  - `index.html` — Login and consent.
  - `chat.html` — The main conversational AI interface.
  - `status.html` — Post-interview live waiting room status.
  - `dashboard.html` & `doctor_panel.html` — The doctor's queue and approval view.
- `ARCHITECTURE.md` — Detailed system architecture and innovative approach document.

## ⚠️ Notes for Hackathon Judges
- **Browser Mic Permission:** Ensure you allow microphone access in your browser when testing the voice feature.
- **Server Persistence:** Patient queue data is automatically saved locally to `session_data.json` inside the backend folder, so data survives server restarts.
