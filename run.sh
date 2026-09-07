#!/usr/bin/env bash
set -euo pipefail
echo "Installing Python requirements..."
python -m pip install -r requirements.txt
echo "Starting app on 0.0.0.0:8080"
exec waitress-serve --listen=0.0.0.0:8080 app:app
