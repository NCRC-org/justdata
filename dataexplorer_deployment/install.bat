@echo off
echo Installing DataExplorer Dependencies...
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
pip install -r apps\dataexplorer\requirements.txt

echo.
echo Installation complete!
echo.
echo Next steps:
echo 1. Copy .env.example to .env and fill in your values
echo 2. Place bigquery_service_account.json in credentials\ directory
echo 3. Add your Census API key to .env file
echo 4. Run: python run_dataexplorer.py
echo.
pause
