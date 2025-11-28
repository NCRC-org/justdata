#!/usr/bin/env python3
"""Direct API test runner that bypasses all wrappers."""

import subprocess
import sys
from pathlib import Path

# Direct execution - no shell, no wrapper
script_path = Path(__file__).parent / "test_claude_api_connection.py"
python_exe = sys.executable

print("Running API test directly...")
print(f"Script: {script_path}")
print()

# Change to script directory for proper .env loading
import os
os.chdir(script_path.parent)

# Run directly with subprocess, no shell
result = subprocess.run(
    [python_exe, str(script_path)],
    shell=False,
    cwd=str(script_path.parent)
)

sys.exit(result.returncode)

