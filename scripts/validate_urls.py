import requests
from bs4 import BeautifulSoup
import os

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
