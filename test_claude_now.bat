@echo off
echo ============================================================
echo Testing Claude API Connection
echo ============================================================
echo.

REM Check if python-dotenv is installed
echo Checking for python-dotenv...
python -c "import dotenv" 2>nul
if errorlevel 1 (
    echo python-dotenv not found. Installing...
    pip install python-dotenv
    if errorlevel 1 (
        echo ERROR: Failed to install python-dotenv
        pause
        exit /b 1
    )
    echo python-dotenv installed successfully!
    echo.
) else (
    echo python-dotenv is already installed
    echo.
)

REM Copy .env file if it doesn't exist
if not exist .env (
    echo Copying .env file from C:\DREAM\justdata\...
    copy "C:\DREAM\justdata\.env" .env
    if errorlevel 1 (
        echo ERROR: Failed to copy .env file
        pause
        exit /b 1
    )
    echo .env file copied successfully!
    echo.
) else (
    echo .env file already exists
    echo.
)

REM Run the Python test
echo Running Claude API test...
echo.
python test_claude_simple.py

pause

