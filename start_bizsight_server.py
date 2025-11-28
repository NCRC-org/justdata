#!/usr/bin/env python3
"""Start BizSight server with proper path setup."""

import os
import sys
from pathlib import Path

# Get the directory where this script is located
script_dir = Path(__file__).parent.absolute()
repo_root = script_dir

# Add repo root to Python path
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Set environment variables
os.environ['DEBUG'] = 'True'
os.environ['FLASK_DEBUG'] = '1'

# Change to repo root directory
os.chdir(repo_root)

print("=" * 80)
print("STARTING BIZSIGHT SERVER")
print("=" * 80)
print(f"Working directory: {os.getcwd()}")
print(f"Python path includes: {repo_root}")
print("=" * 80)
print()

# Import and run the Flask app
if __name__ == "__main__":
    try:
        from apps.bizsight.app import app
        print("Flask app imported successfully")
        print("Starting server on http://localhost:8081")
        print("Press Ctrl+C to stop the server")
        print("=" * 80)
        print()
        app.run(host='0.0.0.0', port=8081, debug=True)
    except Exception as e:
        print(f"ERROR: Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

