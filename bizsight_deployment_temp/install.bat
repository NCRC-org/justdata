@echo off
echo ========================================
echo BizSight Installation Script
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.8 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo [1/3] Checking Python version...
python --version

echo.
echo [2/3] Installing Python packages...
pip install --upgrade pip
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip
    pause
    exit /b 1
)

pip install -r apps\bizsight\requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [3/3] Installing Playwright browser...
playwright install chromium
if errorlevel 1 (
    echo [WARNING] Playwright installation failed. PDF export may not work.
)

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Copy .env.example to .env
echo 2. Edit .env and add your API keys
echo 3. Place bigquery_service_account.json in credentials\ directory
echo 4. Run: run_bizsight.bat
echo.
pause
