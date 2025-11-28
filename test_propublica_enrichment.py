"""
Test script to see what additional data we can get from ProPublica API
"""
import json
import requests
import time

# File path
file_path = r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\enriched_members_cleaned_final.json"

# ProPublica API base URL
BASE_URL = "https://projects.propublica.org/nonprofits/api/v2"

def get_sample_eins(n=5):
    """Extract sample EINs from the data file"""
    print(f"Reading file: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Total records: {len(data)}")
    
    samples = []
    for item in data[:n*2]:  # Get more to ensure we have enough with EINs
        org = item.get('form_990', {}).get('organization', {})
        ein = org.get('ein')
        if ein and len(samples) < n:
            samples.append({
                'ein': ein,
                'strein': org.get('strein', ''),
                'company_name': item.get('company_name', ''),
                'org_name': org.get('name', '')
            })
    
    return samples

def test_api_with_ein(ein_info):
    """Test ProPublica API with a specific EIN"""
    ein = ein_info['ein']
    strein = ein_info['strein']
    
    print(f"\n{'='*80}")
    print(f"Testing EIN: {ein} ({strein})")
    print(f"Company Name: {ein_info['company_name']}")
    print(f"{'='*80}")
    
    # Search by EIN (using strein format)
    search_url = f"{BASE_URL}/search.json"
    params = {'q': strein}
    
    try:
        print(f"\nAPI Request: {search_url}?q={strein}")
        response = requests.get(search_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        print(f"Response Status: {response.status_code}")
        print(f"Total Results: {data.get('total_results', 0)}")
        print(f"Current Page: {data.get('cur_page', 0)}")
        
        if data.get('organizations'):
            org = data['organizations'][0]
            print(f"\n✓ Found Organization: {org.get('name')}")
            print(f"\nAvailable Fields in Organization Object:")
            print("-" * 80)
            
            # Group fields by category
            basic_info = {}
            address_info = {}
            classification_info = {}
            links_info = {}
            other_info = {}
            
            for key, value in sorted(org.items()):
                if value is not None and value != "":
                    if key in ['ein', 'strein', 'name', 'sub_name', 'updated']:
                        basic_info[key] = value
                    elif key in ['address', 'city', 'state', 'zipcode']:
                        address_info[key] = value
                    elif key in ['ntee_code', 'subseccd', 'classification', 'ruling_date', 'deductibility']:
                        classification_info[key] = value
                    elif key in ['guidestar_url', 'nccs_url']:
                        links_info[key] = value
                    else:
                        other_info[key] = value
            
            print("\n📋 BASIC INFORMATION:")
            for key, value in basic_info.items():
                print(f"  • {key}: {value}")
            
            print("\n📍 ADDRESS INFORMATION:")
            for key, value in address_info.items():
                print(f"  • {key}: {value}")
            
            print("\n🏷️ CLASSIFICATION INFORMATION:")
            for key, value in classification_info.items():
                print(f"  • {key}: {value}")
            
            print("\n🔗 EXTERNAL LINKS:")
            for key, value in links_info.items():
                print(f"  • {key}: {value}")
            
            print("\n📊 OTHER FIELDS:")
            for key, value in other_info.items():
                print(f"  • {key}: {value}")
            
            # Show full JSON structure
            print(f"\n📄 Full Organization Object (JSON):")
            print(json.dumps(org, indent=2))
            
            return org
        else:
            print("\n✗ No organizations found")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"\n✗ API Error: {e}")
        return None
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return None

def main():
    print("="*80)
    print("PROPUBLICA API ENRICHMENT TEST")
    print("="*80)
    
    # Get sample EINs
    samples = get_sample_eins(n=3)
    
    print(f"\nFound {len(samples)} sample organizations to test:")
    for i, sample in enumerate(samples, 1):
        print(f"  {i}. EIN {sample['ein']} ({sample['strein']}) - {sample['company_name']}")
    
    # Test API with each sample
    results = []
    for sample in samples:
        result = test_api_with_ein(sample)
        if result:
            results.append(result)
        time.sleep(1)  # Be respectful with API calls
    
    print(f"\n\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Successfully retrieved data for {len(results)} out of {len(samples)} organizations")
    
    if results:
        print("\nFields available from ProPublica API that could enhance your data:")
        all_fields = set()
        for result in results:
            all_fields.update(result.keys())
        
        print(f"\nTotal unique fields: {len(all_fields)}")
        print("\nField list:")
        for field in sorted(all_fields):
            print(f"  • {field}")

if __name__ == "__main__":
    main()

