#!/usr/bin/env python3
"""
Entry point for BranchMapper Flask application.
Compatible with Render, Railway, Heroku, and local development.
"""

import os
import sys
from pathlib import Path

# Use __file__ for reliable path resolution
REPO_ROOT = Path(__file__).resolve().parents[3]  # .../ncrc-test-apps
APP_DIR = Path(__file__).resolve().parent

# Add repo root to Python path for shared modules
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(APP_DIR))

# Load .env from repo root for local development (same as run_justdata.py)
try:
    from dotenv import load_dotenv
    env_path = REPO_ROOT / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env from: {env_path}")
    else:
        print(f"No .env file found at {env_path}")
except ImportError:
    pass

# Verify shared module exists
justdata_path = REPO_ROOT / 'justdata'
if not justdata_path.exists():
    print(f"ERROR: justdata module not found at {justdata_path}")
    sys.exit(1)

print(f"Repository root: {REPO_ROOT}")
print(f"App directory: {APP_DIR}")
print(f"JustData module found at: {justdata_path}")

# Import app using absolute import (don't change directory - breaks package structure)
try:
    from justdata.apps.branchmapper.app import app
    print("Successfully imported BranchMapper app")
except ImportError as e:
    print(f"ERROR importing app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Expose app for gunicorn
application = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8084))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"Starting BranchMapper on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
