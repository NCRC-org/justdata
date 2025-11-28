@echo off
echo ============================================================
echo Starting All Four NCRC Applications
echo ============================================================
echo.

echo Starting BranchSeeker on port 8080...
start "BranchSeeker (Port 8080)" cmd /k "python run_branchseeker.py"

timeout /t 2 /nobreak >nul

echo Starting LendSight on port 8082...
start "LendSight (Port 8082)" cmd /k "python run_lendsight.py"

timeout /t 2 /nobreak >nul

echo Starting MergerMeter on port 8083...
start "MergerMeter (Port 8083)" cmd /k "python run_mergermeter.py"

timeout /t 2 /nobreak >nul

echo Starting BranchMapper on port 8084...
start "BranchMapper (Port 8084)" cmd /k "python run_branchmapper.py"

echo.
echo ============================================================
echo All applications have been started in separate windows.
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

