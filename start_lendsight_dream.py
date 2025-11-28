#!/usr/bin/env python3
"""Start LendSight using C:\DREAM\justdata path with subprocess shell=False."""
import subprocess
import sys
from pathlib import Path

# Use C:\DREAM\justdata to avoid apostrophe issues
dream_path = Path(r"C:\DREAM\justdata")
script_path = dream_path / "run_lendsight.py"
python_exe = sys.executable

print(f"Using C:\DREAM\justdata path to bypass apostrophe issue")
print(f"Script: {script_path}")
print(f"Python: {python_exe}")
print()

if not script_path.exists():
    print(f"ERROR: Script not found at {script_path}")
    print(f"Please verify C:\DREAM\justdata exists and contains run_lendsight.py")
    sys.exit(1)

# Build command as list - this bypasses PowerShell
cmd = [str(python_exe), str(script_path)]

print(f"Executing: {' '.join(cmd)}")
print("Starting LendSight on port 8082...")
print()

try:
    # Use subprocess with shell=False to bypass PowerShell entirely
    process = subprocess.Popen(
        cmd,
        shell=False,  # Critical: bypasses PowerShell wrapper
        cwd=str(dream_path),
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    print(f"✓ LendSight process started (PID: {process.pid})")
    print("Server should be available at: http://127.0.0.1:8082")
    print()
    print("Process is running. Press Ctrl+C to stop.")
    
    # Wait for the process
    process.wait()
except KeyboardInterrupt:
    print("\nStopping LendSight...")
    process.terminate()
    process.wait()
    print("Stopped.")
except Exception as e:
    print(f"ERROR: Could not start LendSight: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

