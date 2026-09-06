import requests
from bs4 import BeautifulSoup
import os
import json
from dotenv import load_dotenv

# load .env if present
load_dotenv()

# BLS integration: if BLS_API_KEY is set in the environment, the script will
# call the BLS JSON API for the configured series (BLS_SERIES env var) and
# print a short sample. Otherwise it falls back to a normal GET request.

BASE = os.path.join(os.path.dirname(__file__), '..')
SRC_FILE = os.path.join(BASE, 'allowed_sources.txt')

def load_sources(path):
    s = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            s.append(line)
    return s

def fetch_title(url):
    try:
        # Special-case BLS URL: if API key present, use BLS JSON API instead
        if 'bls.gov' in url:
            bls_key = os.environ.get('BLS_API_KEY')
            if bls_key:
                series_env = os.environ.get('BLS_SERIES')
                series = [s.strip() for s in series_env.split(',')] if series_env else ['CUUR0000SA0','SUUR0000SA0']
                payload = {"seriesid": series, "startyear": "2011", "endyear": "2014"}
                # include registration key field if present
                payload['registrationKey'] = bls_key
                headers = {'Content-type': 'application/json'}
                p = requests.post('https://api.bls.gov/publicAPI/v2/timeseries/data/', data=json.dumps(payload), headers=headers, timeout=15)
                if p.status_code == 200:
                    # indicate we used the API and return a short title-like summary
                    try:
                        j = p.json()
                        series_count = len(j.get('Results', {}).get('series', []))
                        title = f'BLS API response, series_count={series_count}'
                        return p.status_code, title, None
                    except Exception:
                        return p.status_code, 'BLS API (no JSON)', None
                else:
                    return p.status_code, 'BLS API error', None
            else:
                # no API key: try a browser UA to avoid naive bot blocks
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                r = requests.get(url, timeout=10, headers=headers)
        # Special-case govinfo: if API key present, include as query param
        elif 'govinfo.gov' in url:
            gov_key = os.environ.get('GOVINFO_API_KEY') or os.environ.get('API_KEY')
            if gov_key:
                r = requests.get(url, timeout=10, params={'api_key': gov_key})
            else:
                r = requests.get(url, timeout=10)
        else:
            r = requests.get(url, timeout=10)

        status = r.status_code
        ctype = r.headers.get('content-type','')
        title = ''
        if 'html' in ctype.lower():
            try:
                doc = BeautifulSoup(r.text, 'html.parser')
                title = doc.title.string.strip() if doc.title and doc.title.string else ''
            except Exception:
                title = ''
        else:
            title = ctype or ''
        return status, title, None
    except Exception as e:
        return None, None, str(e)

def main():
    sources = load_sources(SRC_FILE)
    print('Validating', len(sources), 'sources from', SRC_FILE)
    for u in sources:
        status, title, err = fetch_title(u)
        if err:
            print(f"URL: {u}\n  ERROR: {err}\n")
        else:
            print(f"URL: {u}\n  STATUS: {status}\n  TITLE: {title}\n")

if __name__ == '__main__':
    main()
