#!/usr/bin/env python3
"""Run LendSight - designed to be called via utils/run_python_script.py"""
import subprocess
import sys
from pathlib import Path

# Use C:\DREAM\justdata path
dream_path = Path(r"C:\DREAM\justdata")
script_path = dream_path / "run_lendsight.py"
python_exe = sys.executable

if not script_path.exists():
    print(f"ERROR: Script not found at {script_path}")
    sys.exit(1)

# Use subprocess with shell=False - this is the key
cmd = [str(python_exe), str(script_path)]

print("Starting LendSight on port 8082...")
print(f"Command: {' '.join(cmd)}")
print(f"Working directory: {dream_path}")
print()

try:
    result = subprocess.run(
        cmd,
        shell=False,  # Critical: bypasses PowerShell
        cwd=str(dream_path),
        check=False
    )
    sys.exit(result.returncode)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

