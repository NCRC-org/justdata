@echo off
echo ========================================
echo Creating BizSight Deployment Package
echo ========================================
echo.

cd /d "%~dp0apps\bizsight"
if not exist "create_deployment_package.py" (
    echo ERROR: create_deployment_package.py not found!
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo Running packaging script...
echo.
python create_deployment_package.py

if errorlevel 1 (
    echo.
    echo ERROR: Package creation failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Package creation complete!
echo Check your Downloads folder for the ZIP file.
echo ========================================
pause


