import json
import urllib.request
import urllib.parse

# Make API call
url = "https://projects.propublica.org/nonprofits/api/v2/search.json?q=46-5333729"
with urllib.request.urlopen(url, timeout=15) as response:
    data = json.loads(response.read().decode())

# Save to file
with open('api_response.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print("API call successful! Response saved to api_response.json")

