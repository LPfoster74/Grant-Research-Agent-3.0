# Grant Research Agent — Run & Share Guide

Short instructions to run the app on a developer machine, expose it to a local network, and demo with a tunnel (ngrok).

Prerequisites
- Python 3.10+ installed
- A virtual environment is recommended: `python -m venv .venv` then activate it

Install and run (LAN)
```bash
python -m pip install -r requirements.txt
# Run on all interfaces (LAN) using waitress
waitress-serve --listen=0.0.0.0:8080 app:app
```

Windows quick-run
```powershell
# From project root
python -m pip install -r requirements.txt
.\run.bat
```

Expose locally with ngrok (demo)
1. Install ngrok (https://ngrok.com/) and authenticate it.
2. Start the app on port 8080 as above.
3. Run:
```bash
ngrok http 8080
```
ngrok will give you a public HTTPS URL that tunnels to your local server.

Security notes
- The `/share/<uid>` links are accessible to anyone who can reach the server and have the URL.
- If analyses contain sensitive data, enable Basic Auth via environment variables before running:
  - `BASIC_AUTH_USERNAME` and `BASIC_AUTH_PASSWORD` (the app checks these when set)
- Prefer running behind HTTPS (ngrok provides TLS) and/or put the app behind corporate reverse proxy.

Example LAN URL
- If host IP is `10.0.1.25` and you run on port `8080`: `http://10.0.1.25:8080/share/<uid>`

Exact URL patterns
- UI (index) page: `http://<host-ip>:8080/`
- Saved analysis (share) page: `http://<host-ip>:8080/share/<uid>`
- Test SSO identity endpoint (when `TRUST_AUTH_PROXY=1`): `http://<host-ip>:8080/whoami`

Docker Compose example
- Start with:
```bash
docker compose up --build -d
```
This brings up the app and an nginx proxy on host port `8080`. Replace `<host-ip>` below with your host's LAN IP or DNS name.


Troubleshooting
- If the app only responds on `localhost`, ensure you launched with `waitress-serve --listen=0.0.0.0:8080` (Flask dev server binds to `127.0.0.1` by default).
- If colleagues cannot reach it, check the host firewall and corporate network firewall.

Single Sign-On (SSO) / Seamless access for network users
-------------------------------------------------------
If you want colleagues who are already signed into the corporate network to access the app immediately without entering credentials, run the app behind a reverse proxy that performs authentication (Kerberos/NTLM/Azure AD/OIDC) and then forwards an authenticated user header to the app.

1) General approach
- Configure a proxy (IIS, nginx, Apache, or a managed gateway) to perform SSO against your corporate IdP.
- Have the proxy set a header containing the authenticated username (for example `X-Remote-User` or `REMOTE_USER`).
- Run the app with `TRUST_AUTH_PROXY=1` in the environment and optionally set `AUTH_PROXY_HEADER` to the header name the proxy uses. When enabled, the app will trust that header and allow access without prompting for Basic Auth.

Environment variables (example)
```bash
export TRUST_AUTH_PROXY=1
export AUTH_PROXY_HEADER=X-Remote-User
# On Windows (PowerShell)
$env:TRUST_AUTH_PROXY = '1'
$env:AUTH_PROXY_HEADER = 'X-Remote-User'
```

2) nginx + Kerberos (example)
```nginx
server {
  listen 80;
  server_name grant-agent.local;

  location / {
    auth_gss on;
    auth_gss_realm EXAMPLE.COM;
    auth_gss_keytab /etc/httpd/keytabs/grant-agent.keytab;
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header X-Remote-User $remote_user;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }
}
```

3) IIS / Windows Authentication (example)
- In IIS, enable Windows Authentication for the site and disable Anonymous Authentication.
- Configure the IIS Application Request Routing (ARR) or reverse proxy to forward a header with the authenticated username, e.g., `X-Remote-User`.

4) Security note
- Only enable `TRUST_AUTH_PROXY` if the app is running behind a proxy you control and trust. Accepting arbitrary headers from the public Internet is insecure.
- Prefer TLS between clients and the proxy, and between proxy and the app when possible.

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
