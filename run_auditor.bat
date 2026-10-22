@echo off
rem Starts the Repo Auditor Pro web app on http://127.0.0.1:8765
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Mungon .venv - krijoje me: python -m venv .venv
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -q -r auditor_app\requirements.txt
start "" http://127.0.0.1:8765
".venv\Scripts\python.exe" -m uvicorn auditor_app.server:app --host 127.0.0.1 --port 8765
