@echo off
cd /d "%~dp0"
echo ========================================
echo Starting BizSight Application
echo ========================================
echo.
echo Access the application at: http://localhost:8081
echo Press Ctrl+C to stop the server
echo.
python -m apps.bizsight.app
pause
