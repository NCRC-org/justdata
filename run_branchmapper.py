#!/usr/bin/env python3
"""
Entry point for BranchMapper web application.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from justdata.apps.branchmapper.app import app

if __name__ == '__main__':
    print("🚀 Starting BranchMapper - Interactive Bank Branch Location Map...")
    print("📱 Open your browser and go to: http://127.0.0.1:8084")
    print("⏹️  Press Ctrl+C to stop the server")
    print()
    
    port = int(os.environ.get('PORT', 8084))
    app.run(debug=True, host='0.0.0.0', port=port)

