@echo off
cd /d "%~dp0"
echo Starting LendSight...
echo Access at: http://localhost:8082
python -m apps.lendsight.app
pause
