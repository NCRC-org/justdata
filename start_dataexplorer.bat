@echo off
echo ================================================================================
echo Starting DataExplorer Server (Killing existing servers first)
echo ================================================================================
echo.

echo Step 1: Finding and killing existing Python servers on port 8085...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8085 ^| findstr LISTENING') do (
    echo   Killing process %%a...
    taskkill /F /PID %%a >nul 2>&1
    if errorlevel 1 (
        echo   Process %%a not found or already stopped
    ) else (
        echo   Successfully killed process %%a
    )
)

echo.
echo Step 2: Waiting for port to be released...
timeout /t 2 /nobreak >nul

echo.
echo Step 3: Starting DataExplorer server...
echo   Server will run in this window. Press Ctrl+C to stop.
echo.
start "DataExplorer Server" python run_dataexplorer.py

echo.
echo ================================================================================
echo Server started!
echo ================================================================================
echo.
echo The server should be running in a new window.
echo Wait a few seconds for it to start, then open:
echo   http://127.0.0.1:8085
echo.
pause

