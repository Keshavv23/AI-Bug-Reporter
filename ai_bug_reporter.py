import os
import json
from datetime import datetime
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Create folders automatically
if not os.path.exists("bug_reports"):
    os.makedirs("bug_reports")

if not os.path.exists("json_reports"):
    os.makedirs("json_reports")


# Severity Detection
def generate_severity(description):

    description = description.lower()

    critical_keywords = [
        "crash",
        "payment failed",
        "security",
        "data loss"
    ]

    high_keywords = [
        "login",
        "signup",
        "not working",
        "unable"
    ]

    medium_keywords = [
        "slow",
        "delay",
        "ui issue"
    ]

    for word in critical_keywords:
        if word in description:
            return "Critical"

    for word in high_keywords:
        if word in description:
            return "High"

    for word in medium_keywords:
        if word in description:
            return "Medium"

    return "Low"


# Category Detection
def detect_category(description):

    description = description.lower()

    if "login" in description:
        return "Authentication"

    elif "payment" in description:
        return "Payment"

    elif "ui" in description:
        return "UI/UX"

    elif "slow" in description:
        return "Performance"

    elif "crash" in description:
        return "Crash"

    return "General"


# Generate Title
def generate_title(description):

    description = description.lower()

    if "login" in description:
        return "Login functionality issue"

    elif "payment" in description:
        return "Payment transaction failed"

    elif "crash" in description:
        return "Application crash detected"

    return description.capitalize()


# Expected Result
def generate_expected(description):

    description = description.lower()

    if "login" in description:
        return "User should successfully log in"

    elif "payment" in description:
        return "Payment should complete successfully"

    elif "crash" in description:
        return "Application should remain stable"

    return "Feature should work correctly"


# Generate Steps
def generate_steps(description):

    return [
        "Open application",
        "Navigate to affected module",
        f"Perform action related to: {description}",
        "Observe the issue"
    ]


# Severity Color
def severity_color(severity):

    if severity == "Critical":
        return Fore.RED

    elif severity == "High":
        return Fore.LIGHTRED_EX

    elif severity == "Medium":
        return Fore.YELLOW

    else:
        return Fore.GREEN


# Create Bug Report
def create_bug_report(description, bug_id):

    title = generate_title(description)

    severity = generate_severity(description)

    category = detect_category(description)

    expected = generate_expected(description)

    actual = description

    steps = generate_steps(description)

    current_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    severity_col = severity_color(severity)

    # TEXT REPORT
    report = f"""
────────────────────────────────────
🐛 BUG ID       : BUG-{bug_id:03}
📅 DATE         : {current_time}

🐛 BUG TITLE    : {title}
📂 CATEGORY     : {category}
⚠️  SEVERITY     : {severity_col}{severity}{Style.RESET_ALL}

📋 STEPS TO REPRODUCE :
"""

    for index, step in enumerate(steps, start=1):
        report += f"   {index}. {step}\n"

    report += f"""
✅ EXPECTED RESULT :
   {expected}

❌ ACTUAL RESULT :
   {actual}

────────────────────────────────────
"""

    # Save TXT
    txt_filename = f"bug_reports/bug_{bug_id:03}.txt"

    with open(txt_filename, "w", encoding="utf-8") as file:
        file.write(report)

    # JSON DATA
    bug_data = {
        "bug_id": f"BUG-{bug_id:03}",
        "date": current_time,
        "title": title,
        "category": category,
        "severity": severity,
        "steps_to_reproduce": steps,
        "expected_result": expected,
        "actual_result": actual
    }

    # Save JSON
    json_filename = f"json_reports/bug_{bug_id:03}.json"

    with open(json_filename, "w", encoding="utf-8") as json_file:
        json.dump(bug_data, json_file, indent=4)

    return report, txt_filename, json_filename


# MAIN PROGRAM
print(Fore.CYAN + "\n=== AI Bug Report Generator ===\n")

description = input(Fore.WHITE + "Describe the bug: ")

bug_id = len(os.listdir("bug_reports")) + 1

report, txt_file, json_file = create_bug_report(description, bug_id)

print(report)

print(Fore.GREEN + f"💾 TXT Saved  : {txt_file}")
print(Fore.GREEN + f"💾 JSON Saved : {json_file}")