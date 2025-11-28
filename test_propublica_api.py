import json
import requests
from urllib.parse import quote

# Read the JSON file and get sample EINs
file_path = r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\enriched_members_cleaned_final.json"

print("Reading file and extracting sample EINs...")
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total records: {len(data)}")

# Get a few sample EINs with their names
sample_eins = []
for item in data[:10]:
    org = item.get('form_990', {}).get('organization', {})
    ein = org.get('ein')
    if ein:
        sample_eins.append({
            'ein': ein,
            'strein': org.get('strein', ''),
            'name': item.get('company_name', ''),
            'org_name': org.get('name', '')
        })

print(f"\nFound {len(sample_eins)} sample EINs:")
for sample in sample_eins[:5]:
    print(f"  EIN: {sample['ein']} ({sample['strein']}) - {sample['name']}")

# Test ProPublica API
base_url = "https://projects.propublica.org/nonprofits/api/v2"

print("\n" + "="*80)
print("Testing ProPublica API with sample EINs...")
print("="*80)

for sample in sample_eins[:3]:  # Test with first 3
    ein = sample['ein']
    strein = sample['strein']
    
    print(f"\n--- Testing EIN: {ein} ({strein}) ---")
    print(f"Organization: {sample['name']}")
    
    # Method 1: Search by EIN (using strein format)
    search_url = f"{base_url}/search.json"
    params = {'q': strein}
    
    try:
        print(f"\n1. Searching by EIN: {search_url}?q={strein}")
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        search_data = response.json()
        
        print(f"   Status: {response.status_code}")
        print(f"   Total results: {search_data.get('total_results', 0)}")
        
        if search_data.get('organizations'):
            org = search_data['organizations'][0]
            print(f"   Found organization: {org.get('name')}")
            print(f"   Available fields in organization object:")
            for key in sorted(org.keys()):
                value = org[key]
                if value is not None and value != "":
                    print(f"     - {key}: {value}")
        else:
            print("   No organizations found in search results")
            
    except Exception as e:
        print(f"   Error: {e}")
    
    # Method 2: Try direct organization endpoint (if it exists)
    # Note: The API docs don't show a direct /organizations/{ein} endpoint,
    # but let's check what fields we get from search
    
    print("\n" + "-"*80)

print("\n" + "="*80)
print("Analysis complete!")
print("="*80)

