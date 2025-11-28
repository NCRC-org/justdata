#!/usr/bin/env python3
"""Execute API test directly - imports and runs the test function."""

import os
import sys
from pathlib import Path

# Change to script directory for .env loading
script_dir = Path(__file__).parent
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

# Import the test function
from test_claude_api_connection import test_claude_api

# Run it
if __name__ == "__main__":
    success = test_claude_api()
    sys.exit(0 if success else 1)

