#!/usr/bin/env python3
"""Run the batch file that starts LendSight using subprocess shell=False."""
import subprocess
import sys
from pathlib import Path

# The batch file that works
batch_file = Path(r"C:\DREAM\justdata\run_all.bat")

# But we only want LendSight, so let's create a simple command
dream_path = Path(r"C:\DREAM\justdata")
script_path = dream_path / "run_lendsight.py"
python_exe = sys.executable

print("Starting LendSight using C:\\DREAM\\justdata path...")
print(f"Path: {dream_path}")
print(f"Script: {script_path}")
print()

if not script_path.exists():
    print(f"ERROR: Script not found at {script_path}")
    sys.exit(1)

# Build the exact command the batch file uses
# start "LendSight (Port 8082)" cmd /k "cd /d C:\DREAM\justdata && python run_lendsight.py"
cmd = [
    "cmd.exe",
    "/c",
    f'start "LendSight (Port 8082)" cmd /k "cd /d {dream_path} && {python_exe} run_lendsight.py"'
]

print(f"Executing: {' '.join(cmd)}")
print()

try:
    # Use subprocess with shell=False
    result = subprocess.Popen(
        cmd,
        shell=False,
        cwd=str(dream_path)
    )
    print("✓ Command executed - LendSight should be starting in a new window")
    print("Check: http://127.0.0.1:8082")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

