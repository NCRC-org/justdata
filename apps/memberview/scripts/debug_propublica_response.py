"""Debug script to see what ProPublica API actually returns."""
import sys
from pathlib import Path
import json

BASE_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from apps.memberview.utils.propublica_client import ProPublicaClient

# Test with a known EIN from the test results
client = ProPublicaClient()

# Test EIN: 465333729 (Center for Housing Economics)
ein = "465333729"
print(f"Testing EIN: {ein}")
print("=" * 80)

import requests

# Try direct API call to see full response
url = f"https://projects.propublica.org/nonprofits/api/v2/organizations/{ein}.json"
response = requests.get(url)
if response.status_code == 200:
    data = response.json()
    print("\nFull API Response Structure:")
    print(f"Top-level keys: {list(data.keys())}")
    
    org = data.get('organization')
    if org:
        print("\nOrganization keys:")
        print(list(org.keys())[:30])
        
        # Check for filings_with_data or other nested structures
        if 'filings_with_data' in data:
            print("\nFound filings_with_data!")
            filings = data['filings_with_data']
            print(f"Number of filings: {len(filings)}")
            if filings:
                latest = filings[0]
                print(f"Latest filing keys: {list(latest.keys())[:40]}")
                print(f"  totrevenue: {latest.get('totrevenue')}")
                print(f"  totfuncexpns: {latest.get('totfuncexpns')}")
                print(f"  compnsatncurrofcr: {latest.get('compnsatncurrofcr')}")
        
        # Also check if there's a separate filings endpoint
        filings_url = f"https://projects.propublica.org/nonprofits/api/v2/organizations/{ein}/filings.json"
        filings_response = requests.get(filings_url)
        if filings_response.status_code == 200:
            filings_data = filings_response.json()
            print("\n\nFilings endpoint response:")
            print(f"Keys: {list(filings_data.keys())}")
            if 'filings' in filings_data:
                print(f"Number of filings: {len(filings_data['filings'])}")
                if filings_data['filings']:
                    latest = filings_data['filings'][0]
                    print(f"Latest filing keys: {list(latest.keys())[:40]}")
                    print(f"  total_revenue: {latest.get('total_revenue')}")
                    print(f"  total_expenses: {latest.get('total_expenses')}")
                    print(f"  revenue: {latest.get('revenue')}")
                    print(f"  expenses: {latest.get('expenses')}")
                    print(f"  totrevenue: {latest.get('totrevenue')}")
                    print(f"  totfuncexpns: {latest.get('totfuncexpns')}")
else:
    print(f"API call failed: {response.status_code}")

