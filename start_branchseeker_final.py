#!/usr/bin/env python3
"""Start BranchSeeker using C:\DREAM shortcut path with subprocess shell=False."""
import subprocess
import sys
from pathlib import Path

# Use C:\DREAM\#JustData_Repo to avoid apostrophe in "Nat'l Community Reinvestment Coaltn"
project_root = Path(r"C:\DREAM\#JustData_Repo")
script_path = project_root / "run_branchseeker.py"
python_exe = sys.executable

print(f"Project root: {project_root}")
print(f"Script: {script_path}")
print(f"Python: {python_exe}")
print()

if not script_path.exists():
    print(f"ERROR: Script not found at {script_path}")
    print("Please verify C:\\DREAM\\#JustData_Repo exists")
    sys.exit(1)

# Build command as list - this bypasses PowerShell
cmd = [str(python_exe), str(script_path)]

print(f"Executing: {' '.join(cmd)}")
print("Starting BranchSeeker on port 8080...")
print()

try:
    # Use subprocess with shell=False to bypass PowerShell entirely
    process = subprocess.Popen(
        cmd,
        shell=False,  # Critical: bypasses PowerShell wrapper
        cwd=str(project_root),
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    print(f"✓ BranchSeeker process started (PID: {process.pid})")
    print("Server should be available at: http://127.0.0.1:8080")
    print()
    print("Process is running. Press Ctrl+C to stop.")
    
    # Wait for the process
    process.wait()
except KeyboardInterrupt:
    print("\nStopping BranchSeeker...")
    process.terminate()
    process.wait()
    print("Stopped.")
except Exception as e:
    print(f"ERROR: Could not start BranchSeeker: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

