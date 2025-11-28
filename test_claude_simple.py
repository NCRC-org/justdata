#!/usr/bin/env python3
"""
Simple Claude API test - reads from existing .env file.
"""

import os
from pathlib import Path

print("=" * 60)
print("Testing Claude API Connection")
print("=" * 60)
print()

# Check if .env file exists
env_file = Path(".env")
if not env_file.exists():
    print("[ERROR] .env file not found in current directory!")
    print(f"       Looking for: {env_file.absolute()}")
    print()
    print("Please ensure .env file exists or copy it from C:\\DREAM\\justdata\\.env")
    exit(1)

print(f"[OK] Found .env file: {env_file.absolute()}")
print()

# Load environment variables
try:
    from dotenv import load_dotenv
    result = load_dotenv(dotenv_path=env_file)
    if result:
        print("[OK] Loaded environment variables from .env file")
    else:
        print("[WARNING] .env file loaded but may be empty")
except ImportError:
    print("[ERROR] python-dotenv not installed!")
    print("Please install it with: pip install python-dotenv")
    exit(1)
except Exception as e:
    print(f"[ERROR] Failed to load .env file: {e}")
    exit(1)

print()

# Check for API key
claude_api_key = os.getenv("CLAUDE_API_KEY")

if not claude_api_key:
    print("[ERROR] CLAUDE_API_KEY not found in environment!")
    print()
    print("Checking .env file contents...")
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'CLAUDE_API_KEY' in content:
                print("[INFO] CLAUDE_API_KEY found in .env file but not loaded")
                print("       This may be a formatting issue in the .env file")
            else:
                print("[ERROR] CLAUDE_API_KEY not found in .env file")
    except Exception as e:
        print(f"[ERROR] Could not read .env file: {e}")
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
            print("⚠️  TIMEOUT ERROR - This could be due to:")
            print("  - Cloudflare outage (as mentioned)")
            print("  - Network connectivity issues")
            print("  - API service temporarily unavailable")
        elif "401" in error_str or "unauthorized" in error_str:
            print("⚠️  AUTHENTICATION ERROR:")
            print("  - Please check that your CLAUDE_API_KEY is correct")
            print("  - The API key may have expired or been revoked")
        elif "429" in error_str or "rate limit" in error_str:
            print("⚠️  RATE LIMIT ERROR:")
            print("  - You may have exceeded your API quota")
            print("  - Please wait before trying again")
        elif "connection" in error_str or "network" in error_str or "resolve" in error_str:
            print("⚠️  NETWORK ERROR - This could be due to:")
            print("  - Cloudflare outage (as mentioned)")
            print("  - Internet connectivity issues")
            print("  - DNS resolution problems")
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

