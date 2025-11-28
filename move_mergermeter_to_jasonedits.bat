@echo off
REM Move MergerMeter to JasonEdits branch - Batch file to bypass PowerShell
REM This uses cmd.exe directly, avoiding PowerShell wrapper issues

cd /d "%~dp0"
echo ============================================================
echo MergerMeter Migration to JasonEdits Branch
echo ============================================================
echo.

echo Step 1: Checking current branch...
git status
echo.

echo Step 2: Fetching latest from remote...
git fetch
echo.

echo Step 3: Switching to JasonEdits branch...
git checkout JasonEdits 2>nul || git checkout -b JasonEdits origin/JasonEdits 2>nul || git checkout -b JasonEdits
echo.

echo Step 4: Pulling latest changes...
git pull origin JasonEdits
echo.

echo Step 5: Staging MergerMeter files...
git add apps/mergermeter/
git add run_mergermeter.py
git add shared/
echo.

echo Step 6: Showing staged changes...
git status
echo.

echo Step 7: Committing changes...
git commit -m "Fix MergerMeter for GitHub merge - remove hard-coded paths, add graceful fallbacks, add README"
echo.

echo Step 8: Final status...
git status
echo.

echo ============================================================
echo Migration Complete!
echo ============================================================
echo.
echo Next Steps:
echo 1. Review the changes with: git log -1
echo 2. Push to JasonEdits branch: git push origin JasonEdits
echo 3. Verify on GitHub that changes are on JasonEdits branch
echo.
echo Remember: Always push to origin JasonEdits, never to origin main!
echo ============================================================
echo.
pause

