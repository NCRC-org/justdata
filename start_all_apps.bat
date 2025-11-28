@echo off
REM Batch script to start all four NCRC applications
REM This script starts each application in a separate command window

echo Starting all four NCRC applications...
echo.

REM Start LendSight on port 8082
echo Starting LendSight on port 8082...
start "LendSight (Port 8082)" cmd /k "python run_lendsight.py"

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start BranchSeeker on port 8080
echo Starting BranchSeeker on port 8080...
start "BranchSeeker (Port 8080)" cmd /k "python run_branchseeker.py"

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start BranchMapper on port 8084
echo Starting BranchMapper on port 8084...
start "BranchMapper (Port 8084)" cmd /k "python run_branchmapper.py"

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Start MergerMeter on port 8083
echo Starting MergerMeter on port 8083...
start "MergerMeter (Port 8083)" cmd /k "python run_mergermeter.py"

echo.
echo All applications have been started in separate windows.
echo.
echo Application URLs:
echo   LendSight:      http://127.0.0.1:8082
echo   BranchSeeker:   http://127.0.0.1:8080
echo   BranchMapper:   http://127.0.0.1:8084
echo   MergerMeter:    http://127.0.0.1:8083
echo.
echo You can close this window - the applications will continue running.
pause

