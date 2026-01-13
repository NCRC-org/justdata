#!/usr/bin/env python3
"""
Startup script for MergerMeter Flask application.
Compatible with Render, Railway, Heroku, and local development.
Uses simplified path resolution based on __file__ for reliability.
"""

import os
import sys
from pathlib import Path

# Use __file__ for reliable path resolution
# This works regardless of current working directory
REPO_ROOT = Path(__file__).resolve().parents[3]  # .../ncrc-test-apps
APP_DIR = Path(__file__).resolve().parent

# Add repo root to Python path for shared modules
sys.path.insert(0, str(REPO_ROOT))

# Add app directory to Python path
sys.path.insert(0, str(APP_DIR))

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
    from justdata.apps.mergermeter.app import app
    print("Successfully imported MergerMeter app")
except ImportError as e:
    print(f"ERROR importing app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Expose app for gunicorn
application = app

if __name__ == '__main__':
    # Get port from environment variable (Render/Railway/Heroku set this)
    port = int(os.environ.get('PORT', 8083))
    
    # Host: 0.0.0.0 allows external connections (required for cloud services)
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Debug mode: only enable in development
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"Starting MergerMeter on {host}:{port}")
    print(f"Debug mode: {debug}")
    
    try:
        app.run(
            host=host,
            port=port,
            debug=debug
        )
    except Exception as e:
        print(f"ERROR starting app: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
