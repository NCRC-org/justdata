#!/usr/bin/env python3
"""Direct runner for LendSight packaging script to avoid PowerShell path issues."""

import subprocess
import sys
from pathlib import Path

# Get the script path
script_path = Path(__file__).parent / 'apps' / 'lendsight' / 'package_lendsight.py'

# Run the script directly with Python
subprocess.run([sys.executable, str(script_path)], check=True)












