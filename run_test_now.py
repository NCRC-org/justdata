"""Run API test now - self-contained"""
import json
import urllib.request
import urllib.parse
import sys

print("="*80)
print("PROPUBLICA API TEST - Running Now")
print("="*80)

# Test with sample EINs from your data
test_eins = [
    ("46-5333729", "Center for Housing Economics"),
    ("82-3374968", "The Resiliency Collaborative Inc"),
    ("82-1125482", "City Fields")
]

base_url = "https://projects.propublica.org/nonprofits/api/v2/search.json"

results = []

for strein, name in test_eins:
    print(f"\n{'='*80}")
    print(f"Testing EIN: {strein}")
    print(f"Organization: {name}")
    print(f"{'='*80}")
    
    params = {'q': strein}
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        print(f"\nRequesting: {url}")
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.loads(response.read().decode())
        
        print(f"✓ Success! Status: {response.status}")
        print(f"Total Results: {data.get('total_results', 0)}")
        
        if data.get('organizations'):
            org = data['organizations'][0]
            print(f"\n✓ Found: {org.get('name')}")
            print(f"\nAvailable Fields ({len(org)} total):")
            print("-" * 80)
            
            # Group fields
            fields_by_category = {
                'Basic Info': ['ein', 'strein', 'name', 'sub_name', 'updated'],
                'Address': ['address', 'city', 'state', 'zipcode'],
                'Classification': ['ntee_code', 'subseccd', 'classification', 'ruling_date', 'deductibility'],
                'Links': ['guidestar_url', 'nccs_url'],
                'Other': []
            }
            
            categorized = {cat: {} for cat in fields_by_category}
            
            for key, value in sorted(org.items()):
                if value is not None and value != "":
                    categorized_flag = False
                    for cat, fields in fields_by_category.items():
                        if key in fields:
                            categorized[cat][key] = value
                            categorized_flag = True
                            break
                    if not categorized_flag:
                        categorized['Other'][key] = value
            
            for cat, fields in categorized.items():
                if fields:
                    print(f"\n{cat}:")
                    for key, value in sorted(fields.items()):
                        display_value = str(value)
                        if len(display_value) > 70:
                            display_value = display_value[:67] + "..."
                        print(f"  • {key:20s}: {display_value}")
            
            results.append({
                'ein': strein,
                'organization': org,
                'success': True
            })
        else:
            print("\n✗ No organizations found")
            results.append({
                'ein': strein,
                'success': False
            })
            
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        results.append({
            'ein': strein,
            'error': str(e),
            'success': False
        })

# Summary
print(f"\n\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")
successful = sum(1 for r in results if r.get('success'))
print(f"Successfully retrieved data for {successful} out of {len(test_eins)} organizations")

if successful > 0:
    print("\nFields available from ProPublica API:")
    all_fields = set()
    for r in results:
        if r.get('success'):
            all_fields.update(r['organization'].keys())
    
    print(f"\nTotal unique fields: {len(all_fields)}")
    print("\nField list:")
    for field in sorted(all_fields):
        print(f"  • {field}")

# Save results
try:
    with open('api_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Full results saved to: api_test_results.json")
except Exception as e:
    print(f"\nNote: Could not save results file: {e}")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)

