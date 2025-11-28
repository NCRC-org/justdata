@echo off
cd /d "C:\DREAM\#JustData_Repo"
echo Starting LendSight on port 8082...
echo.
start "LendSight (Port 8082)" cmd /k "cd /d C:\DREAM\#JustData_Repo && python run_lendsight.py"
echo.
echo LendSight is starting in a new window.
echo Open your browser and go to: http://127.0.0.1:8082
echo.
pause

