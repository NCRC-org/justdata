#!/usr/bin/env python3
"""
Run DataExplorer dashboard application.
"""

import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from apps.dataexplorer.app import app
from apps.dataexplorer.config import DataExplorerConfig

if __name__ == '__main__':
    port = DataExplorerConfig.PORT
    print(f"Starting DataExplorer on http://127.0.0.1:{port}")
    print(f"Press Ctrl+C to stop")
    # Force reloader to pick up code changes
    app.run(host='127.0.0.1', port=port, debug=True, use_reloader=True, use_debugger=True, extra_files=None)

