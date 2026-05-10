# 🤖 AI Bug Report Generator & QA Intelligence Platform

An AI-powered bug reporting platform built with Python, Flask, and Groq LLaMA. Automatically generates structured bug reports, creates GitHub Issues, sends Slack alerts, and provides analytics — all from a simple bug description.

---

## 🔥 Features

| Feature | Description |
|---|---|
| 🐛 AI Bug Report Generation | Type a bug description → AI generates full structured report |
| 🧪 AI Test Case Generator | Auto-generates functional, negative, and edge case tests |
| 🧠 OCR Screenshot Analysis | Upload screenshot → extracts text and analyzes the bug |
| 🐙 GitHub Issues Integration | Auto-creates GitHub Issues from every bug report |
| 🔔 Slack Alerts | Sends real-time Slack notification to your team |
| 📊 Analytics Dashboard | Visual charts for severity and category distribution |
| 📜 Bug History | Searchable, filterable bug history with status tracking |
| 📄 PDF Export | Professional PDF bug reports for enterprise use |
| 🔐 User Authentication | Register, login, logout — each user sees only their bugs |
| 🌐 REST API | JSON API endpoints for external integrations |

---

## 🧠 Tech Stack

**Backend**
- Python 3.12+
- Flask + Flask-Login
- SQLite

**AI**
- Groq API (LLaMA 3.3 70B)
- Tesseract OCR
- Pillow (image processing)

**Integrations**
- GitHub API (PyGithub)
- Slack Webhooks
- ReportLab (PDF generation)

**Frontend**
- HTML + CSS
- Chart.js (analytics)
- Glassmorphism UI

---

## 🚀 Getting Started

### 1 — Clone the repo
```bash
git clone https://github.com/Keshavv23/AI-Bug-Reporter.git
cd AI-Bug-Reporter
```

### 2 — Install dependencies
```bash
pip install -r requirements.txt
```

### 3 — Install Tesseract OCR
Download from: https://github.com/UB-Mannheim/tesseract/wiki

### 4 — Create `.env` file
```
GROQ_API_KEY=your_groq_api_key
GITHUB_TOKEN=your_github_token
GITHUB_REPO=your_username/your_repo
SLACK_WEBHOOK=your_slack_webhook_url
SECRET_KEY=any_random_secret_string
```

### 5 — Run the app
```bash
python app.py
```

### 6 — Open in browser
```
http://127.0.0.1:5000
```

---

## 📸 How It Works

```
User types bug description
         ↓
AI generates structured report
(title, severity, category, steps, fix)
         ↓
┌────────────────────────────┐
│  Saves to SQLite database  │
│  Saves TXT + JSON + PDF    │
│  Creates GitHub Issue      │
│  Sends Slack alert         │
└────────────────────────────┘
         ↓
Report displayed with AI test cases
```

---

## 🌐 REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/history` | All bugs as JSON |
| GET | `/api/analytics` | Bug counts and stats |
| GET | `/api/bugs/<bug_id>` | Single bug details |
| GET | `/api/update-status/<bug_id>/<status>` | Update bug status |

---

## 📁 Project Structure

```
AI-Bug-Reporter/
├── app.py                 # Main Flask application
├── ai_bug_reporter.py     # CLI version
├── requirements.txt       # Python dependencies
├── .env                   # API keys (not in repo)
├── .gitignore
├── templates/
│   ├── index.html         # Main bug reporter UI
│   ├── history.html       # Bug history dashboard
│   ├── analytics.html     # Analytics charts
│   ├── login.html         # Login page
│   └── register.html      # Register page
├── static/
│   └── uploads/           # Screenshot uploads
├── bug_reports/           # TXT reports
├── json_reports/          # JSON reports
└── pdf_reports/           # PDF reports
```

---

## 👤 Author

**Keshav** — QA Automation Engineer & AI Developer

- GitHub: [@Keshavv23](https://github.com/Keshavv23)
- LinkedIn: [keshav-besh-1b1a45302](https://linkedin.com/in/keshav-besh-1b1a45302)

---

## 📄 License

MIT License — free to use and modify.