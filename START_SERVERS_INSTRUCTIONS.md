# Starting All Four Applications

## Quick Start

**Run this batch file to start all four applications:**
```cmd
START_ALL_SERVERS.bat
```

Or use the existing file:
```cmd
start_all_apps.bat
```

## What Happens

The batch file will:
1. Open 4 separate command windows (one for each application)
2. Start each application in its own window
3. Display the URLs for each application

## Application URLs

Once started, access the applications at:

- **BranchSeeker**: http://127.0.0.1:8080
- **LendSight**: http://127.0.0.1:8082
- **MergerMeter**: http://127.0.0.1:8083
- **BranchMapper**: http://127.0.0.1:8084

## Verify They're Running

After starting, wait a few seconds, then run:
```cmd
check_servers.bat
```

Or check manually:
```cmd
netstat -ano | findstr ":8080 :8082 :8083 :8084"
```

## Manual Start (Alternative)

If the batch file doesn't work, start each manually in separate terminals:

**Terminal 1:**
```cmd
python run_branchseeker.py
```

**Terminal 2:**
```cmd
python run_lendsight.py
```

**Terminal 3:**
```cmd
python run_mergermeter.py
```

**Terminal 4:**
```cmd
python run_branchmapper.py
```

## Stopping Servers

To stop a server, close its command window or press `Ctrl+C` in that window.

