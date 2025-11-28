@echo off
REM Quick verification script for DataExplorer changes
REM Run this after making code changes to verify they're active

echo ================================================================================
echo DataExplorer Change Verification
echo ================================================================================
echo.

python apps/dataexplorer/verify_changes.py

echo.
echo ================================================================================
echo If verification passed, hard refresh your browser: Ctrl+Shift+R
echo ================================================================================
pause

