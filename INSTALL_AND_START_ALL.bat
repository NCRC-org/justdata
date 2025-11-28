@echo off
echo ============================================================
echo Installing Dependencies and Starting All Applications
echo ============================================================
echo.

echo Step 1: Installing required Python packages...
echo.

echo Installing Flask...
pip install flask>=2.3.0
if errorlevel 1 (
    echo ERROR: Failed to install Flask
    pause
    exit /b 1
)

echo Installing python-dotenv...
pip install python-dotenv
if errorlevel 1 (
    echo ERROR: Failed to install python-dotenv
    pause
    exit /b 1
)

echo Installing other dependencies...
pip install pandas google-cloud-bigquery openpyxl anthropic openai numpy
if errorlevel 1 (
    echo WARNING: Some packages may have failed to install
)

echo.
echo Step 2: Installing all requirements from requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo WARNING: Some requirements may have failed to install
    echo Continuing anyway...
)

echo.
echo ============================================================
echo Starting All Four Applications
echo ============================================================
echo.

echo Starting BranchSeeker on port 8080...
start "BranchSeeker (Port 8080)" cmd /k "cd /d %~dp0 && python run_branchseeker.py"

timeout /t 2 /nobreak >nul

echo Starting LendSight on port 8082...
start "LendSight (Port 8082)" cmd /k "cd /d %~dp0 && python run_lendsight.py"

timeout /t 2 /nobreak >nul

echo Starting MergerMeter on port 8083...
start "MergerMeter (Port 8083)" cmd /k "cd /d %~dp0 && python run_mergermeter.py"

timeout /t 2 /nobreak >nul

echo Starting BranchMapper on port 8084...
start "BranchMapper (Port 8084)" cmd /k "cd /d %~dp0 && python run_branchmapper.py"

echo.
echo ============================================================
echo All applications have been started!
echo.
echo Application URLs:
echo   BranchSeeker:   http://127.0.0.1:8080
echo   LendSight:      http://127.0.0.1:8082
echo   MergerMeter:    http://127.0.0.1:8083
echo   BranchMapper:   http://127.0.0.1:8084
echo.
echo Wait a few seconds for servers to start, then check:
echo   check_servers.bat
echo ============================================================
pause

