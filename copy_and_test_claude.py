#!/usr/bin/env python3
"""
Copy .env file and test Claude API connection.
"""

import os
import shutil
from pathlib import Path

# Copy .env file from C:\DREAM\justdata\ to current directory
source_env = Path(r"C:\DREAM\justdata\.env")
dest_env = Path(".env")

print("=" * 60)
print("Copying .env file and testing Claude API")
print("=" * 60)
print()

# Copy the file (only if destination doesn't exist or is different)
if source_env.exists():
    if dest_env.exists():
        # Check if files are different
        try:
            source_size = source_env.stat().st_size
            dest_size = dest_env.stat().st_size
            if source_size != dest_size:
                print(f"[INFO] .env file exists but sizes differ. Attempting to update...")
                try:
                    shutil.copy2(source_env, dest_env)
                    print(f"[OK] Updated .env file from {source_env}")
                except Exception as e:
                    print(f"[WARNING] Could not update .env file (may be in use): {e}")
                    print(f"[INFO] Using existing .env file")
            else:
                print(f"[OK] .env file already exists and matches source")
        except Exception as e:
            print(f"[INFO] Using existing .env file: {dest_env.absolute()}")
    else:
        try:
            shutil.copy2(source_env, dest_env)
            print(f"[OK] Copied .env file from {source_env}")
            print(f"     To: {dest_env.absolute()}")
        except Exception as e:
            print(f"[ERROR] Failed to copy .env file: {e}")
            print()
    print()
else:
    print(f"[WARNING] Source .env file not found: {source_env}")
    print(f"[INFO] Will try to use existing .env file if it exists")
    print()

# Now test the API
print("Testing Claude API connection...")
print()

# Load environment variables
try:
    from dotenv import load_dotenv
    # Load from current directory
    env_loaded = load_dotenv(dotenv_path=dest_env if dest_env.exists() else None)
    if env_loaded:
        print("[OK] Loaded environment variables from .env file")
    else:
        print("[WARNING] .env file not found or empty, checking system environment...")
except ImportError:
    print("[ERROR] python-dotenv not installed!")
    print("Please install it with: pip install python-dotenv")
    print()
    exit(1)

# Check for API key
claude_api_key = os.getenv("CLAUDE_API_KEY")

if not claude_api_key:
    print("[ERROR] CLAUDE_API_KEY environment variable not found!")
    print()
    print("Please check:")
    print("  1. The .env file was copied successfully")
    print("  2. The .env file contains CLAUDE_API_KEY")
    print()
    exit(1)

print("[OK] API Key found")
print(f"     Key length: {len(claude_api_key)} characters")
print(f"     Key prefix: {claude_api_key[:15]}...")
print()

# Test API connection
try:
    import anthropic
    
    print("Connecting to Claude API...")
    print("(Note: There may be a Cloudflare outage affecting connectivity)")
    print()
    
    # Initialize client
    client = anthropic.Anthropic(api_key=claude_api_key)
    
    # Make a simple test call with timeout
    print("Sending test message to Claude API...")
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            timeout=30.0,  # 30 second timeout
            messages=[{
                "role": "user",
                "content": "Say 'Hello, Claude API is working!' if you can read this."
            }]
        )
        
        # Get response text
        response_text = response.content[0].text
        
        print()
        print("=" * 60)
        print("[SUCCESS] Claude API is responding!")
        print("=" * 60)
        print()
        print("Response from Claude:")
        print(f"  {response_text}")
        print()
        print("API Configuration:")
        print(f"  Model: claude-sonnet-4-20250514")
        print(f"  Status: Connected and working")
        print()
        print("Note: API is working despite potential Cloudflare issues!")
        print()
        
    except Exception as api_error:
        error_str = str(api_error).lower()
        print()
        print("=" * 60)
        print("[ERROR] Claude API connection failed!")
        print("=" * 60)
        print()
        print(f"Error details: {api_error}")
        print()
        
        # Check for specific error types
        if "timeout" in error_str or "timed out" in error_str:
            print("This looks like a timeout error.")
            print("Possible causes:")
            print("  - Cloudflare outage (as mentioned)")
            print("  - Network connectivity issues")
            print("  - API service temporarily unavailable")
        elif "401" in error_str or "unauthorized" in error_str:
            print("This looks like an authentication error.")
            print("Please check that your CLAUDE_API_KEY is correct.")
        elif "429" in error_str or "rate limit" in error_str:
            print("This looks like a rate limit error.")
            print("You may have exceeded your API quota.")
        elif "connection" in error_str or "network" in error_str:
            print("This looks like a network connection error.")
            print("Possible causes:")
            print("  - Cloudflare outage (as mentioned)")
            print("  - Internet connectivity issues")
        else:
            print("Please check the error message above for more details.")
        
        print()
        exit(1)
    
except ImportError:
    print("[ERROR] anthropic package not installed!")
    print()
    print("Please install it with:")
    print("  pip install anthropic")
    print()
    exit(1)

print("=" * 60)
print("Test completed successfully!")
print("=" * 60)

