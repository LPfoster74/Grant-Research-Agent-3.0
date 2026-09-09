from flask import Flask, render_template, request, redirect, url_for, abort
import requests
from bs4 import BeautifulSoup
import uuid
import os
import json

from flask import Response

# create app early so decorators can reference it
app = Flask(__name__)

# Basic auth: if BASIC_AUTH_USER is set in the environment, require basic auth
BASIC_AUTH_USER = os.environ.get('BASIC_AUTH_USER')
BASIC_AUTH_PASS = os.environ.get('BASIC_AUTH_PASS')
# Optionally trust an authenticated reverse proxy that sets a header (for SSO)
# Set TRUST_AUTH_PROXY=1 and AUTH_PROXY_HEADER (default X-Remote-User) in the environment
TRUST_AUTH_PROXY = os.environ.get('TRUST_AUTH_PROXY')
AUTH_PROXY_HEADER = os.environ.get('AUTH_PROXY_HEADER', 'X-Remote-User')


def check_basic_auth():
    if not BASIC_AUTH_USER:
        return True
    # Allow bypass when a trusted proxy has authenticated the user and set a header
    try:
        if TRUST_AUTH_PROXY and (request.headers.get(AUTH_PROXY_HEADER) or request.environ.get('REMOTE_USER')):
            return True
    except Exception:
        pass
    auth = request.authorization
    if not auth:
        return False
    return auth.username == BASIC_AUTH_USER and auth.password == BASIC_AUTH_PASS


@app.before_request
def require_basic_auth():
    # allow access to static files without auth check
    if request.path.startswith('/static/'):
        return None
    if not check_basic_auth():
        return Response('Authentication required', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})


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


def load_agent_prompt(path=None):
    base = os.path.dirname(__file__)
    candidates = []
    if path:
        candidates.append(path)
    # primary agent prompt file
    candidates.append(os.path.join(base, 'agent_prompt.txt'))
    # fallback to existing prompt file if present
    candidates.append(os.path.join(base, 'VS Code Copilot Prompt 3.0.txt'))
    for p in candidates:
        try:
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception:
            continue
    return ''


AGENT_PROMPT = load_agent_prompt()


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
    # include agent prompt text used by the app so results are reproducible
    result['agent_prompt'] = AGENT_PROMPT
    # include recipient type for later regeneration and generate a narrative summary
    result["recipient_type"] = recipient_type
    result["narrative_summary"] = generate_narrative(result, circumstances, uploaded_text=None, recipient_type=recipient_type, verbosity='concise')
    return result


def assess_risk(circumstances, uploaded_text, recipient_type):
    score = 0
    text = (circumstances or '').lower() + ' ' + (uploaded_text or '').lower() + ' ' + (recipient_type or '').lower()
    keywords_high = ['fraud', 'overlap', 'unauthorized', 'noncompliance', 'penalty', 'debar', 'suspend']
    keywords_med = ['indirect cost', 'matching', 'cost principles', 'audit', 'cost sharing', 'allowable']
    for k in keywords_high:
        if k in text:
            score += 3
    for k in keywords_med:
        if k in text:
            score += 1
    # recipient type adjustments
    if 'nonprofit' in text or 'tribal' in text:
        score += 0
    if score >= 4:
        return 'High'
    if score >= 2:
        return 'Moderate'
    return 'Low'


def generate_narrative(analysis, circumstances, uploaded_text=None, recipient_type=None, verbosity='concise'):
    # Compose a multi-paragraph narrative that reads like an LLM summary
    parts = []
    # Opening summary
    parts.append(f"Case summary: {analysis['summary']}")

    # If brief, give a short summary with risk and recommendation
    if verbosity == 'brief' or verbosity == 'concise':
        risk = assess_risk(circumstances, uploaded_text, recipient_type)
        parts.append(f"Risk assessment (heuristic): {risk}. Recommended next steps: {', '.join(analysis.get('suggestions',[]))}.")
        parts.append("Opinion: Based on the facts provided, a targeted compliance review is recommended. This is an analytical opinion, not legal advice.")
        if verbosity == 'brief':
            return "\n\n".join(parts)

    # For detailed verbosity, include authorities and compliance checks
    auths = analysis.get('authorities', [])
    if auths:
        listed = ', '.join([a.get('title') or a.get('url') for a in auths[:5]])
        parts.append(f"Primary authorities consulted: {listed}. Full reference list included in Additional References.")

    # Compliance checks
    checks = analysis.get('compliance_checks', [])
    if checks:
        chk_text = '; '.join([f"{c['section']} ({c['topic']})" for c in checks])
        parts.append(f"Key compliance areas to review: {chk_text}.")

    # Fact-check summary: count authorities that returned a fetched title vs raw URL
    reachable = 0
    for a in auths:
        t = a.get('title','')
        u = a.get('url','')
        if t and t != u:
            reachable += 1
    parts.append(f"Fact-check: {reachable} of the primary sources returned identifiable titles when fetched; consult the Additional References for direct links and to verify effective dates.")

    # Risk assessment
    risk = assess_risk(circumstances, uploaded_text, recipient_type)
    parts.append(f"Risk assessment (heuristic): {risk}. Recommended next steps: {', '.join(analysis.get('suggestions',[]))}.")

    # Tone and opinion paragraph (cautious)
    parts.append("Opinion: Based on the facts provided and the cited authorities, the situation appears to require targeted compliance review. This summary is an analytical opinion, not legal advice — confirm with counsel or agency policy before taking enforcement action.")

    return "\n\n".join(parts)


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
    # store recipient_type (also stored by build_analysis) and uploaded text for regeneration
    analysis['recipient_type'] = recipient_type
    if uploaded_name:
        analysis['uploaded_text'] = uploaded_text

    uid = save_analysis(analysis)
    share_url = url_for("share", uid=uid, _external=True)
    return render_template("result.html", analysis=analysis, share_url=share_url)


@app.route("/share/<uid>")
def share(uid):
    data = load_analysis(uid)
    if not data:
        abort(404)
    return render_template("result.html", analysis=data, share_url=request.url)


@app.route('/narrative_regen', methods=['POST'])
def narrative_regen():
    payload = request.get_json() or {}
    uid = payload.get('uid')
    verbosity = payload.get('verbosity', 'concise')
    if not uid:
        return {'error': 'uid required'}, 400
    analysis = load_analysis(uid)
    if not analysis:
        return {'error': 'analysis not found'}, 404

    circumstances = analysis.get('summary', '')
    uploaded_text = analysis.get('uploaded_text') or analysis.get('uploaded_text_snippet')
    recipient_type = analysis.get('recipient_type')
    new_summary = generate_narrative(analysis, circumstances, uploaded_text=uploaded_text, recipient_type=recipient_type, verbosity=verbosity)
    # update stored analysis
    analysis['narrative_summary'] = new_summary
    try:
        path = os.path.join(os.path.dirname(__file__), 'data', f"{uid}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return {'summary': new_summary}


@app.route('/whoami')
def whoami():
    # Only allow this test endpoint when TRUST_AUTH_PROXY is enabled to avoid leaking info
    try:
        if not TRUST_AUTH_PROXY:
            return {'error': 'TRUST_AUTH_PROXY not enabled'}, 403
    except Exception:
        return {'error': 'server misconfigured'}, 500

    user = request.headers.get(AUTH_PROXY_HEADER) or request.environ.get('REMOTE_USER') or None
    # fallback to basic auth username if present
    if not user and request.authorization:
        user = request.authorization.username
    return {'user': user or 'anonymous'}





if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


 

