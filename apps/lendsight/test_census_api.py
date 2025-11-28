#!/usr/bin/env python3
"""
Test script to verify Census API is working correctly.
"""

import os
import sys

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..')
sys.path.insert(0, project_root)

from dotenv import load_dotenv
# Load .env from project root
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)
print(f"[DEBUG] Looking for .env at: {env_path}")
print(f"[DEBUG] .env file exists: {os.path.exists(env_path)}")

def test_census_api():
    """Test Census API connection and data retrieval."""
    print("=" * 60)
    print("Census API Test")
    print("=" * 60)
    
    # Check if API key is set
    api_key = os.getenv('CENSUS_API_KEY')
    if not api_key:
        print("\n[ERROR] CENSUS_API_KEY environment variable is NOT SET")
        print("Please set it in your .env file or environment variables")
        print("Get a free API key from: https://api.census.gov/data/key_signup.html")
        return False
    
    print(f"\n[OK] CENSUS_API_KEY is set (length: {len(api_key)} characters)")
    
    # Check if census package is installed
    try:
        from census import Census
        print("[OK] 'census' package is installed")
    except ImportError:
        print("[ERROR] 'census' package is NOT installed")
        print("Install with: pip install census us requests")
        return False
    
    # Test API connection with a simple query
    try:
        c = Census(api_key)
        print("[OK] Census client initialized")
        
        # Test with a known county (Montgomery County, Maryland - FIPS: 24031)
        print("\nTesting API call for Montgomery County, Maryland...")
        data = c.acs5.get(
            ['B01003_001E'],  # Total population
            {'for': 'county:031', 'in': 'state:24'},
            year=2022
        )
        
        if data and len(data) > 0:
            population = data[0].get('B01003_001E', 'N/A')
            print(f"[OK] API call successful! Population: {population}")
            return True
        else:
            print("[ERROR] API call returned no data")
            return False
            
    except Exception as e:
        print(f"[ERROR] API call failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_census_api()
    sys.exit(0 if success else 1)

