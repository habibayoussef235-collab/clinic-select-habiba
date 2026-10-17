@echo off
echo Starting Clinic Select...
echo.
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    venv\Scripts\pip install -r requirements.txt
)
venv\Scripts\python app.py
pause
