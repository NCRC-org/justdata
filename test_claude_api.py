#!/usr/bin/env python3
"""
Test script to check if Claude API is configured and responding.
"""

import os
import sys

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Check for API key
claude_api_key = os.getenv("CLAUDE_API_KEY")

print("=" * 60)
print("Claude API Connection Test")
print("=" * 60)
print()

# Check if API key exists
if not claude_api_key:
    print("[ERROR] CLAUDE_API_KEY environment variable not found!")
    print()
    print("Please set the CLAUDE_API_KEY environment variable:")
    print("  1. Create a .env file in the project root")
    print("  2. Add: CLAUDE_API_KEY=sk-ant-xxx")
    print("  3. Or set it in your system environment variables")
    print()
    sys.exit(1)

# Check API key format
if not claude_api_key.startswith("sk-ant-"):
    print("[WARNING] API key format may be incorrect.")
    print(f"   Expected format: sk-ant-xxx...")
    print(f"   Your key starts with: {claude_api_key[:10]}...")
    print()
else:
    print("[OK] API Key found and format looks correct")
    print(f"   Key prefix: {claude_api_key[:10]}...")
    print()

# Test API connection
print("Testing Claude API connection...")
print()

try:
    import anthropic
    
    # Initialize client
    client = anthropic.Anthropic(api_key=claude_api_key)
    
    # Make a simple test call
    print("Sending test message to Claude API...")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
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
    
except ImportError:
    print("[ERROR] anthropic package not installed!")
    print()
    print("Please install it with:")
    print("  pip install anthropic")
    print()
    sys.exit(1)
    
except Exception as e:
    print()
    print("=" * 60)
    print("[ERROR] Claude API connection failed!")
    print("=" * 60)
    print()
    print(f"Error details: {str(e)}")
    print()
    
    # Provide helpful error messages
    error_str = str(e).lower()
    
    if "401" in error_str or "unauthorized" in error_str:
        print("This looks like an authentication error.")
        print("Please check that your CLAUDE_API_KEY is correct.")
    elif "429" in error_str or "rate limit" in error_str:
        print("This looks like a rate limit error.")
        print("You may have exceeded your API quota. Please wait and try again.")
    elif "timeout" in error_str or "connection" in error_str:
        print("This looks like a network connection error.")
        print("Please check your internet connection.")
    else:
        print("Please check the error message above for more details.")
    
    print()
    sys.exit(1)

print("=" * 60)
print("Test completed successfully!")
print("=" * 60)

