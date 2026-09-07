@echo off
REM Install dependencies and run the app with waitress on 0.0.0.0:8080
python -m pip install -r requirements.txt
echo Starting app on 0.0.0.0:8080
waitress-serve --listen=0.0.0.0:8080 app:app
