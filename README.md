# LeadLift — Marketing Automation Dashboard

LeadLift is a premium, self-hosted marketing automation dashboard built to streamline partnership outreach and business development for agency/clinic services. It features AI-powered personalization, automated email sequences, a Kanban pipeline board, and real-time analytics.

---

## ✨ Features

- **📊 Live Analytics Dashboard**: Real-time KPI cards, pipeline funnel breakdown, and custom target deadline countdown.
- **🔄 Kanban Pipeline Board**: Drag-and-drop contacts through custom pipeline stages (Enriched ➔ Contacted ➔ Responded ➔ Meeting ➔ Signed).
- **🏢 Lead Manager**: Comprehensive list of 50 pre-qualified clinic & agency leads with locations, services, and partnership scores.
- **👤 Contact Organizer**: Detailed decision-maker profiles linked to target companies, complete with verified email domains and LinkedIn URLs.
- **✉️ Outreach Center**: Compose messages using pre-built templates or draft hyper-personalized pitches utilizing **Gemini AI** with pre-configured agency hooks.
- **📅 Meeting Tracker**: Book, log, and monitor meeting details and outcomes.
- **⚙️ Settings Panel**: Save sender profile info, SMTP configurations, Calendly links, and Gemini API keys.
- **✨ Premium UI/UX**: Custom dark-mode glassmorphism styling built with modern responsive CSS.

---

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.10+)
- **Database**: SQLite (SQLAlchemy/Raw queries with dict-like row factories)
- **Frontend**: Single-Page App (SPA) built with Vanilla HTML5, CSS3, and JavaScript
- **AI Integration**: Google Gemini API (`google-genai` Python library)
- **Email Wrapper**: SMTP (`aiosmtplib`, `ssl`, `email`)
- **Task Scheduler**: Advanced Python Scheduler (`apscheduler`)

---

## 🚀 Quickstart

### 1. Prerequisites
Ensure you have Python 3.10+ installed on your machine.

### 2. Clone the Repository
```bash
git clone <your-repository-url>
cd Sales
```

### 3. Create & Activate Virtual Environment
**On Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Launch the Server
```bash
python app.py
```

Open your browser and navigate to **[http://localhost:8000](http://localhost:8000)**.

---

## ⚙️ Configuration Setup

After launching the dashboard, go to the **Settings** (⚙️) tab in the sidebar and enter:
1. **Gemini API Key**: Obtain a free key from [Google AI Studio](https://aistudio.google.com/apikey) to enable personalized AI pitching.
2. **SMTP Details**: Your sender email (e.g. Gmail) and an App Password (not your regular password) to automate sending emails.
3. **Calendly Booking Link**: To automatically embed your meeting schedule in emails.

---

## 📂 Project Structure

```
├── static/
│   ├── index.html       # Single Page Application HTML structure
│   ├── styles.css       # Premium Glassmorphism Dark CSS design tokens
│   └── app.js           # Client-side SPA Router, state management, and charting
├── data/
│   └── *.csv            # Source lead data (agencies, decision-makers)
├── app.py               # FastAPI server entry point and REST API routes
├── database.py          # SQLite database schema, connections, and CSV seeding
├── automation.py        # Core Gemini AI engine, SMTP email, and follow-up cron jobs
├── requirements.txt     # Python package requirements list
└── .gitignore           # Standard git ignoring patterns
```
