@echo off
echo Clearing Python cache...
for /d /r apps\bizsight %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /r apps\bizsight %%f in (*.pyc) do @if exist "%%f" del /q "%%f"

echo Stopping server on port 8081...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8081 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
timeout /t 2 /nobreak >nul

echo Starting server...
set DEBUG=True
set FLASK_DEBUG=1
python -m apps.bizsight.app

