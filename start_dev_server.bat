@echo off
echo ========================================
echo Starting BranchSeeker Development Server
echo ========================================
echo.
echo Server will be available at: http://127.0.0.1:8080
echo.
echo The server is running in DEBUG mode, so:
echo - Template changes will auto-reload
echo - You can see changes by refreshing your browser
echo.
echo Press Ctrl+C to stop the server
echo.
echo ========================================
echo.

cd /d %~dp0
python run_branchseeker.py

