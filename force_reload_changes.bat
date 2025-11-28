@echo off
echo ================================================================================
echo FORCE RELOAD - DataExplorer Changes
echo ================================================================================
echo.
echo This script will:
echo   1. Kill the existing server
echo   2. Clear Python cache files
echo   3. Restart the server
echo   4. Test the API
echo.
pause

echo.
echo Step 1: Killing existing server...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8085 ^| findstr LISTENING') do (
    echo   Killing process %%a...
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo Step 2: Clearing Python cache...
for /d /r apps\dataexplorer %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
for /r apps\dataexplorer %%f in (*.pyc) do @if exist "%%f" del /q "%%f" 2>nul
echo   Cache cleared

echo.
echo Step 3: Waiting for port to be released...
timeout /t 3 /nobreak >nul

echo.
echo Step 4: Starting server in background...
start "DataExplorer Server" python run_dataexplorer.py

echo.
echo Step 5: Waiting for server to start...
timeout /t 5 /nobreak >nul

echo.
echo Step 6: Testing server...
python apps\dataexplorer\verify_changes.py

echo.
echo ================================================================================
echo IMPORTANT: Now do a HARD REFRESH in your browser:
echo   - Press Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
echo   - OR: Open DevTools (F12) → Network tab → Check "Disable cache"
echo ================================================================================
echo.
pause

