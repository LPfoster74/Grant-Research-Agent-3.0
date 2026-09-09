"""
USFS Federal Financial Assistance Query Agent
Standalone CLI script version converted from the provided plain-language prompt.

Usage:
  python app.py --circumstances "Describe the issue" [--cfda CFDA] [--recipient RecipientType]

The script produces a structured, authoritative-style analysis consistent with the
Required Response Structure in the prompt. It does not call any external LLM APIs.
"""

import argparse
import json
import os
import requests
import sys
from datetime import datetime

AGENT_PROMPT = """
Role & Mission
You are the Federal Financial Assistance Query Agent for the United States Forest Service (USFS). Your purpose is to help USFS personnel interpret, apply, and understand requirements related to Federal Financial Assistance (US Federal Grants) across the entire grant lifecycle (pre‑award, post‑award, closeout). You provide accurate, authoritative, and concise guidance rooted in official regulations, policies, and authoritative federal sources.

Core Responsibilities

Interpret & Summarize Queries
• Read user questions carefully and restate them briefly to confirm understanding.
• Identify key regulatory or program components implied by the question.

Analyze Facts & Circumstances
• Incorporate any provided context such as CFDA number, program details, or recipient type.
• When context is missing, ask only the minimum number of clarifying questions necessary.

Research & Synthesize Information
• Consult 1–2 authoritative source areas relevant to the specific query.
• Prioritize the most current codified regulations, policies, and guidance.
• Ensure all referenced sources are official (.gov, .mil, .edu, or USFS SharePoint).

Provide Actionable Guidance
• Produce clear, plain‑language explanations—not raw citations.
• Highlight regulatory requirements, compliance obligations, limitations, and timelines.
"""

# Default authoritative sources (can be extended via allowed_sources.txt)
DEFAULT_SOURCES = [
    "https://www.ecfr.gov/current/title-2/subtitle-A/chapter-II/part-200",
    "https://www.ecfr.gov/current/title-2/subtitle-B/chapter-IV/part-400",
    "https://www.ecfr.gov/current/title-2/subtitle-A/chapter-I/part-180",
    "https://uscode.house.gov",
]


def load_allowed_sources(path=None):
    base = os.path.dirname(__file__)
    src = path or os.path.join(base, "allowed_sources.txt")
    sources = []
    try:
        with open(src, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                sources.append(line)
    except Exception:
        sources = []
    # ensure defaults present
    for d in DEFAULT_SOURCES:
        if d not in sources:
            sources.append(d)
    # dedupe preserving order
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
        r = requests.get(url, timeout=4)
        if r.status_code == 200:
            # naive title extraction
            text = r.text
            start = text.find('<title>')
            if start != -1:
                end = text.find('</title>', start)
                if end != -1:
                    return text[start + 7:end].strip()
        return url
    except Exception:
        return url


def assess_risk_text(text):
    t = (text or "").lower()
    score = 0
    for k in ['fraud', 'unauthorized', 'noncompliance', 'debar', 'suspend', 'penalty']:
        if k in t:
            score += 3
    for k in ['indirect cost', 'matching', 'cost principles', 'audit', 'allowable']:
        if k in t:
            score += 1
    if score >= 4:
        return 'High'
    if score >= 2:
        return 'Moderate'
    return 'Low'


def build_analysis(circumstances, cfda=None, recipient_type='Other'):
    """Create a structured analysis dictionary using the agent rules."""
    summary = circumstances.strip()
    if cfda:
        summary = f"{summary} (CFDA: {cfda.strip()})"
    summary = f"User inquiry regarding: {summary}. Recipient type: {recipient_type}."

    # authorities (top 3)
    authorities = []
    for url in ALLOWED_SOURCES[:3]:
        authorities.append({"url": url, "title": fetch_title(url)})

    # key compliance areas (simple mapping)
    compliance_checks = [
        {"section": "2 CFR 200.400-200.475", "topic": "Cost Principles (allowable, allocable, reasonable)"},
        {"section": "2 CFR 200.300-200.309", "topic": "Pre-award requirements & risk assessment"},
        {"section": "2 CFR 200.330-200.332", "topic": "Subrecipient monitoring & pass-through responsibilities"},
    ]

    key_requirements = [
        "Document allowability and allocability per 2 CFR Part 200 Subpart E",
        "Track and document matching/contributed funds where required",
        "Retain records consistent with federal retention and audit requirements",
    ]

    suggestions = [
        "Provide estimated award amount and period of performance",
        "Indicate whether the entity is a subrecipient or contractor",
        "Attach relevant award terms or NOFO language if available",
    ]

    narrative = generate_narrative(summary, circumstances, recipient_type)

    analysis = {
        "summary": summary,
        "authorities": authorities,
        "compliance_checks": compliance_checks,
        "key_requirements": key_requirements,
        "suggestions": suggestions,
        "narrative_summary": narrative,
        "risk": assess_risk_text(circumstances),
        "agent_prompt": AGENT_PROMPT,
        "timestamp": datetime.utcnow().isoformat() + 'Z',
    }
    return analysis


def generate_narrative(summary, circumstances, recipient_type):
    risk = assess_risk_text(circumstances)
    parts = []
    parts.append(f"Case summary: {summary}")
    parts.append(f"Risk assessment (heuristic): {risk}.")
    parts.append("Applicable authorities: see Additional References.")
    parts.append("Recommended next steps: gather award documents, confirm recipient classification, and verify allowability under 2 CFR Part 200.")
    parts.append("Opinion: This is an analytical, non-binding summary based on the facts provided and cited authorities.")
    return "\n\n".join(parts)


def print_analysis(analysis):
    print('\n=== Case Summary & Applicable Authorities ===\n')
    print(analysis['summary'] + '\n')
    print('Primary authorities:')
    for a in analysis['authorities']:
        print(f"- {a.get('title') or a.get('url')}: {a.get('url')}")
    print('\n=== Key Requirements ===\n')
    for k in analysis['key_requirements']:
        print(f"- {k}")
    print('\n=== Compliance Checks ===\n')
    for c in analysis['compliance_checks']:
        print(f"- {c['section']}: {c['topic']}")
    print('\n=== Risk & Recommendations ===\n')
    print(f"Risk level: {analysis['risk']}")
    print('\nRecommended actions:')
    for s in analysis['suggestions']:
        print(f"- {s}")
    print('\n=== Narrative ===\n')
    print(analysis['narrative_summary'])
    print('\n=== Agent Prompt (embedded) ===\n')
    print(AGENT_PROMPT[:800] + ('... (truncated)' if len(AGENT_PROMPT) > 800 else ''))


def save_analysis(analysis, path=None):
    base = os.path.dirname(__file__)
    folder = os.path.join(base, 'data')
    os.makedirs(folder, exist_ok=True)
    uid = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    filename = path or os.path.join(folder, f"analysis_{uid}.json")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    return filename


def main(argv=None):
    p = argparse.ArgumentParser(description='USFS Federal Financial Assistance Query Agent (CLI)')
    p.add_argument('--circumstances', '-c', help='Circumstances prompting research', required=False)
    p.add_argument('--cfda', help='CFDA number (optional)', required=False)
    p.add_argument('--recipient', help='Recipient type (optional)', default='Other')
    p.add_argument('--save', help='Save analysis JSON to file (optional path)', required=False)
    args = p.parse_args(argv)

    if not args.circumstances:
        print('Enter the circumstances (single line). Ctrl-D to finish:')
        try:
            args.circumstances = sys.stdin.read().strip()
        except Exception:
            args.circumstances = ''
    if not args.circumstances:
        print('No circumstances provided; exiting.')
        return 1

    analysis = build_analysis(args.circumstances, cfda=args.cfda, recipient_type=args.recipient)
    print_analysis(analysis)
    if args.save is not None:
        path = save_analysis(analysis, path=args.save)
        print(f"\nSaved analysis to: {path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
