#!/usr/bin/env python3
"""
Entry point for MergerMeter web application.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

def check_required_config():
    """Check for required configuration and prompt if missing"""
    missing = []
    
    # Check for GCP Project ID
    gcp_project_id = os.getenv('GCP_PROJECT_ID')
    if not gcp_project_id:
        missing.append('GCP_PROJECT_ID')
    
    # Check for GCP Credentials
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        missing.append('GOOGLE_APPLICATION_CREDENTIALS')
    elif creds_path and not Path(creds_path).exists():
        print(f"⚠️  Warning: Credentials file not found: {creds_path}")
        print("   Please verify the path in your .env file.\n")
    
    if missing:
        print("="*70)
        print("⚠️  Missing Required Configuration")
        print("="*70)
        print("\nThe following required environment variables are not set:")
        for item in missing:
            print(f"  - {item}")
        print("\nTo configure MergerMeter, run:")
        print("  python apps/mergermeter/setup_config.py")
        print("\nOr create a .env file in the root directory with:")
        print("  GCP_PROJECT_ID=your-gcp-project-id")
        print("  GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json")
        print("\nSee apps/mergermeter/.env.example for a template.")
        print("="*70)
        print()
        return False
    
    return True

from apps.mergermeter.app import app

if __name__ == '__main__':
    # Check configuration before starting
    if not check_required_config():
        print("Cannot start MergerMeter without required configuration.")
        print("Please run: python apps/mergermeter/setup_config.py")
        sys.exit(1)
    
    print("Starting MergerMeter - Two-bank merger impact analyzer...")
    print("Open your browser and go to: http://127.0.0.1:8083")
    print("Press Ctrl+C to stop the server")
    print()
    
    port = int(os.environ.get('PORT', 8083))
    app.run(debug=True, host='0.0.0.0', port=port)

