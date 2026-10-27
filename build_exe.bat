@echo off
REM Builds a standalone AladinMovieSplitter.exe with PyInstaller (output: dist\AladinMovieSplitter.exe).
REM Optional: put ffmpeg.exe and ffprobe.exe in a folder named "ffmpeg" next to this file to bundle them.
setlocal
cd /d "%~dp0"

where python >nul 2>nul || (echo Python 3.11+ is required. & pause & exit /b 1)
if not exist ".venv\Scripts\python.exe" python -m venv .venv
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt || (echo Install failed. & pause & exit /b 1)

set "EXTRA="
if exist "ffmpeg\ffmpeg.exe" if exist "ffmpeg\ffprobe.exe" set "EXTRA=--add-binary ffmpeg\ffmpeg.exe;ffmpeg --add-binary ffmpeg\ffprobe.exe;ffmpeg"
set "ICON="
if exist "assets\app_icon.ico" set "ICON=--icon assets\app_icon.ico"

".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name AladinMovieSplitter %ICON% %EXTRA% main.py
if errorlevel 1 (echo Build failed. & pause & exit /b 1)

echo.
echo Done: dist\AladinMovieSplitter.exe
pause
endlocal
