@echo off
cd /d "%~dp0"
echo Starting BranchSeeker...
echo Access at: http://localhost:8080
python -m apps.branchseeker.app
pause
