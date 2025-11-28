# Server Status Check

## Quick Check

Run this batch file to check which servers are running:
```bash
check_servers.bat
```

Or run the Python script:
```bash
python check_servers.py
```

## Application Ports

| Application | Port | URL | Status |
|-------------|------|-----|--------|
| BranchSeeker | 8080 | http://127.0.0.1:8080 | Check with script |
| LendSight | 8082 | http://127.0.0.1:8082 | Check with script |
| MergerMeter | 8083 | http://127.0.0.1:8083 | Check with script |
| BranchMapper | 8084 | http://127.0.0.1:8084 | Check with script |

## Manual Check

You can also manually check using:
```bash
netstat -ano | findstr "8080 8082 8083 8084"
```

## Start All Servers

To start all four servers:
```bash
start_all_apps.bat
```

Or start individually:
```bash
python run_branchseeker.py   # Port 8080
python run_lendsight.py      # Port 8082
python run_mergermeter.py    # Port 8083
python run_branchmapper.py   # Port 8084
```

