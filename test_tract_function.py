#!/usr/bin/env python3
"""
Test the tract distribution function directly to see what's failing.
"""

import sys
import os
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

# Load environment variables
try:
    from dotenv import load_dotenv
    dream_analysis_env = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\.env")
    if dream_analysis_env.exists():
        load_dotenv(dream_analysis_env, override=False)
        print(f"Loaded .env from: {dream_analysis_env}")
except ImportError:
    print("python-dotenv not available")

# Check API key
api_key = os.getenv('CENSUS_API_KEY')
print(f"\nCENSUS_API_KEY present: {api_key is not None}")
if api_key:
    print(f"CENSUS_API_KEY length: {len(api_key)}")
    print(f"CENSUS_API_KEY first 10 chars: {api_key[:10]}...")
else:
    print("ERROR: CENSUS_API_KEY is NOT set!")
    print("This will prevent tract data from loading.")
    sys.exit(1)

# Test the function
print("\n" + "=" * 80)
print("TESTING get_tract_household_distributions_for_geoids")
print("=" * 80)

try:
    from apps.dataexplorer.acs_utils import get_tract_household_distributions_for_geoids
    
    # Test with Abilene, TX (Taylor County, GEOID5: 48441)
    test_geoids = ['48441']
    print(f"\nTesting with GEOIDs: {test_geoids}")
    print("This is Taylor County, TX (Abilene)")
    
    result = get_tract_household_distributions_for_geoids(test_geoids, avg_minority_percentage=None)
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"tract_income_distribution: {result.get('tract_income_distribution', {})}")
    print(f"tract_minority_distribution: {result.get('tract_minority_distribution', {})}")
    
    if not result.get('tract_income_distribution') and not result.get('tract_minority_distribution'):
        print("\nERROR: Both distributions are empty!")
        print("Check the logs above for errors.")
    else:
        print("\nSUCCESS: Data returned!")
        
except Exception as e:
    print(f"\nERROR: Exception occurred: {e}")
    import traceback
    traceback.print_exc()

