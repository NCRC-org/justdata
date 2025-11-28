#!/usr/bin/env python3
"""Run the API test using the DREAM launcher utility to bypass PowerShell wrapper."""

import subprocess
import sys
from pathlib import Path

# Get paths
dream_root = Path(r"C:\DREAM")
launcher = dream_root / "utils" / "run_python_script.py"
test_script = Path(__file__).parent / "test_claude_api_connection.py"

print("Using DREAM launcher utility to bypass PowerShell wrapper...")
print(f"Launcher: {launcher}")
print(f"Test script: {test_script}")
print()

# Use subprocess with shell=False to bypass PowerShell
python_exe = sys.executable
cmd = [python_exe, str(launcher), str(test_script)]

try:
    result = subprocess.run(
        cmd,
        shell=False,
        check=False,
        cwd=str(dream_root)
    )
    sys.exit(result.returncode)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

