@echo off
REM Aladin Movie Splitter launcher: creates a virtual environment on first run, then starts the app.
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python 3.11 or newer was not found. Install it from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during setup.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv || (echo Failed to create the virtual environment. & pause & exit /b 1)
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || (echo Dependency installation failed. & pause & exit /b 1)
)

start "" ".venv\Scripts\pythonw.exe" main.py %*
endlocal
