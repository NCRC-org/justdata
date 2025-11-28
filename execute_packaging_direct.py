#!/usr/bin/env python3
"""Execute packaging directly using subprocess"""
import subprocess
import sys
from pathlib import Path

# Get the script path
script_path = Path(__file__).parent / 'apps' / 'bizsight' / 'create_deployment_package.py'

# Run it using subprocess with shell=False to avoid PowerShell
result = subprocess.run(
    [sys.executable, str(script_path)],
    cwd=str(script_path.parent),
    capture_output=False,
    text=True
)

sys.exit(result.returncode)


