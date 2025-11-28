#!/usr/bin/env python3
"""Execute LendSight by calling cmd.exe directly with subprocess shell=False."""
import subprocess
import sys
from pathlib import Path

# Get absolute paths
project_root = Path(__file__).parent.absolute()
script_path = project_root / "run_lendsight.py"
python_exe = sys.executable

# Build the command that cmd.exe will execute
# This is what the batch file does: start "Title" cmd /k "python script.py"
cmd_exe_command = f'start "LendSight (Port 8082)" cmd /k "cd /d "{project_root}" && {python_exe} run_lendsight.py"'

print("Executing LendSight via cmd.exe...")
print(f"Command: {cmd_exe_command}")
print()

try:
    # Call cmd.exe directly with /c to execute the command
    # shell=False means we're calling cmd.exe directly, not through PowerShell
    result = subprocess.Popen(
        ["cmd.exe", "/c", cmd_exe_command],
        shell=False,
        cwd=str(project_root)
    )
    print("✓ Command sent to cmd.exe")
    print("LendSight should be starting in a new window.")
    print("Check: http://127.0.0.1:8082")
    print()
    print("If a new window opened, LendSight is running there.")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

