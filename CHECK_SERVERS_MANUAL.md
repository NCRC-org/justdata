# Manual Server Status Check

Due to terminal issues, please run these commands manually in Command Prompt (cmd.exe):

## Quick Check Commands

### Option 1: Use the batch file
Open Command Prompt and run:
```cmd
check_servers.bat
```

### Option 2: Use Python script
```cmd
python check_servers.py
```

### Option 3: Manual netstat check
```cmd
netstat -ano | findstr ":8080 :8082 :8083 :8084"
```

## Expected Output

If servers are running, you'll see lines like:
```
TCP    0.0.0.0:8080           0.0.0.0:0              LISTENING       12345
TCP    0.0.0.0:8082           0.0.0.0:0              LISTENING       12346
TCP    0.0.0.0:8083           0.0.0.0:0              LISTENING       12347
TCP    0.0.0.0:8084           0.0.0.0:0              LISTENING       12348
```

## Application Ports

| Application | Port | URL |
|-------------|------|-----|
| BranchSeeker | 8080 | http://127.0.0.1:8080 |
| LendSight | 8082 | http://127.0.0.1:8082 |
| MergerMeter | 8083 | http://127.0.0.1:8083 |
| BranchMapper | 8084 | http://127.0.0.1:8084 |

## Quick Test

You can also test if a server is running by opening these URLs in your browser:
- http://127.0.0.1:8080 (BranchSeeker)
- http://127.0.0.1:8082 (LendSight)
- http://127.0.0.1:8083 (MergerMeter)
- http://127.0.0.1:8084 (BranchMapper)

If the page loads, the server is running. If you get "connection refused" or timeout, it's not running.

## Start Servers

To start all servers:
```cmd
start_all_apps.bat
```

Or start individually:
```cmd
python run_branchseeker.py
python run_lendsight.py
python run_mergermeter.py
python run_branchmapper.py
```

