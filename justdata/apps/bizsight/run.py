#!/usr/bin/env python3
"""
Entry point for BizSight Flask application.
Compatible with Render, Railway, Heroku, and local development.
"""

import os
import sys
from pathlib import Path

# Use __file__ for reliable path resolution
REPO_ROOT = Path(__file__).resolve().parents[3]  # .../JustData
APP_DIR = Path(__file__).resolve().parent

# Add repo root to Python path for justdata modules
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(APP_DIR))

# Verify justdata module exists
justdata_path = REPO_ROOT / 'justdata'
if not justdata_path.exists():
    print(f"ERROR: justdata module not found at {justdata_path}")
    sys.exit(1)

print(f"Repository root: {REPO_ROOT}")
print(f"App directory: {APP_DIR}")
print(f"JustData module found at: {justdata_path}")

# Import app using absolute import
try:
    from justdata.apps.bizsight.app import app
    print("Successfully imported BizSight app")
except ImportError as e:
    print(f"ERROR importing app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Expose app for gunicorn
application = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    print(f"Starting BizSight on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
