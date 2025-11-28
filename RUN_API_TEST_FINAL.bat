@echo off
REM Run API test using C:\dream symbolic link to avoid apostrophe issue
cd /d "C:\dream\#JustData_Repo"
echo ========================================================================
echo Running ProPublica API Test
echo ========================================================================
python execute_inline.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Script failed with exit code %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)
echo.
echo ========================================================================
echo Test completed successfully!
echo ========================================================================
pause

