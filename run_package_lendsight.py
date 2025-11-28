#!/usr/bin/env python3
"""Run LendSight packaging script directly to avoid PowerShell path issues."""

import subprocess
import sys
from pathlib import Path

# Get the absolute path to the packaging script
script_path = Path(__file__).parent.absolute() / 'apps' / 'lendsight' / 'package_lendsight.py'

# Run it directly with shell=False to avoid PowerShell issues
result = subprocess.run([sys.executable, str(script_path)], shell=False, check=False)
sys.exit(result.returncode)

