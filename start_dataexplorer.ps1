# PowerShell script to kill existing servers and start DataExplorer
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "Starting DataExplorer Server (Killing existing servers first)" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Step 1: Finding and killing existing Python servers on port 8085..." -ForegroundColor Yellow
$processes = Get-NetTCPConnection -LocalPort 8085 -ErrorAction SilentlyContinue | 
    Where-Object { $_.State -eq "Listen" } | 
    Select-Object -ExpandProperty OwningProcess -Unique

if ($processes) {
    foreach ($pid in $processes) {
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "  Killing process $pid ($($proc.ProcessName))..." -ForegroundColor Red
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            Write-Host "  Successfully killed process $pid" -ForegroundColor Green
        }
    }
} else {
    Write-Host "  No processes found on port 8085" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Step 2: Waiting for port to be released..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Step 3: Starting DataExplorer server..." -ForegroundColor Yellow
Write-Host "  Server will run in this window. Press Ctrl+C to stop." -ForegroundColor Gray
Write-Host ""

# Start the server in a new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; python run_dataexplorer.py"

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "Server started!" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The server should be running in a new window." -ForegroundColor Gray
Write-Host "Wait a few seconds for it to start, then open:" -ForegroundColor Gray
Write-Host "  http://127.0.0.1:8085" -ForegroundColor Cyan
Write-Host ""

