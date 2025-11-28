@echo off
REM Windows batch script to update version from changelog
REM Usage: update_version.bat [--check-only] [--force]

cd /d "%~dp0"
python update_version.py %*

