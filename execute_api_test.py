#!/usr/bin/env python3
"""Execute API test by importing it directly - bypasses all wrappers."""

import os
import sys
from pathlib import Path

# Change to script directory
script_dir = Path(__file__).parent
os.chdir(script_dir)

# Add to path
sys.path.insert(0, str(script_dir))

# Import and run the test function directly
from test_claude_api_connection import test_claude_api

if __name__ == "__main__":
    success = test_claude_api()
    sys.exit(0 if success else 1)

