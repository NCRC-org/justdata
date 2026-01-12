@echo off
REM DataExplorer Docker Build Script (Windows)
REM Builds the Docker image for DataExplorer

setlocal enabledelayedexpansion

REM Configuration
set IMAGE_NAME=dataexplorer
set VERSION=%1
if "%VERSION%"=="" set VERSION=2.0.0
set REGISTRY=%2

echo Building DataExplorer Docker Image
echo Version: %VERSION%
echo.

REM Navigate to repository root
cd /d "%~dp0\..\.."

REM Build the image
echo Building Docker image...
docker build -f apps\dataexplorer\Dockerfile -t %IMAGE_NAME%:%VERSION% -t %IMAGE_NAME%:latest .

if %ERRORLEVEL% EQU 0 (
    echo Build successful!
    echo.
    echo Image: %IMAGE_NAME%:%VERSION%
    echo Image: %IMAGE_NAME%:latest
) else (
    echo Build failed
    exit /b 1
)

REM Optionally push to registry
if not "%REGISTRY%"=="" (
    echo.
    echo Pushing to registry: %REGISTRY%
    
    REM Tag for registry
    docker tag %IMAGE_NAME%:%VERSION% %REGISTRY%/%IMAGE_NAME%:%VERSION%
    docker tag %IMAGE_NAME%:latest %REGISTRY%/%IMAGE_NAME%:latest
    
    REM Push
    docker push %REGISTRY%/%IMAGE_NAME%:%VERSION%
    docker push %REGISTRY%/%IMAGE_NAME%:latest
    
    if %ERRORLEVEL% EQU 0 (
        echo Push successful!
        echo.
        echo Registry image: %REGISTRY%/%IMAGE_NAME%:%VERSION%
    ) else (
        echo Push failed
        exit /b 1
    )
)

echo.
echo Done!
echo.
echo To run the container:
echo   docker run -d --name dataexplorer -p 8085:8085 %IMAGE_NAME%:%VERSION%
