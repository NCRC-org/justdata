# NCRC Applications - Localhost URLs

## Quick Access URLs

All four applications are running on your local machine. Access them using these URLs:

### 1. LendSight - Mortgage Lending Analysis
**URL:** http://127.0.0.1:8082  
**Port:** 8082  
**Purpose:** Mortgage lending analysis and fair lending assessment

### 2. BranchSeeker - Bank Branch Location Analysis
**URL:** http://127.0.0.1:8080  
**Port:** 8080  
**Purpose:** Bank branch location analysis and market concentration assessment

### 3. BranchMapper - Interactive Branch Map
**URL:** http://127.0.0.1:8084  
**Port:** 8084  
**Purpose:** Interactive map visualization of bank branch locations

### 4. MergerMeter - Two-Bank Merger Impact Analysis
**URL:** http://127.0.0.1:8083  
**Port:** 8083  
**Purpose:** Two-bank merger impact analysis and CRA goal-setting assessment

---

## Starting All Applications

To start all four applications at once, run one of these commands:

### Windows PowerShell:
```powershell
.\start_all_apps.ps1
```

### Windows Command Prompt:
```cmd
start_all_apps.bat
```

### Manual Start (Individual):
```bash
# Terminal 1 - LendSight
python run_lendsight.py
# Then open: http://127.0.0.1:8082

# Terminal 2 - BranchSeeker
python run_branchseeker.py
# Then open: http://127.0.0.1:8080

# Terminal 3 - BranchMapper
python run_branchmapper.py
# Then open: http://127.0.0.1:8084

# Terminal 4 - MergerMeter
python run_mergermeter.py
# Then open: http://127.0.0.1:8083
```

---

## Application Status

All applications can run simultaneously on different ports. Each application runs independently and does not interfere with the others.

---

## Quick Reference

| Application | URL | Port | Status |
|-------------|-----|------|--------|
| LendSight | http://127.0.0.1:8082 | 8082 | Ready |
| BranchSeeker | http://127.0.0.1:8080 | 8080 | Ready |
| BranchMapper | http://127.0.0.1:8084 | 8084 | Ready |
| MergerMeter | http://127.0.0.1:8083 | 8083 | Ready |

