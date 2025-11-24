#!/usr/bin/env python3
"""
Interactive setup script for MergerMeter configuration.
Prompts user for required configuration values and creates .env file.
"""

import os
import sys
from pathlib import Path
from getpass import getpass

def print_header():
    """Print setup header"""
    print("\n" + "="*70)
    print("MergerMeter Configuration Setup")
    print("="*70)
    print("\nThis script will help you configure MergerMeter.")
    print("You'll need the following information:")
    print("  - Google Cloud Project ID")
    print("  - Path to GCP service account credentials JSON file")
    print("  - (Optional) Claude API key for AI features")
    print()

def get_input(prompt, default=None, required=True, password=False):
    """Get user input with optional default value"""
    if default:
        prompt_text = f"{prompt} [{default}]: "
    else:
        prompt_text = f"{prompt}: "
    
    if password:
        value = getpass(prompt_text)
    else:
        value = input(prompt_text).strip()
    
    if not value and default:
        value = default
    
    if not value and required:
        print(f"  ⚠️  This field is required. Please provide a value.")
        return get_input(prompt, default, required, password)
    
    return value

def validate_credentials_file(path_str):
    """Validate that credentials file exists"""
    if not path_str:
        return False
    
    cred_path = Path(path_str)
    if not cred_path.exists():
        print(f"  ⚠️  File not found: {path_str}")
        return False
    
    if not cred_path.suffix == '.json':
        print(f"  ⚠️  Credentials file should be a JSON file")
        return False
    
    return True

def validate_project_id(project_id):
    """Basic validation of GCP project ID"""
    if not project_id:
        return False
    
    # GCP project IDs are alphanumeric with hyphens, 6-30 chars
    if len(project_id) < 6 or len(project_id) > 30:
        print(f"  ⚠️  Project ID should be 6-30 characters")
        return False
    
    return True

def generate_secret_key():
    """Generate a random secret key"""
    import secrets
    return secrets.token_hex(32)

def main():
    """Main setup function"""
    print_header()
    
    # Get project root (where run_mergermeter.py is)
    if len(sys.argv) > 1:
        project_root = Path(sys.argv[1])
    else:
        # Try to find project root
        current_dir = Path.cwd()
        if (current_dir / 'run_mergermeter.py').exists():
            project_root = current_dir
        elif (current_dir.parent / 'run_mergermeter.py').exists():
            project_root = current_dir.parent
        else:
            project_root = current_dir
    
    env_file = project_root / '.env'
    
    # Check if .env already exists
    if env_file.exists():
        print(f"⚠️  .env file already exists at: {env_file}")
        overwrite = input("Do you want to overwrite it? (yes/no) [no]: ").strip().lower()
        if overwrite not in ['yes', 'y']:
            print("Setup cancelled. Existing .env file preserved.")
            return
        print()
    
    print("Please provide the following configuration:\n")
    
    # Required: GCP Project ID
    print("1. Google Cloud Project ID (Required)")
    print("   This is your GCP project ID where BigQuery data is stored.")
    print("   Example: hdma1-242116")
    gcp_project_id = get_input("   GCP Project ID", required=True)
    
    while not validate_project_id(gcp_project_id):
        gcp_project_id = get_input("   GCP Project ID", required=True)
    
    # Required: GCP Credentials
    print("\n2. Google Cloud Credentials File (Required)")
    print("   Path to your GCP service account credentials JSON file.")
    print("   Download from: https://console.cloud.google.com/iam-admin/serviceaccounts")
    print("   Example: /path/to/your-project-credentials.json")
    
    creds_path = get_input("   Credentials file path", required=True)
    
    # Convert to absolute path if relative
    creds_path_obj = Path(creds_path)
    if not creds_path_obj.is_absolute():
        # Try relative to project root
        creds_path_obj = project_root / creds_path
        if creds_path_obj.exists():
            creds_path = str(creds_path_obj.resolve())
        else:
            # Try relative to current directory
            creds_path_obj = Path.cwd() / creds_path
            if creds_path_obj.exists():
                creds_path = str(creds_path_obj.resolve())
    
    while not validate_credentials_file(creds_path):
        creds_path = get_input("   Credentials file path", required=True)
        # Try to resolve relative paths
        creds_path_obj = Path(creds_path)
        if not creds_path_obj.is_absolute():
            creds_path_obj = project_root / creds_path
            if creds_path_obj.exists():
                creds_path = str(creds_path_obj.resolve())
    
    # Optional: Port
    print("\n3. Server Port (Optional)")
    print("   Port number for the Flask web server.")
    port = get_input("   Port", default="8083", required=False)
    
    # Optional: Secret Key
    print("\n4. Secret Key (Optional)")
    print("   Secret key for Flask sessions. Leave blank to auto-generate.")
    secret_key = get_input("   Secret Key", required=False, password=True)
    if not secret_key:
        secret_key = generate_secret_key()
        print(f"   ✓ Generated secret key: {secret_key[:20]}...")
    
    # Optional: AI Features
    print("\n5. AI Features (Optional)")
    print("   Claude API key for AI-powered analysis summaries.")
    print("   Leave blank if you don't want to use AI features.")
    use_ai = input("   Do you want to configure AI features? (yes/no) [no]: ").strip().lower()
    
    ai_provider = None
    claude_api_key = None
    
    if use_ai in ['yes', 'y']:
        ai_provider = get_input("   AI Provider", default="claude", required=False)
        claude_api_key = get_input("   Claude API Key", required=False, password=True)
    
    # Write .env file
    print("\n" + "="*70)
    print("Creating .env file...")
    
    env_content = f"""# MergerMeter Environment Configuration
# Generated by setup_config.py
# DO NOT commit this file to version control

# =============================================================================
# REQUIRED - BigQuery Configuration
# =============================================================================
GCP_PROJECT_ID={gcp_project_id}
GOOGLE_APPLICATION_CREDENTIALS={creds_path}

# =============================================================================
# OPTIONAL - Server Configuration
# =============================================================================
PORT={port}
SECRET_KEY={secret_key}

# =============================================================================
# OPTIONAL - AI Features (if using AI-powered insights)
# =============================================================================
"""
    
    if ai_provider and claude_api_key:
        env_content += f"""AI_PROVIDER={ai_provider}
CLAUDE_API_KEY={claude_api_key}
"""
    else:
        env_content += """# AI_PROVIDER=claude
# CLAUDE_API_KEY=your-claude-api-key-here
"""
    
    env_content += """
# =============================================================================
# OPTIONAL - Advanced Configuration
# =============================================================================
DEBUG=False
LOG_LEVEL=INFO
MAX_CONTENT_LENGTH=10485760
"""
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        print(f"✓ .env file created successfully at: {env_file}")
        print("\n" + "="*70)
        print("Setup Complete!")
        print("="*70)
        print("\nNext steps:")
        print("1. Verify your .env file contains the correct values")
        print("2. Run: python run_mergermeter.py")
        print("3. Open your browser to: http://127.0.0.1:8083")
        print("\nFor more information, see: apps/mergermeter/README.md")
        print()
        
    except Exception as e:
        print(f"\n❌ Error creating .env file: {e}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(0)

