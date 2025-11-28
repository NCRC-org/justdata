@echo off
echo ================================================================================
echo Restarting DataExplorer Server
echo ================================================================================
echo.

echo Step 1: Finding and killing existing server processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8085 ^| findstr LISTENING') do (
    echo Killing process %%a...
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo Step 2: Waiting for port to be released...
timeout /t 3 /nobreak >nul

echo.
echo Step 3: Starting server...
start "DataExplorer Server" python run_dataexplorer.py

echo.
echo ================================================================================
echo Server restart complete!
echo ================================================================================
echo.
echo The server should be starting in a new window.
echo Wait a few seconds, then:
echo   1. Hard refresh your browser: Ctrl+Shift+R
echo   2. Run verification: python apps\dataexplorer\verify_changes.py
echo.
pause

