@echo off
REM Batch script to start JustData API server and LendSight app

echo Starting JustData API server and LendSight app...
echo.

REM Start JustData API server on port 8000
echo Starting JustData API server on port 8000...
start "JustData API (Port 8000)" cmd /k "cd /d %~dp0 && python run.py"

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start LendSight on port 8082
echo Starting LendSight on port 8082...
start "LendSight (Port 8082)" cmd /k "cd /d %~dp0 && python run_lendsight.py"

echo.
echo Both servers have been started in separate windows.
echo.
echo Server URLs:
echo   JustData API:  http://localhost:8000
echo   API Docs:      http://localhost:8000/docs
echo   LendSight:     http://127.0.0.1:8082
echo.
echo You can close this window - the servers will continue running.
pause

