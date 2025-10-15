#!/usr/bin/env python3
"""
Entry point for LendSight web application.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from justdata.apps.lendsight.app import app

if __name__ == '__main__':
    print("🚀 Starting LendSight (Lending Data Analyzer)...")
    print("📱 Open your browser and go to: http://127.0.0.1:8082")
    print("⏹️  Press Ctrl+C to stop the server")
    print()
    
    port = int(os.environ.get('PORT', 8082))
    app.run(debug=True, host='0.0.0.0', port=port)

