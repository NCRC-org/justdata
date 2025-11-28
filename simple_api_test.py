"""
Simple test using only Python standard library - no external dependencies
"""
import json
import urllib.request
import urllib.parse

# Test with a sample EIN from your data
test_ein = "46-5333729"  # Center for Housing Economics
base_url = "https://projects.propublica.org/nonprofits/api/v2/search.json"

# Build URL
params = {'q': test_ein}
url = f"{base_url}?{urllib.parse.urlencode(params)}"

print("="*80)
print("PROPUBLICA API TEST - Using Standard Library Only")
print("="*80)
print(f"\nTesting EIN: {test_ein}")
print(f"Request URL: {url}\n")

try:
    # Make request
    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.loads(response.read().decode())
    
    print(f"✓ Success! Status: {response.status}")
    print(f"\nTotal Results: {data.get('total_results', 0)}")
    
    if data.get('organizations'):
        org = data['organizations'][0]
        print(f"\n✓ Found Organization: {org.get('name')}")
        print(f"\nAvailable Fields ({len(org)} total):")
        print("-" * 80)
        
        # Show all fields
        for key, value in sorted(org.items()):
            if value is not None and value != "":
                # Truncate long values for display
                display_value = str(value)
                if len(display_value) > 80:
                    display_value = display_value[:77] + "..."
                print(f"  • {key:20s}: {display_value}")
        
        print("\n" + "="*80)
        print("FULL JSON RESPONSE:")
        print("="*80)
        print(json.dumps(org, indent=2))
        
    else:
        print("\n✗ No organizations found in response")
        print("\nFull response:")
        print(json.dumps(data, indent=2))
        
except urllib.error.HTTPError as e:
    print(f"\n✗ HTTP Error: {e.code} - {e.reason}")
    if e.fp:
        error_body = e.fp.read().decode()
        print(f"Error details: {error_body}")
except Exception as e:
    print(f"\n✗ Error: {type(e).__name__}: {e}")

