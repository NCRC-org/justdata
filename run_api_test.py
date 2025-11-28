"""
Run API test and save results to file
"""
import json
import urllib.request
import urllib.parse
import sys

# Test with a sample EIN from your data
test_ein = "46-5333729"  # Center for Housing Economics
base_url = "https://projects.propublica.org/nonprofits/api/v2/search.json"

# Build URL
params = {'q': test_ein}
url = f"{base_url}?{urllib.parse.urlencode(params)}"

output_lines = []
output_lines.append("="*80)
output_lines.append("PROPUBLICA API TEST - Using Standard Library Only")
output_lines.append("="*80)
output_lines.append(f"\nTesting EIN: {test_ein}")
output_lines.append(f"Request URL: {url}\n")

try:
    # Make request
    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.loads(response.read().decode())
    
    output_lines.append(f"✓ Success! Status: {response.status}")
    output_lines.append(f"\nTotal Results: {data.get('total_results', 0)}")
    
    if data.get('organizations'):
        org = data['organizations'][0]
        output_lines.append(f"\n✓ Found Organization: {org.get('name')}")
        output_lines.append(f"\nAvailable Fields ({len(org)} total):")
        output_lines.append("-" * 80)
        
        # Show all fields
        for key, value in sorted(org.items()):
            if value is not None and value != "":
                # Truncate long values for display
                display_value = str(value)
                if len(display_value) > 80:
                    display_value = display_value[:77] + "..."
                output_lines.append(f"  • {key:20s}: {display_value}")
        
        output_lines.append("\n" + "="*80)
        output_lines.append("FULL JSON RESPONSE:")
        output_lines.append("="*80)
        output_lines.append(json.dumps(org, indent=2))
        
        # Also save full response to JSON file
        with open('api_test_result.json', 'w', encoding='utf-8') as f:
            json.dump({'request': {'ein': test_ein, 'url': url}, 'response': data}, f, indent=2)
        output_lines.append(f"\n✓ Full response saved to: api_test_result.json")
        
    else:
        output_lines.append("\n✗ No organizations found in response")
        output_lines.append("\nFull response:")
        output_lines.append(json.dumps(data, indent=2))
        
except urllib.error.HTTPError as e:
    output_lines.append(f"\n✗ HTTP Error: {e.code} - {e.reason}")
    if e.fp:
        error_body = e.fp.read().decode()
        output_lines.append(f"Error details: {error_body}")
except Exception as e:
    output_lines.append(f"\n✗ Error: {type(e).__name__}: {e}")
    import traceback
    output_lines.append(traceback.format_exc())

# Write output
output_text = "\n".join(output_lines)
print(output_text)

# Also save to file
with open('api_test_output.txt', 'w', encoding='utf-8') as f:
    f.write(output_text)

print(f"\n✓ Output also saved to: api_test_output.txt")

