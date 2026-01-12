#!/usr/bin/env python3
"""Start the Flask server"""
import os
import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(repo_root))

# Set environment variables
os.environ['PYTHONPATH'] = str(repo_root)
os.environ['PORT'] = os.getenv('PORT', '8085')

from apps.dataexplorer.app import app

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8085))
    debug = os.getenv('DEBUG', 'true').lower() == 'true'
    print(f"Starting Flask server on port {port} (debug={debug})...")
    app.run(host='0.0.0.0', port=port, debug=debug)

