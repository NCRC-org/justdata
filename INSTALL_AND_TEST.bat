@echo off
echo ============================================================
echo Installing python-dotenv and Testing Claude API
echo ============================================================
echo.

echo Step 1: Installing python-dotenv...
pip install python-dotenv
if errorlevel 1 (
    echo ERROR: Failed to install python-dotenv
    pause
    exit /b 1
)
echo.
echo Step 2: Testing Claude API...
echo.
python test_claude_simple.py

pause

