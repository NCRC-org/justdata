@echo off
echo Installing duckduckgo-search library...
pip install duckduckgo-search

echo.
echo Running email search script...
python find_missing_emails.py

pause















