#!/usr/bin/env python3
"""Execute API test directly - no subprocess, imports and runs inline."""

import os
import sys
from pathlib import Path

# Set working directory
os.chdir(r'C:\DREAM\justdata')

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Execute test inline
print("=" * 60)
print("Testing Claude API Connection")
print("=" * 60)
print()

api_key = os.getenv("CLAUDE_API_KEY")
if not api_key:
    print("❌ ERROR: CLAUDE_API_KEY not found")
    print("\nPlease check your .env file in C:\\DREAM\\justdata")
    sys.exit(1)

print(f"✓ API Key found: {api_key[:20]}...{api_key[-10:]}")
print()

try:
    import anthropic
    print("Testing API connection...")
    client = anthropic.Anthropic(api_key=api_key)
    print("Sending test request to Claude API...")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[{"role": "user", "content": "Say 'Hello, API test successful!' and nothing else."}]
    )
    result = response.content[0].text
    print()
    print("=" * 60)
    print("✅ API TEST SUCCESSFUL!")
    print("=" * 60)
    print()
    print(f"Response: {result}")
    print()
    print("The Claude API is working correctly.")
    
except anthropic.APIError as e:
    print()
    print("=" * 60)
    print("❌ API ERROR")
    print("=" * 60)
    print()
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {str(e)}")
    print()
    error_str = str(e).lower()
    if "401" in str(e) or "authentication" in error_str:
        print("This appears to be an authentication error.")
        print("Please check that your API key is valid.")
    elif "429" in str(e) or "rate limit" in error_str:
        print("This appears to be a rate limit error.")
    elif "cloudflare" in error_str or "cf-" in error_str:
        print("⚠️  CLOUDFLARE BLOCKING DETECTED")
        print("\nPossible solutions:")
        print("1. Check if you're behind a corporate firewall/proxy")
        print("2. Try using a VPN or different network")
        print("3. Contact your network administrator")
    sys.exit(1)
    
except Exception as e:
    print()
    print("=" * 60)
    print("❌ CONNECTION ERROR")
    print("=" * 60)
    print()
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {str(e)}")
    print()
    error_str = str(e).lower()
    if "cloudflare" in error_str or "cf-" in error_str:
        print("⚠️  CLOUDFLARE BLOCKING DETECTED")
        print("\nPossible solutions:")
        print("1. Check if you're behind a corporate firewall/proxy")
        print("2. Try using a VPN or different network")
        print("3. Contact your network administrator")
    elif "timeout" in error_str:
        print("This appears to be a timeout error.")
    elif "connection" in error_str or "network" in error_str:
        print("This appears to be a network connectivity issue.")
    else:
        import traceback
        traceback.print_exc()
    sys.exit(1)

