@echo off
echo ================================================================================
echo CLEARING ALL FLASK AND PYTHON CACHES
echo ================================================================================

echo.
echo Clearing Python bytecode cache for bizsight...
for /d /r apps\bizsight %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /r apps\bizsight %%f in (*.pyc) do @if exist "%%f" del /q "%%f"

echo.
echo Clearing Python bytecode cache for dataexplorer...
for /d /r apps\dataexplorer %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /r apps\dataexplorer %%f in (*.pyc) do @if exist "%%f" del /q "%%f"

echo.
echo Clearing Jinja2 template cache for bizsight...
for /d /r apps\bizsight\templates %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /r apps\bizsight\templates %%f in (*.pyc) do @if exist "%%f" del /q "%%f"

echo.
echo Clearing Jinja2 template cache for dataexplorer...
for /d /r apps\dataexplorer\templates %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /r apps\dataexplorer\templates %%f in (*.pyc) do @if exist "%%f" del /q "%%f"

echo Clearing Flask instance cache...
if exist apps\bizsight\instance rd /s /q apps\bizsight\instance
if exist apps\dataexplorer\instance rd /s /q apps\dataexplorer\instance

echo.
echo Stopping servers...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8081 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
timeout /t 2 /nobreak >nul

echo.
echo ================================================================================
echo CACHE CLEARED - Servers stopped
echo ================================================================================
echo.
echo To restart the server:
echo   For bizsight: python -m apps.bizsight.app
echo   For dataexplorer: python -m apps.dataexplorer.app
echo.
pause

