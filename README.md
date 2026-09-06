# Forest Service Grants Research (Prototype)

Local Flask app to summarize and analyze Federal Financial Assistance (grants) queries for Forest Service staff.

Quick start

1. Create a Python virtual environment and activate it.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Run the app

```bash
python app.py
```

3. Open http://127.0.0.1:5000 in your browser.

Notes
- The app references primary regulatory sources and includes a simple analysis scaffold. It fetches page titles from allowed sources when reachable.
- For production use, secure the app, add authentication, and integrate up-to-date regulatory data sources.
