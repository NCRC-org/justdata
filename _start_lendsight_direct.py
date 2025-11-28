#!/usr/bin/env python3
"""Direct launcher for LendSight - bypasses all wrappers."""
import subprocess
import sys
from pathlib import Path

# Get absolute paths
project_root = Path(__file__).parent.absolute()
script_path = project_root / "run_lendsight.py"
python_exe = sys.executable

print(f"Project root: {project_root}")
print(f"Script: {script_path}")
print(f"Python: {python_exe}")
print()

# Build command as list - this is the key
cmd = [str(python_exe), str(script_path)]

print(f"Executing: {' '.join(cmd)}")
print("Starting LendSight on port 8082...")
print()

try:
    # Use subprocess with shell=False - bypasses PowerShell
    process = subprocess.Popen(
        cmd,
        shell=False,  # Critical!
        cwd=str(project_root),
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    print(f"✓ LendSight started (PID: {process.pid})")
    print("Server should be available at: http://127.0.0.1:8082")
    print()
    print("Press Ctrl+C to stop...")
    
    # Wait for process
    process.wait()
except KeyboardInterrupt:
    print("\nStopping LendSight...")
    process.terminate()
    process.wait()
    print("Stopped.")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

