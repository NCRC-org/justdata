@echo off
echo Installing BranchMapper Dependencies...
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Install dependencies
echo Installing Python packages...
pip install --upgrade pip
pip install -r apps\branchmapper\requirements.txt

echo.
echo Installation complete!
echo.
echo Next steps:
echo 1. Copy .env.example to .env and fill in your API keys
echo 2. Place bigquery_service_account.json in credentials\ directory
echo 3. Set CENSUS_API_KEY in .env file
echo 4. Run: python -m apps.branchmapper.app
echo.
pause
