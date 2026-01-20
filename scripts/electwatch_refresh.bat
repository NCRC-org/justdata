@echo off
REM ElectWatch Weekly Data Refresh
REM Run this manually or via Windows Task Scheduler
REM Log file saved to Desktop

set LOGFILE=%USERPROFILE%\Desktop\electwatch_refresh_log.txt

echo ======================================== >> "%LOGFILE%"
echo ElectWatch Weekly Refresh >> "%LOGFILE%"
echo Started: %date% %time% >> "%LOGFILE%"
echo ======================================== >> "%LOGFILE%"

cd /d "C:\Users\edite\OneDrive - NCRC\Code\JustData"

REM Activate virtual environment if you have one (uncomment if needed)
REM call venv\Scripts\activate.bat

REM Run the refresh and log output
python -m justdata.apps.electwatch.weekly_update >> "%LOGFILE%" 2>&1

echo ======================================== >> "%LOGFILE%"
echo Finished: %date% %time% >> "%LOGFILE%"
echo ======================================== >> "%LOGFILE%"

REM Optional: Commit the data to git (uncomment to enable auto-commit)
REM git add justdata/apps/electwatch/data/current/
REM git commit -m "ElectWatch weekly data refresh %date%"
REM git push
