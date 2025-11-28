@echo off
echo ============================================================
echo NCRC Application Server Status Check
echo ============================================================
echo.

echo Checking ports 8080, 8082, 8083, 8084...
echo.

netstat -ano | findstr ":8080 " | findstr "LISTENING" >nul
if %errorlevel% == 0 (
    echo [OK] BranchSeeker   Port 8080 - RUNNING
    echo       URL: http://127.0.0.1:8080
) else (
    echo [X]  BranchSeeker   Port 8080 - NOT RUNNING
)
echo.

netstat -ano | findstr ":8082 " | findstr "LISTENING" >nul
if %errorlevel% == 0 (
    echo [OK] LendSight      Port 8082 - RUNNING
    echo       URL: http://127.0.0.1:8082
) else (
    echo [X]  LendSight      Port 8082 - NOT RUNNING
)
echo.

netstat -ano | findstr ":8083 " | findstr "LISTENING" >nul
if %errorlevel% == 0 (
    echo [OK] MergerMeter    Port 8083 - RUNNING
    echo       URL: http://127.0.0.1:8083
) else (
    echo [X]  MergerMeter    Port 8083 - NOT RUNNING
)
echo.

netstat -ano | findstr ":8084 " | findstr "LISTENING" >nul
if %errorlevel% == 0 (
    echo [OK] BranchMapper   Port 8084 - RUNNING
    echo       URL: http://127.0.0.1:8084
) else (
    echo [X]  BranchMapper   Port 8084 - NOT RUNNING
)
echo.

echo ============================================================
echo To start servers, run:
echo   python run_branchseeker.py   (Port 8080)
echo   python run_lendsight.py      (Port 8082)
echo   python run_mergermeter.py    (Port 8083)
echo   python run_branchmapper.py   (Port 8084)
echo.
echo Or use: start_all_apps.bat
echo ============================================================
pause

