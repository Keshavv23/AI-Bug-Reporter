import os
import json
import requests
import sqlite3
import base64
import pytesseract
import re

from github import Github, Auth
from PIL import Image
from datetime import datetime

from flask import (
    Flask,
    render_template,
    request,
    send_file,
    redirect,
    flash,
    jsonify
)

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)

from reportlab.lib.styles import getSampleStyleSheet

from groq import Groq
from dotenv import load_dotenv


app = Flask(__name__)
load_dotenv()

# ---------------------------------
# SECRET KEY
# ---------------------------------
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey123")

# ---------------------------------
# LOGIN MANAGER
# ---------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ---------------------------------
# GROQ CLIENT
# ---------------------------------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------------------------------
# GITHUB SETUP
# ---------------------------------
auth          = Auth.Token(os.getenv("GITHUB_TOKEN"))
github_client = Github(auth=auth)
github_repo   = github_client.get_repo(os.getenv("GITHUB_REPO"))

# ---------------------------------
# TESSERACT CONFIG
# ---------------------------------
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# ---------------------------------
# FILE UPLOAD CONFIG
# ---------------------------------
UPLOAD_FOLDER = os.path.join("static", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# ---------------------------------
# CREATE FOLDERS
# ---------------------------------
for folder in ["bug_reports", "json_reports", "pdf_reports", "static/uploads"]:
    if not os.path.exists(folder):
        os.makedirs(folder)


# ---------------------------------
# DATABASE SETUP
# ---------------------------------
def init_db():
    conn   = sqlite3.connect("bugs.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            email      TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bugs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER,
            bug_id          TEXT,
            title           TEXT,
            category        TEXT,
            severity        TEXT,
            expected_result TEXT,
            actual_result   TEXT,
            suggested_fix   TEXT,
            screenshot      TEXT,
            ocr_text        TEXT,
            ai_analysis     TEXT,
            status          TEXT DEFAULT 'Open',
            priority        TEXT DEFAULT 'Medium',
            created_at      TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------------------------------
# EMAIL VALIDATION
# ---------------------------------
def is_valid_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email)


# ---------------------------------
# USER MODEL
# ---------------------------------
class User(UserMixin):
    def __init__(self, id, username, email):
        self.id       = id
        self.username = username
        self.email    = email


@login_manager.user_loader
def load_user(user_id):
    conn   = sqlite3.connect("bugs.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email FROM users WHERE id = ?",
        (user_id,)
    )
    user = cursor.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1], user[2])
    return None


# ---------------------------------
# OCR IMAGE ANALYSIS
# ---------------------------------
def extract_text_from_image(image_path):
    try:
        image          = Image.open(image_path)
        extracted_text = pytesseract.image_to_string(image)
        if extracted_text.strip() == "":
            return "No readable text detected."
        return extracted_text.strip()
    except Exception as e:
        return f"OCR Failed: {str(e)}"


# ---------------------------------
# AI BUG ANALYSIS (Groq)
# ---------------------------------
def analyze_screenshot_with_ai(ocr_text):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """
You are an expert QA engineer.
Analyze OCR extracted text from a software bug screenshot.
Return:
1. Bug understanding
2. Severity analysis
3. Possible root cause
4. Suggested fix
"""
                },
                {
                    "role": "user",
                    "content": f"OCR Text: {ocr_text}"
                }
            ],
            temperature=0.5,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI Analysis Failed: {str(e)}"


# ---------------------------------
# AI TEST CASE GENERATOR
# ---------------------------------
def generate_test_cases(description):
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """
You are a professional QA engineer.
Generate:
1. Functional test cases
2. Negative test cases
3. Edge cases
4. Regression test cases
Return clean bullet points.
"""
                },
                {
                    "role": "user",
                    "content": f"Generate test cases for: {description}"
                }
            ],
            temperature=0.5,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Test Case Generation Failed: {str(e)}"


# ---------------------------------
# SLACK ALERT
# ---------------------------------
def send_slack_alert(bug_data):
    try:
        webhook_url = os.getenv("SLACK_WEBHOOK")
        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"New Bug Report — {bug_data['bug_id']}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Title:*\n{bug_data['title']}"},
                        {"type": "mrkdwn", "text": f"*Severity:*\n{bug_data['severity']}"},
                        {"type": "mrkdwn", "text": f"*Category:*\n{bug_data['category']}"},
                        {"type": "mrkdwn", "text": f"*Date:*\n{bug_data['date']}"}
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*AI Suggested Fix:*\n{bug_data['fix']}"
                    }
                },
                {"type": "divider"}
            ]
        }
        requests.post(webhook_url, json=message)
    except:
        pass


# ---------------------------------
# GITHUB ISSUE CREATION
# ---------------------------------
def create_github_issue(bug_data):
    try:
        title = f"[{bug_data['severity']}] {bug_data['title']}"
        body  = f"""
## Bug Report — {bug_data['bug_id']}

**Category:** {bug_data['category']}
**Severity:** {bug_data['severity']}
**Date:** {bug_data['date']}

---

### Steps to Reproduce
{chr(10).join(f"{i+1}. {s}" for i, s in enumerate(bug_data['steps']))}

### Expected Result
{bug_data['expected']}

### Actual Result
{bug_data['actual']}

### AI Suggested Fix
{bug_data['fix']}
"""
        issue = github_repo.create_issue(
            title=title,
            body=body,
            labels=["bug"]
        )
        return issue.html_url
    except Exception as e:
        return f"GitHub Error: {str(e)}"


# ---------------------------------
# SEVERITY DETECTION
# ---------------------------------
def generate_severity(description):
    description = description.lower()
    if any(w in description for w in ["crash", "data loss", "security"]):
        return "Critical"
    if any(w in description for w in ["payment", "login", "signup", "not working", "unable"]):
        return "High"
    if any(w in description for w in ["slow", "delay", "ui", "alignment"]):
        return "Medium"
    return "Low"


# ---------------------------------
# CATEGORY DETECTION
# ---------------------------------
def detect_category(description):
    description = description.lower()
    if "login"   in description: return "Authentication"
    if "payment" in description: return "Payment"
    if "ui"      in description: return "UI/UX"
    if "slow"    in description: return "Performance"
    if "crash"   in description: return "Crash"
    return "General"


# ---------------------------------
# TITLE GENERATION
# ---------------------------------
def generate_title(description):
    description = description.lower()
    if "login"   in description: return "Login Functionality Issue"
    if "payment" in description: return "Payment Transaction Failed"
    if "crash"   in description: return "Application Crash Detected"
    if "slow"    in description: return "Application Performance Issue"
    return description.capitalize()


# ---------------------------------
# EXPECTED RESULT
# ---------------------------------
def generate_expected(description):
    description = description.lower()
    if "login"   in description: return "User should successfully log in"
    if "payment" in description: return "Payment should complete successfully"
    if "crash"   in description: return "Application should remain stable"
    if "slow"    in description: return "Application should respond quickly"
    return "Feature should work correctly"


# ---------------------------------
# STEPS GENERATION
# ---------------------------------
def generate_steps(description):
    return [
        "Open application",
        "Navigate to affected module",
        f"Perform action related to: {description}",
        "Observe the issue"
    ]


# ---------------------------------
# AI SUGGESTED FIX
# ---------------------------------
def generate_fix(description):
    description = description.lower()
    if "login" in description:
        return "• Check mobile click event binding\n• Verify JavaScript event listeners\n• Check authentication API response\n• Validate responsive UI elements"
    if "payment" in description:
        return "• Verify payment gateway API\n• Check transaction validation\n• Inspect backend payment response\n• Monitor network/API requests"
    if "crash" in description:
        return "• Check null pointer exceptions\n• Analyze memory usage\n• Verify application logs\n• Handle unhandled exceptions"
    if "slow" in description:
        return "• Optimize database queries\n• Check API response times\n• Reduce large asset loading\n• Improve backend optimization"
    return "• Check logs\n• Verify API responses\n• Validate frontend/backend flow"


# ---------------------------------
# PDF GENERATION
# ---------------------------------
def generate_pdf(bug_data, filename):
    doc     = SimpleDocTemplate(filename)
    styles  = getSampleStyleSheet()
    content = []

    content.append(Paragraph(f"<b>{bug_data['title']}</b>", styles['Title']))
    content.append(Spacer(1, 20))

    fields = [
        ("Bug ID",             bug_data['bug_id']),
        ("Date",               bug_data['date']),
        ("Category",           bug_data['category']),
        ("Severity",           bug_data['severity']),
        ("Expected Result",    bug_data['expected']),
        ("Actual Result",      bug_data['actual']),
        ("OCR Analysis",       bug_data['ocr_text']),
        ("AI Analysis",        bug_data['ai_analysis']),
        ("AI Suggested Fix",   bug_data['fix'])
    ]

    for label, value in fields:
        content.append(Paragraph(f"<b>{label}:</b> {value}", styles['BodyText']))
        content.append(Spacer(1, 12))

    doc.build(content)


# ---------------------------------
# REGISTER
# ---------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email    = request.form["email"].strip()
        password = request.form["password"].strip()

        if not username or not email or not password:
            flash("All fields are required!", "error")
            return redirect("/register")

        if not is_valid_email(email):
            flash("Invalid email format!", "error")
            return redirect("/register")

        if len(password) < 6:
            flash("Password must be at least 6 characters!", "error")
            return redirect("/register")

        hashed_pw  = generate_password_hash(password)
        created_at = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        try:
            conn   = sqlite3.connect("bugs.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, email, password, created_at) VALUES (?, ?, ?, ?)",
                (username, email, hashed_pw, created_at)
            )
            conn.commit()
            conn.close()
            flash("Account created successfully!", "success")
            return redirect("/login")
        except Exception as e:
            flash(f"Registration failed: {str(e)}", "error")
            return redirect("/register")

    return render_template("register.html", error=None)


# ---------------------------------
# LOGIN
# ---------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form["email"].strip()
        password = request.form["password"].strip()

        if not email or not password:
            flash("All fields are required!", "error")
            return redirect("/login")

        conn   = sqlite3.connect("bugs.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, email, password FROM users WHERE email = ?",
            (email,)
        )
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            login_user(User(user[0], user[1], user[2]))
            flash("Login successful!", "success")
            return redirect("/")

        flash("Invalid email or password!", "error")
        return redirect("/login")

    return render_template("login.html", error=None)


# ---------------------------------
# LOGOUT  ← FIXED: flash() now correctly inside function
# ---------------------------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "success")  # ← correct indentation!
    return redirect("/login")


# ---------------------------------
# HOME ROUTE
# ---------------------------------
@app.route("/", methods=["GET", "POST"])
@login_required
def home():
    report = None

    if request.method == "POST":
        description    = request.form["description"]
        image          = request.files.get("screenshot")
        image_filename = None
        ocr_text       = "No screenshot uploaded."
        ai_analysis    = "No AI screenshot analysis available."

        if image and image.filename != "":
            image_filename = secure_filename(image.filename)
            image_path     = os.path.join(app.config["UPLOAD_FOLDER"], image_filename)
            image.save(image_path)
            ocr_text    = extract_text_from_image(image_path)
            ai_analysis = analyze_screenshot_with_ai(ocr_text)

        # Get next ID from database
        conn_id   = sqlite3.connect("bugs.db")
        cursor_id = conn_id.cursor()
        cursor_id.execute("SELECT COUNT(*) FROM bugs")
        bug_id = cursor_id.fetchone()[0] + 1
        conn_id.close()

        title    = generate_title(description)
        severity = generate_severity(description)
        category = detect_category(description)
        expected = generate_expected(description)
        steps    = generate_steps(description)
        fix      = generate_fix(description)
        test_cases = generate_test_cases(description)

        current_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        bug_data = {
            "bug_id":      f"BUG-{bug_id:03}",
            "date":        current_time,
            "title":       title,
            "category":    category,
            "severity":    severity,
            "steps":       steps,
            "expected":    expected,
            "actual":      description,
            "fix":         fix,
            "screenshot":  image_filename,
            "ocr_text":    ocr_text,
            "ai_analysis": ai_analysis,
            "test_cases":  test_cases
        }

        # SAVE TXT
        with open(f"bug_reports/bug_{bug_id:03}.txt", "w", encoding="utf-8") as f:
            f.write(json.dumps(bug_data, indent=4))

        # SAVE JSON
        with open(f"json_reports/bug_{bug_id:03}.json", "w", encoding="utf-8") as f:
            json.dump(bug_data, f, indent=4)

        # SAVE PDF
        generate_pdf(bug_data, f"pdf_reports/bug_{bug_id:03}.pdf")

        # SAVE DATABASE
        conn   = sqlite3.connect("bugs.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bugs (
                user_id, bug_id, title, category, severity,
                expected_result, actual_result, suggested_fix,
                screenshot, ocr_text, ai_analysis,
                status, priority, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            current_user.id,
            bug_data["bug_id"],
            bug_data["title"],
            bug_data["category"],
            bug_data["severity"],
            bug_data["expected"],
            bug_data["actual"],
            bug_data["fix"],
            bug_data["screenshot"],
            bug_data["ocr_text"],
            bug_data["ai_analysis"],
            "Open",
            severity,
            bug_data["date"]
        ))
        conn.commit()
        conn.close()

        bug_data["pdf_file"]   = f"bug_{bug_id:03}.pdf"
        bug_data["github_url"] = create_github_issue(bug_data)
        send_slack_alert(bug_data)

        report = bug_data

    return render_template("index.html", report=report)


# ---------------------------------
# DOWNLOAD PDF
# ---------------------------------
@app.route("/download/<filename>")
@login_required
def download_file(filename):
    return send_file(
        os.path.join("pdf_reports", filename),
        as_attachment=True
    )


# ---------------------------------
# HISTORY  ← FIXED: filters now properly wired
# ---------------------------------
@app.route("/history")
@login_required
def history():
    search   = request.args.get("search", "").strip()
    severity = request.args.get("severity", "")
    status   = request.args.get("status", "")

    query  = """
        SELECT bug_id, title, category, severity, status, priority, created_at
        FROM bugs
        WHERE user_id = ?
    """
    params = [current_user.id]

    if search:
        query += " AND (title LIKE ? OR bug_id LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if severity:
        query += " AND severity = ?"
        params.append(severity)

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY id DESC"

    conn   = sqlite3.connect("bugs.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    bugs   = cursor.fetchall()
    conn.close()

    return render_template(
        "history.html",
        bugs=bugs,
        search=search,      # ← FIXED: now passed to template
        severity=severity,  # ← FIXED: now passed to template
        status=status       # ← FIXED: now passed to template
    )


# ---------------------------------
# ANALYTICS
# ---------------------------------
@app.route("/analytics")
@login_required
def analytics():
    conn   = sqlite3.connect("bugs.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM bugs WHERE user_id = ?", (current_user.id,))
    total_bugs = cursor.fetchone()[0]

    cursor.execute(
        "SELECT severity, COUNT(*) FROM bugs WHERE user_id = ? GROUP BY severity",
        (current_user.id,)
    )
    severity_data = cursor.fetchall()

    cursor.execute(
        "SELECT category, COUNT(*) FROM bugs WHERE user_id = ? GROUP BY category",
        (current_user.id,)
    )
    category_data = cursor.fetchall()

    conn.close()

    return render_template(
        "analytics.html",
        total_bugs=total_bugs,
        severity_labels=[r[0] for r in severity_data],
        severity_counts=[r[1] for r in severity_data],
        category_labels=[r[0] for r in category_data],
        category_counts=[r[1] for r in category_data]
    )


# ---------------------------------
# API — HISTORY
# ---------------------------------
@app.route("/api/history")
@login_required
def api_history():
    conn   = sqlite3.connect("bugs.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT bug_id, title, category, severity, created_at
        FROM bugs WHERE user_id = ? ORDER BY id DESC
    """, (current_user.id,))
    bugs = cursor.fetchall()
    conn.close()

    return jsonify([{
        "bug_id":     b[0],
        "title":      b[1],
        "category":   b[2],
        "severity":   b[3],
        "created_at": b[4]
    } for b in bugs])


# ---------------------------------
# API — ANALYTICS
# ---------------------------------
@app.route("/api/analytics")
@login_required
def api_analytics():
    conn   = sqlite3.connect("bugs.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM bugs WHERE user_id = ?", (current_user.id,))
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM bugs WHERE severity='Critical' AND user_id = ?", (current_user.id,))
    critical = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM bugs WHERE severity='High' AND user_id = ?", (current_user.id,))
    high = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "total_bugs":    total,
        "critical_bugs": critical,
        "high_bugs":     high
    })


# ---------------------------------
# API — SINGLE BUG
# ---------------------------------
@app.route("/api/bugs/<bug_id>")
@login_required
def api_single_bug(bug_id):
    conn   = sqlite3.connect("bugs.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT bug_id, title, category, severity,
               expected_result, actual_result, suggested_fix, created_at
        FROM bugs WHERE bug_id = ? AND user_id = ?
    """, (bug_id, current_user.id))
    bug = cursor.fetchone()
    conn.close()

    if not bug:
        return jsonify({"error": "Bug not found"}), 404

    return jsonify({
        "bug_id":          bug[0],
        "title":           bug[1],
        "category":        bug[2],
        "severity":        bug[3],
        "expected_result": bug[4],
        "actual_result":   bug[5],
        "suggested_fix":   bug[6],
        "created_at":      bug[7]
    })


# ---------------------------------
# API — UPDATE BUG STATUS
# ---------------------------------
@app.route("/api/update-status/<bug_id>/<status>")
@login_required
def update_bug_status(bug_id, status):
    allowed = ["Open", "In Progress", "Resolved", "Closed"]

    if status not in allowed:
        return jsonify({"error": "Invalid status"}), 400

    conn   = sqlite3.connect("bugs.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE bugs SET status = ? WHERE bug_id = ? AND user_id = ?",
        (status, bug_id, current_user.id)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "message":    "Status updated",
        "bug_id":     bug_id,
        "new_status": status
    })


# ---------------------------------
# RUN FLASK APP
# ---------------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)