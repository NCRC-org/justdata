@echo off
cd /d "C:\DREAM\justdata"
echo ============================================================
echo Restarting All Applications with CSS Fix
echo ============================================================
echo.

echo Stopping any existing instances...
taskkill /FI "WINDOWTITLE eq BranchSeeker*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq LendSight*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq MergerMeter*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq BranchMapper*" /T /F >nul 2>&1
timeout /t 2 /nobreak >nul

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
echo All applications have been restarted!
echo ============================================================
echo.
echo Application URLs (CSS should now work):
echo   BranchSeeker:   http://127.0.0.1:8080
echo   LendSight:      http://127.0.0.1:8082
echo   MergerMeter:    http://127.0.0.1:8083
echo   BranchMapper:   http://127.0.0.1:8084
echo.
echo Wait a few seconds for servers to start, then refresh your browser.
echo ============================================================
pause

