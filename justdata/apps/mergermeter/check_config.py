#!/usr/bin/env python3
"""
Check MergerMeter configuration and prompt for missing values.
This script validates that all required configuration is present.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def check_config():
    """Check configuration and prompt for missing values"""
    
    # Load .env file
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / '.env'
    
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✓ Loaded .env file from: {env_file}")
    else:
        print(f"⚠️  .env file not found at: {env_file}")
        print("   Run 'python apps/mergermeter/setup_config.py' to create one.")
        return False
    
    # Check required configuration
    missing = []
    warnings = []
    
    # Required: GCP Project ID
    gcp_project_id = os.getenv('GCP_PROJECT_ID')
    if not gcp_project_id:
        missing.append('GCP_PROJECT_ID')
    else:
        print(f"✓ GCP_PROJECT_ID: {gcp_project_id}")
    
    # Required: GCP Credentials
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        missing.append('GOOGLE_APPLICATION_CREDENTIALS')
    else:
        creds_file = Path(creds_path)
        if creds_file.exists():
            print(f"✓ GOOGLE_APPLICATION_CREDENTIALS: {creds_path}")
        else:
            warnings.append(f"GOOGLE_APPLICATION_CREDENTIALS file not found: {creds_path}")
    
    # Optional: Port
    port = os.getenv('PORT', '8083')
    print(f"✓ PORT: {port}")
    
    # Optional: Secret Key
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key or secret_key == 'change-this-to-a-random-secret-key-for-production':
        warnings.append("SECRET_KEY not set or using default value (should be changed for production)")
    else:
        print(f"✓ SECRET_KEY: {'*' * 20}...")
    
    # Optional: AI Features
    ai_provider = os.getenv('AI_PROVIDER')
    claude_api_key = os.getenv('CLAUDE_API_KEY')
    if ai_provider and not claude_api_key:
        warnings.append("AI_PROVIDER is set but CLAUDE_API_KEY is missing")
    elif claude_api_key:
        print(f"✓ AI features configured (provider: {ai_provider or 'claude'})")
    
    # Report results
    print()
    if missing:
        print("❌ Missing required configuration:")
        for item in missing:
            print(f"   - {item}")
        print("\nRun 'python apps/mergermeter/setup_config.py' to configure.")
        return False
    
    if warnings:
        print("⚠️  Warnings:")
        for warning in warnings:
            print(f"   - {warning}")
        print()
    
    print("✓ Configuration check passed!")
    return True

if __name__ == '__main__':
    success = check_config()
    sys.exit(0 if success else 1)

