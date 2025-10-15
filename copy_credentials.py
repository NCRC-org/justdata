#!/usr/bin/env python3
"""
Helper script to copy credentials from your existing .env file to the JustData .env file.
"""

import os
import shutil
from pathlib import Path

def copy_credentials():
    """Copy credentials from existing .env file to JustData .env file."""
    
    print("🔐 JustData Credentials Copy Tool")
    print("=" * 40)
    
    # Get the current directory
    current_dir = Path.cwd()
    justdata_env = current_dir / ".env"
    template_env = current_dir / "env.template"
    
    print(f"Current directory: {current_dir}")
    print(f"Looking for .env file: {justdata_env}")
    
    # Check if .env already exists
    if justdata_env.exists():
        print("⚠️  .env file already exists!")
        response = input("Do you want to overwrite it? (y/N): ").lower()
        if response != 'y':
            print("❌ Operation cancelled. Please backup your .env file first.")
            return
    
    # Check if template exists
    if not template_env.exists():
        print("❌ env.template file not found!")
        return
    
    # Ask for source .env file path
    print("\n📁 Please provide the path to your existing .env file")
    print("Example: /path/to/your/other/project/.env")
    
    source_env_path = input("Source .env file path: ").strip()
    
    if not source_env_path:
        print("❌ No source path provided!")
        return
    
    source_env = Path(source_env_path)
    
    if not source_env.exists():
        print(f"❌ Source file not found: {source_env}")
        return
    
    try:
        # Copy the template to .env
        shutil.copy2(template_env, justdata_env)
        print(f"✅ Created .env file from template")
        
        # Read the source .env file
        with open(source_env, 'r') as f:
            source_content = f.read()
        
        # Parse source environment variables
        source_vars = {}
        for line in source_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                source_vars[key.strip()] = value.strip()
        
        print(f"📋 Found {len(source_vars)} environment variables in source file")
        
        # Read the new .env file
        with open(justdata_env, 'r') as f:
            env_content = f.read()
        
        # Replace placeholder values with actual values
        updated_content = env_content
        
        # BigQuery credentials
        bq_fields = [
            'BQ_TYPE', 'BQ_PROJECT_ID', 'BQ_PRIVATE_KEY_ID', 'BQ_PRIVATE_KEY',
            'BQ_CLIENT_EMAIL', 'BQ_CLIENT_ID', 'BQ_AUTH_URI', 'BQ_TOKEN_URI',
            'BQ_AUTH_PROVIDER_X509_CERT_URL', 'BQ_CLIENT_X509_CERT_URL'
        ]
        
        for field in bq_fields:
            if field in source_vars:
                placeholder = f"your-{field.lower().replace('_', '-')}"
                updated_content = updated_content.replace(placeholder, source_vars[field])
                print(f"✅ Updated {field}")
            else:
                print(f"⚠️  {field} not found in source file")
        
        # AI API keys
        if 'OPENAI_API_KEY' in source_vars:
            updated_content = updated_content.replace("your-openai-api-key-here", source_vars['OPENAI_API_KEY'])
            print("✅ Updated OPENAI_API_KEY")
        
        if 'CLAUDE_API_KEY' in source_vars:
            updated_content = updated_content.replace("your-claude-api-key-here", source_vars['CLAUDE_API_KEY'])
            print("✅ Updated CLAUDE_API_KEY")
        
        # Write the updated .env file
        with open(justdata_env, 'w') as f:
            f.write(updated_content)
        
        print(f"\n✅ Credentials copied successfully!")
        print(f"📁 New .env file created at: {justdata_env}")
        print("\n🔍 Please review the .env file and update any remaining fields manually.")
        print("💡 You can now run: make test-db")
        
    except Exception as e:
        print(f"❌ Error copying credentials: {e}")
        if justdata_env.exists():
            justdata_env.unlink()
            print("🧹 Cleaned up partial .env file")

if __name__ == "__main__":
    copy_credentials()

