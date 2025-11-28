@echo off
REM Package MergerMeter for deployment
cd /d "%~dp0"
python package_deployment.py
pause

