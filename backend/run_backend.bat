@echo off
echo Starting Media Search Backend...
call venv\Scripts\activate.bat
set PYTHONUNBUFFERED=1
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
