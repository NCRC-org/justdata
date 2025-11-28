@echo off
cd /d "%~dp0"
echo Starting BranchMapper...
echo Access at: http://localhost:8084
python -m apps.branchmapper.app
pause
