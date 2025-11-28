@echo off
cd /d "C:\DREAM\justdata"
echo ============================================================
echo Verifying, Cleaning, and Starting All Applications
echo ============================================================
echo.

echo Step 1: Verifying dependencies...
python -c "import flask; print('Flask:', flask.__version__)" 2>nul || echo Flask: NOT INSTALLED
python -c "from dotenv import load_dotenv; print('python-dotenv: OK')" 2>nul || echo python-dotenv: NOT INSTALLED
echo.

echo Step 2: Cleaning up unneeded files...
if exist "_backup_before_flatten" rmdir /s /q "_backup_before_flatten" && echo   Removed _backup_before_flatten
if exist "justdata" rmdir /s /q "justdata" && echo   Removed leftover justdata folder
if exist "2.3.0" del /q "2.3.0" && echo   Removed stray file 2.3.0
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
echo Wait a few seconds for servers to start.
echo ============================================================
pause

