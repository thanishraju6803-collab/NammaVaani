@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found.
  echo First run: py -m venv .venv
  echo Then run: .venv\Scripts\python -m pip install -r requirements.txt
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python -m uvicorn web_app:app --host 127.0.0.1 --port 8000
pause
