@echo off
echo ============================================================
echo Installing All Required Dependencies
echo ============================================================
echo.

echo Installing Flask and core dependencies...
pip install flask>=2.3.0 python-dotenv pandas google-cloud-bigquery openpyxl anthropic openai numpy
if errorlevel 1 (
    echo ERROR: Failed to install some core packages
    pause
    exit /b 1
)

echo.
echo Installing all requirements from requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo WARNING: Some requirements may have failed
    echo Check the output above for details
)

echo.
echo ============================================================
echo Installation Complete!
echo ============================================================
echo.
echo You can now start the applications with:
echo   START_ALL_SERVERS.bat
echo   or
echo   start_all_apps.bat
echo.
pause

