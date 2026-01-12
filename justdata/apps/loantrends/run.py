#!/usr/bin/env python3
"""
Entry point for LoanTrends Flask application.
Compatible with Render, Railway, Heroku, and local development.
"""

import os
import sys
from pathlib import Path

# Use __file__ for reliable path resolution
REPO_ROOT = Path(__file__).resolve().parents[2]  # .../JustData
APP_DIR = Path(__file__).resolve().parent

# Add repo root to Python path for shared modules
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(APP_DIR))

# Verify shared module exists
shared_path = REPO_ROOT / 'shared'
if not shared_path.exists():
    print(f"ERROR: Shared module not found at {shared_path}")
    sys.exit(1)

print(f"Repository root: {REPO_ROOT}")
print(f"App directory: {APP_DIR}")
print(f"Shared module found at: {shared_path}")

# Import app using absolute import (don't change directory - breaks package structure)
try:
    from apps.loantrends.app import app
    print("Successfully imported LoanTrends app")
except ImportError as e:
    print(f"ERROR importing app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Expose app for gunicorn
application = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8083))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"Starting LoanTrends on {host}:{port}")
    app.run(host=host, port=port, debug=debug)




