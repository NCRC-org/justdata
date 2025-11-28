@echo off
cd /d "%~dp0"
cd apps\bizsight
python create_deployment_package.py
pause


