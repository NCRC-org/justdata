@echo off
REM Use DREAM launcher utility to bypass PowerShell wrapper
cd /d "C:\DREAM"
python utils\run_python_script.py justdata\test_claude_api_connection.py
pause
