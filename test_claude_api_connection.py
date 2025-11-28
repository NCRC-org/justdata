#!/usr/bin/env python3
"""
Test Claude API connection and verify it's working.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_claude_api():
    """Test Claude API connection."""
    print("=" * 60)
    print("Testing Claude API Connection")
    print("=" * 60)
    print()
    
    # Check for API key
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        print("❌ ERROR: CLAUDE_API_KEY not found in environment variables")
        print()
        print("Please check:")
        print("1. You have a .env file in the project root")
        print("2. The .env file contains: CLAUDE_API_KEY=sk-ant-...")
        return False
    
    print(f"✓ API Key found: {api_key[:20]}...{api_key[-10:]}")
    print()
    
    # Test API connection
    try:
        import anthropic
        print("Testing API connection...")
        
        client = anthropic.Anthropic(api_key=api_key)
        
        # Simple test prompt
        test_prompt = "Say 'Hello, API test successful!' and nothing else."
        
        print("Sending test request to Claude API...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{"role": "user", "content": test_prompt}]
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
        return True
        
    except anthropic.APIError as e:
        print()
        print("=" * 60)
        print("❌ API ERROR")
        print("=" * 60)
        print()
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print()
        
        if "401" in str(e) or "authentication" in str(e).lower():
            print("This appears to be an authentication error.")
            print("Please check that your API key is valid.")
        elif "429" in str(e) or "rate limit" in str(e).lower():
            print("This appears to be a rate limit error.")
            print("You may have exceeded your API usage limits.")
        elif "cloudflare" in str(e).lower() or "cf-" in str(e).lower():
            print("This appears to be a Cloudflare blocking issue.")
            print("The API endpoint may be blocked by Cloudflare.")
        else:
            print("This is an unexpected API error.")
        
        return False
        
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
            print("⚠️  CLOUDFLARE DETECTED")
            print()
            print("Possible solutions:")
            print("1. Check if you're behind a corporate firewall/proxy")
            print("2. Try using a VPN or different network")
            print("3. Check if Cloudflare is blocking the Anthropic API endpoint")
            print("4. Contact your network administrator")
        elif "timeout" in error_str:
            print("This appears to be a timeout error.")
            print("The API request took too long to complete.")
        elif "connection" in error_str or "network" in error_str:
            print("This appears to be a network connectivity issue.")
            print("Please check your internet connection.")
        else:
            print("This is an unexpected error.")
            import traceback
            traceback.print_exc()
        
        return False

if __name__ == "__main__":
    success = test_claude_api()
    print()
    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Tests failed. Please check the errors above.")
        sys.exit(1)

