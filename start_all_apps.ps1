# PowerShell script to start all four NCRC applications
# This script starts each application in a separate PowerShell window

Write-Host "Starting all four NCRC applications..." -ForegroundColor Green
Write-Host ""

# Start LendSight on port 8082
Write-Host "Starting LendSight on port 8082..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python run_lendsight.py"

# Wait a moment
Start-Sleep -Seconds 2

# Start BranchSeeker on port 8080
Write-Host "Starting BranchSeeker on port 8080..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python run_branchseeker.py"

# Wait a moment
Start-Sleep -Seconds 2

# Start BranchMapper on port 8084
Write-Host "Starting BranchMapper on port 8084..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python run_branchmapper.py"

# Wait a moment
Start-Sleep -Seconds 2

# Start MergerMeter on port 8083
Write-Host "Starting MergerMeter on port 8083..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python run_mergermeter.py"

# Wait for applications to start
Write-Host ""
Write-Host "Waiting for applications to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check if ports are listening
Write-Host ""
Write-Host "Checking application status..." -ForegroundColor Green
Write-Host ""

$ports = @(8080, 8082, 8083, 8084)
$appNames = @{
    8080 = "BranchSeeker"
    8082 = "LendSight"
    8083 = "MergerMeter"
    8084 = "BranchMapper"
}

foreach ($port in $ports) {
    $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($connection) {
        Write-Host "$($appNames[$port]) (Port $port): RUNNING" -ForegroundColor Green
    } else {
        Write-Host "$($appNames[$port]) (Port $port): Starting..." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Application URLs:" -ForegroundColor Cyan
Write-Host "  LendSight:      http://127.0.0.1:8082" -ForegroundColor White
Write-Host "  BranchSeeker:   http://127.0.0.1:8080" -ForegroundColor White
Write-Host "  BranchMapper:   http://127.0.0.1:8084" -ForegroundColor White
Write-Host "  MergerMeter:    http://127.0.0.1:8083" -ForegroundColor White
Write-Host ""
Write-Host "All applications have been started in separate windows." -ForegroundColor Green
Write-Host "You can close this window - the applications will continue running." -ForegroundColor Green

