#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("CLAUDE_API_KEY")

if not api_key:
    print("ERROR: No API key found")
    exit(1)

print(f"API Key: {api_key[:20]}...")
print("Testing connection...")

try:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=50,
        messages=[{"role": "user", "content": "Say 'test successful'"}]
    )
    print("SUCCESS:", response.content[0].text)
except Exception as e:
    print("ERROR:", str(e))
    if "cloudflare" in str(e).lower() or "cf-" in str(e).lower():
        print("CLOUDFLARE BLOCKING DETECTED")

