#!/usr/bin/env python3
"""Run API test inline - no subprocess, no wrapper issues."""

import os
import sys
from pathlib import Path

# Change to script directory for .env loading
script_dir = Path(__file__).parent
os.chdir(script_dir)

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Now run the test inline
print("=" * 60)
print("Testing Claude API Connection")
print("=" * 60)
print()

api_key = os.getenv("CLAUDE_API_KEY")
if not api_key:
    print("❌ ERROR: CLAUDE_API_KEY not found")
    sys.exit(1)

print(f"✓ API Key found: {api_key[:20]}...{api_key[-10:]}")
print()

try:
    import anthropic
    print("Testing API connection...")
    client = anthropic.Anthropic(api_key=api_key)
    print("Sending test request...")
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
    sys.exit(0)
    
except anthropic.APIError as e:
    print()
    print("=" * 60)
    print("❌ API ERROR")
    print("=" * 60)
    print(f"Error: {str(e)}")
    if "cloudflare" in str(e).lower() or "cf-" in str(e).lower():
        print("\n⚠️  CLOUDFLARE BLOCKING DETECTED")
    sys.exit(1)
    
except Exception as e:
    print()
    print("=" * 60)
    print("❌ CONNECTION ERROR")
    print("=" * 60)
    print(f"Error: {str(e)}")
    error_str = str(e).lower()
    if "cloudflare" in error_str or "cf-" in error_str:
        print("\n⚠️  CLOUDFLARE BLOCKING DETECTED")
    import traceback
    traceback.print_exc()
    sys.exit(1)

