#!/usr/bin/env python3
"""
Entry point for ElectWatch Flask application.

Usage:
    python run.py
    gunicorn apps.electwatch.run:application
"""

import os
import sys
from pathlib import Path

# Set up paths
REPO_ROOT = Path(__file__).resolve().parents[2]  # .../ncrc-test-apps
APP_DIR = Path(__file__).resolve().parent

# Add repo root to Python path for shared module imports
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(APP_DIR))

# Load environment variables from .env BEFORE importing app/config
from dotenv import load_dotenv
env_file = REPO_ROOT / '.env'
if env_file.exists():
    load_dotenv(env_file)
    print(f"[ENV] Loaded .env from: {env_file}")
else:
    print(f"[ENV] Warning: No .env file found at {env_file}")

# Verify shared module exists
shared_path = REPO_ROOT / 'shared'
if not shared_path.exists():
    print(f"ERROR: Shared module not found at {shared_path}")
    print("Make sure you're running from the ncrc-test-apps repository")
    sys.exit(1)

# Import app
try:
    from apps.electwatch.app import app
    print("Successfully imported ElectWatch app")
except ImportError as e:
    print(f"ERROR importing app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Expose application for gunicorn
application = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8083))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'

    print(f"""
    ==============================================================
    |                     ElectWatch v0.9.0                      |
    |     Monitor Elected Officials' Financial Relationships     |
    |                  A Just Data Tool by NCRC                  |
    ==============================================================

    Starting server on {host}:{port}
    Debug mode: {debug}
    """)

    app.run(host=host, port=port, debug=debug)
