#!/usr/bin/env python3
"""Start LendSight using subprocess with shell=False to bypass PowerShell."""
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent
python_exe = sys.executable
script_path = project_root / "run_lendsight.py"

# Use subprocess with shell=False to bypass PowerShell
cmd = [python_exe, str(script_path)]

print("Starting LendSight on port 8082...")
print(f"Command: {' '.join(cmd)}")
print(f"Working directory: {project_root}")

try:
    process = subprocess.Popen(
        cmd,
        shell=False,
        cwd=str(project_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    print(f"✓ LendSight process started (PID: {process.pid})")
    print("Server should be available at: http://127.0.0.1:8082")
    print("\nProcess is running in the background.")
    print("Press Ctrl+C to stop, or close this window.")
    
    # Keep the script running so the server stays up
    try:
        process.wait()
    except KeyboardInterrupt:
        print("\nStopping LendSight...")
        process.terminate()
        process.wait()
        print("LendSight stopped.")
except Exception as e:
    print(f"ERROR: Could not start LendSight: {e}")
    sys.exit(1)

