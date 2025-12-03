#!/usr/bin/env python3
"""
Main entry point for JustData unified application.
This is the central Flask app that serves all sub-applications as blueprints.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from justdata.main.app import create_app

# Create app instance at module level for gunicorn
app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting JustData - Unified Data Analysis Platform")
    print("=" * 60)
    print(f"📱 Open your browser and go to: http://127.0.0.1:8000")
    print(f"🏠 Landing page: http://127.0.0.1:8000/")
    print(f"📊 BranchSeeker: http://127.0.0.1:8000/branchseeker/")
    print(f"💼 BizSight: http://127.0.0.1:8000/bizsight/")
    print(f"🏦 LendSight: http://127.0.0.1:8000/lendsight/")
    print(f"🔀 MergerMeter: http://127.0.0.1:8000/mergermeter/")
    print(f"🗺️  BranchMapper: http://127.0.0.1:8000/branchmapper/")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    port = int(os.environ.get('PORT', 8000))
    app.run(debug=True, host='0.0.0.0', port=port)

