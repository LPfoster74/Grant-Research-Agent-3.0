from flask import Flask, render_template, request, redirect, url_for, abort
import requests
from bs4 import BeautifulSoup
import uuid
import os
import json

app = Flask(__name__)

def load_allowed_sources(path=None):
    default = [
        "https://www.ecfr.gov/current/title-2/subtitle-A/chapter-II/part-200",
    ]
    sources = []
    base = os.path.dirname(__file__)
    src_file = path or os.path.join(base, "allowed_sources.txt")
    try:
        with open(src_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                sources.append(line)
    except Exception:
        sources = default

    # Ensure default 2 CFR Part 200 is present
    if "https://www.ecfr.gov/current/title-2/subtitle-A/chapter-II/part-200" not in sources:
        sources.insert(0, "https://www.ecfr.gov/current/title-2/subtitle-A/chapter-II/part-200")

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for s in sources:
        if s in seen:
            continue
        seen.add(s)
        unique.append(s)
    return unique


ALLOWED_SOURCES = load_allowed_sources()


def fetch_title(url):
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            doc = BeautifulSoup(resp.text, "html.parser")
            title = doc.title.string.strip() if doc.title and doc.title.string else url
            return title
    except Exception:
        return url
    return url


def build_analysis(circumstances, cfda, recipient_type):
    # Summarize the case
    summary = f"User inquiry regarding: {circumstances.strip()}"
    if cfda:
        summary += f" (CFDA: {cfda.strip()})"
    summary += f". Recipient type: {recipient_type}."

    # Applicable authorities (basic links + fetched titles)
    authorities = []
    for url in ALLOWED_SOURCES[:4]:
        authorities.append({"url": url, "title": fetch_title(url)})

    # Compliance checks referencing 2 CFR Part 200 sections commonly relevant
    compliance_checks = [
        {"section": "2 CFR 200.400-200.475", "topic": "Cost Principles (allowable costs, allocability, reasonableness)"},
        {"section": "2 CFR 200.300-200.309", "topic": "Pre-award requirements and risk assessment"},
        {"section": "2 CFR 200.330-200.332", "topic": "Subrecipient monitoring and pass-through entity responsibilities"},
        {"section": "2 CFR 200.344", "topic": "Closeout procedures"},
    ]

    # Key requirements and impacts (high-level)
    key_requirements = [
        "Document cost allowability under 2 CFR Part 200 Subpart E",
        "Perform risk-based monitoring for subrecipients and document oversight plans",
        "Ensure matching funds are properly identified, allowable, and documented",
        "Retain records per federal requirements and agency directives for audit readiness",
    ]

    # Suggested next-info from user
    suggestions = [
        "Provide estimated award amount and period of performance",
        "Attach relevant contract/grant terms or bill language if available",
        "Confirm whether recipient is a subrecipient or contractor",
    ]

    result = {
        "summary": summary,
        "authorities": authorities,
        "compliance_checks": compliance_checks,
        "additional_references": ALLOWED_SOURCES,
        "key_requirements": key_requirements,
        "suggestions": suggestions,
    }
    return result


def extract_text_from_pdf(path):
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(path)
        text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
        return "\n".join(text)
    except Exception:
        return ""


def extract_text_from_docx(path):
    try:
        import docx
        doc = docx.Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        return "\n".join(paragraphs)
    except Exception:
        return ""


def handle_upload(file_storage):
    if not file_storage or file_storage.filename == "":
        return None, None
    folder = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(folder, exist_ok=True)
    filename = file_storage.filename
    safe_name = f"{uuid.uuid4().hex}_{filename}"
    path = os.path.join(folder, safe_name)
    file_storage.save(path)
    text = ""
    fname = filename.lower()
    if fname.endswith('.pdf'):
        text = extract_text_from_pdf(path)
    elif fname.endswith('.docx'):
        text = extract_text_from_docx(path)
    elif fname.endswith('.txt'):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception:
            text = ""
    return safe_name, text


def save_analysis(result):
    folder = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(folder, exist_ok=True)
    uid = uuid.uuid4().hex
    path = os.path.join(folder, f"{uid}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return uid


def load_analysis(uid):
    path = os.path.join(os.path.dirname(__file__), "data", f"{uid}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    circumstances = request.form.get("circumstances", "").strip()
    cfda = request.form.get("cfda", "").strip()
    recipient_type = request.form.get("recipient_type", "Other")

    if not circumstances:
        return redirect(url_for("index"))

    # handle optional upload
    upload = request.files.get('upload')
    uploaded_name, uploaded_text = handle_upload(upload) if upload else (None, None)

    analysis = build_analysis(circumstances, cfda, recipient_type)
    if uploaded_name:
        analysis['uploaded_file'] = uploaded_name
        snippet = (uploaded_text or '')[:2000]
        analysis['uploaded_text_snippet'] = snippet

    uid = save_analysis(analysis)
    share_url = url_for("share", uid=uid, _external=True)
    return render_template("result.html", analysis=analysis, share_url=share_url)


@app.route("/share/<uid>")
def share(uid):
    data = load_analysis(uid)
    if not data:
        abort(404)
    return render_template("result.html", analysis=data, share_url=request.url)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
