@echo off
REM Switch to JasonEdits branch - Batch file to bypass PowerShell
cd /d "%~dp0"

echo ============================================================
echo Switching to JasonEdits Branch
echo ============================================================
echo.

echo Checking current branch...
git status
echo.

echo Fetching latest from remote...
git fetch
echo.

echo Switching to JasonEdits branch...
git checkout JasonEdits 2>nul
if errorlevel 1 (
    echo JasonEdits not found locally, checking remote...
    git checkout -b JasonEdits origin/JasonEdits 2>nul
    if errorlevel 1 (
        echo Creating new JasonEdits branch...
        git checkout -b JasonEdits
    )
)
echo.

echo Pulling latest changes...
git pull origin JasonEdits 2>nul
echo.

echo Current branch status:
git status
echo.

echo ============================================================
echo Successfully switched to JasonEdits branch!
echo ============================================================
echo.
pause

