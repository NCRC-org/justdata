#!/usr/bin/env python3
"""Launch BranchMapper in a new terminal window."""
import subprocess
import sys
from pathlib import Path

# Use C:\DREAM\#JustData_Repo to avoid apostrophe in "Nat'l Community Reinvestment Coaltn"
project_root = Path(r"C:\DREAM\#JustData_Repo")
script_path = project_root / "start_branchmapper_final.py"
python_exe = sys.executable

if not script_path.exists():
    print(f"ERROR: Script not found at {script_path}")
    sys.exit(1)

# Build command to run in new window
# Use cmd /k to keep window open
cmd = f'cmd /k "cd /d {project_root} && {python_exe} start_branchmapper_final.py"'

print(f"Launching BranchMapper in new window...")
print(f"Window title: BranchMapper Server (Port 8084)")

try:
    # Use CREATE_NEW_CONSOLE to open a new window
    if sys.platform == 'win32':
        subprocess.Popen(
            cmd,
            shell=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        print("✓ BranchMapper window opened")
        print("Server will be available at: http://127.0.0.1:8084")
    else:
        # For non-Windows, just run normally
        subprocess.Popen([str(python_exe), str(script_path)], cwd=str(project_root))
except Exception as e:
    print(f"ERROR: Could not launch BranchMapper: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

