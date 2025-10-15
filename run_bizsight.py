#!/usr/bin/env python3
"""
Entry point for BizSight web application.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from justdata.apps.bizsight.app import app

if __name__ == '__main__':
    print("🚀 Starting BizSight (Business Data Analyzer)...")
    print("📱 Open your browser and go to: http://127.0.0.1:8081")
    print("⏹️  Press Ctrl+C to stop the server")
    print()
    
    port = int(os.environ.get('PORT', 8081))
    app.run(debug=True, host='0.0.0.0', port=port)

