@echo off
cd /d "%~dp0"
echo Running ProPublica API matching test with schema analysis...
echo.
python analyze_and_test_propublica.py
echo.
pause

