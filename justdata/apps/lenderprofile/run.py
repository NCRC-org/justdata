#!/usr/bin/env python3
"""
Run script for LenderProfile
Supports both development (Flask dev server) and production (gunicorn)
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

from apps.lenderprofile.app import app, application

# Export application for gunicorn (required for Docker/production)
# This allows: gunicorn apps.lenderprofile.run:application
__all__ = ['app', 'application']

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8086))
    debug = os.getenv('DEBUG', 'true').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)

