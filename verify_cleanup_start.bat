@echo off
cd /d "C:\DREAM\justdata"
echo ============================================================
echo Verifying Installation, Cleaning Up, and Starting Apps
echo ============================================================
echo.

echo Step 1: Verifying dependencies...
python check_dependencies.py
if errorlevel 1 (
    echo.
    echo WARNING: Some dependencies may be missing
    echo Continuing anyway...
)
echo.

echo Step 2: Cleaning up unneeded files...
if exist "_backup_before_flatten" (
    rmdir /s /q "_backup_before_flatten"
    echo   Removed _backup_before_flatten
)
if exist "justdata" (
    rmdir /s /q "justdata"
    echo   Removed leftover justdata folder
)
if exist "cleanup_leftover.py" del /q "cleanup_leftover.py"
if exist "flatten_structure.py" del /q "flatten_structure.py"
if exist "install_missing.bat" del /q "install_missing.bat"
if exist "check_dependencies.py" del /q "check_dependencies.py"
if exist "cleanup_dream_justdata.py" del /q "cleanup_dream_justdata.py"
if exist "verify_and_start.bat" del /q "verify_and_start.bat"
if exist "2.3.0" del /q "2.3.0"
echo   Cleanup complete!
echo.

echo Step 3: Starting all four applications...
echo.

echo Starting BranchSeeker on port 8080...
start "BranchSeeker (Port 8080)" cmd /k "cd /d C:\DREAM\justdata && python run_branchseeker.py"

timeout /t 3 /nobreak >nul

echo Starting LendSight on port 8082...
start "LendSight (Port 8082)" cmd /k "cd /d C:\DREAM\justdata && python run_lendsight.py"

timeout /t 3 /nobreak >nul

echo Starting MergerMeter on port 8083...
start "MergerMeter (Port 8083)" cmd /k "cd /d C:\DREAM\justdata && python run_mergermeter.py"

timeout /t 3 /nobreak >nul

echo Starting BranchMapper on port 8084...
start "BranchMapper (Port 8084)" cmd /k "cd /d C:\DREAM\justdata && python run_branchmapper.py"

echo.
echo ============================================================
echo All applications have been started!
echo ============================================================
echo.
echo Application URLs:
echo   BranchSeeker:   http://127.0.0.1:8080
echo   LendSight:      http://127.0.0.1:8082
echo   MergerMeter:    http://127.0.0.1:8083
echo   BranchMapper:   http://127.0.0.1:8084
echo.
echo Wait a few seconds for servers to start, then check:
echo   check_servers.bat
echo.
echo Or visit the URLs above in your browser.
echo ============================================================
pause

