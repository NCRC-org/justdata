#!/usr/bin/env python3
"""
Test script to verify Census API calls for demographic and income data.
"""

import os
import sys
from pathlib import Path
import requests

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Try to load .env from parent DREAM Analysis directory
try:
    from dotenv import load_dotenv
    # Try loading from current directory first
    load_dotenv()
    # Also try loading from parent DREAM Analysis directory
    dream_analysis_env = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\.env")
    if dream_analysis_env.exists():
        load_dotenv(dream_analysis_env, override=False)
except ImportError:
    pass

def test_census_api_key():
    """Test if Census API key is available."""
    api_key = os.getenv('CENSUS_API_KEY')
    if not api_key:
        print("[ERROR] CENSUS_API_KEY not found in environment variables")
        print("\nChecking .env files:")
        # Check current directory
        current_env = Path('.env')
        if current_env.exists():
            print(f"  [OK] Found .env in current directory: {current_env.absolute()}")
        else:
            print(f"  [X] No .env in current directory")
        
        # Check parent DREAM Analysis directory
        dream_env = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\.env")
        if dream_env.exists():
            print(f"  [OK] Found .env in DREAM Analysis directory: {dream_env}")
            # Try to read it
            try:
                with open(dream_env, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'CENSUS_API_KEY' in content:
                        print("  [OK] CENSUS_API_KEY found in .env file")
                        # Extract the key (simple parsing)
                        for line in content.split('\n'):
                            if line.strip().startswith('CENSUS_API_KEY'):
                                key_part = line.split('=')[1].strip()
                                if key_part:
                                    print(f"  [OK] Key appears to be set (first 10 chars: {key_part[:10]}...)")
                    else:
                        print("  [X] CENSUS_API_KEY not found in .env file")
            except Exception as e:
                print(f"  [X] Error reading .env file: {e}")
        else:
            print(f"  [X] No .env in DREAM Analysis directory")
        return None
    else:
        print(f"[OK] CENSUS_API_KEY found (first 10 chars: {api_key[:10]}...)")
        return api_key

def test_demographic_api(api_key, test_geoid='48059'):
    """Test fetching demographic data for a test county (Harris County, TX)."""
    print(f"\n{'='*60}")
    print("Testing Demographic Data API (Race/Ethnicity)")
    print(f"{'='*60}")
    
    acs_year = 2022
    acs_variables = [
        'B01003_001E',  # Total population
        'B03002_001E',  # Total (for race breakdown)
        'B03002_003E',  # White alone (not Hispanic)
        'B03002_004E',  # Black or African American alone (not Hispanic)
        'B03002_005E',  # American Indian/Alaska Native alone (not Hispanic)
        'B03002_006E',  # Asian alone (not Hispanic)
        'B03002_007E',  # Native Hawaiian/Pacific Islander alone (not Hispanic)
        'B03002_012E',  # Hispanic or Latino (of any race)
    ]
    
    state_fips = test_geoid[:2]
    county_fips = test_geoid[2:]
    
    url = f"https://api.census.gov/data/{acs_year}/acs/acs5"
    params = {
        'get': ','.join(acs_variables),
        'for': f'county:{county_fips}',
        'in': f'state:{state_fips}',
        'key': api_key
    }
    
    print(f"URL: {url}")
    print(f"Parameters: {params}")
    print(f"Testing with GEOID: {test_geoid} (State: {state_fips}, County: {county_fips})")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Success! Received {len(data)} rows")
            if len(data) > 1:
                headers = data[0]
                values = data[1]
                record = dict(zip(headers, values))
                
                print("\nData received:")
                print(f"  Total Population: {record.get('B01003_001E', 'N/A')}")
                print(f"  White (not Hispanic): {record.get('B03002_003E', 'N/A')}")
                print(f"  Black (not Hispanic): {record.get('B03002_004E', 'N/A')}")
                print(f"  Asian (not Hispanic): {record.get('B03002_006E', 'N/A')}")
                print(f"  Hispanic or Latino: {record.get('B03002_012E', 'N/A')}")
                return True
            else:
                print("[WARNING] Response has no data rows")
                return False
        else:
            print(f"[ERROR] Status Code: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_household_income_api(api_key, test_geoid='48059'):
    """Test fetching household income data."""
    print(f"\n{'='*60}")
    print("Testing Household Income Data API")
    print(f"{'='*60}")
    
    acs_year = 2022
    acs_variables = [
        'B19001_001E',  # Total households
        'B19001_002E',  # < $10,000
        'B19001_003E',  # $10,000 to $14,999
        'B19113_001E',  # Median family income
    ]
    
    state_fips = test_geoid[:2]
    county_fips = test_geoid[2:]
    
    url = f"https://api.census.gov/data/{acs_year}/acs/acs5"
    params = {
        'get': ','.join(acs_variables),
        'for': f'county:{county_fips}',
        'in': f'state:{state_fips}',
        'key': api_key
    }
    
    print(f"Testing with GEOID: {test_geoid}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Success! Received {len(data)} rows")
            if len(data) > 1:
                headers = data[0]
                values = data[1]
                record = dict(zip(headers, values))
                
                print("\nData received:")
                print(f"  Total Households: {record.get('B19001_001E', 'N/A')}")
                print(f"  < $10,000: {record.get('B19001_002E', 'N/A')}")
                print(f"  $10,000-$14,999: {record.get('B19001_003E', 'N/A')}")
                print(f"  Median Family Income: ${record.get('B19113_001E', 'N/A')}")
                return True
            else:
                print("[WARNING] Response has no data rows")
                return False
        else:
            print(f"[ERROR] Status Code: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tract_data_api(api_key, test_geoid='48059'):
    """Test fetching tract-level household data."""
    print(f"\n{'='*60}")
    print("Testing Tract-Level Household Data API")
    print(f"{'='*60}")
    
    acs_year = 2022
    household_variable = 'B11001_001E'  # Total households
    
    state_fips = test_geoid[:2]
    county_fips = test_geoid[2:]
    
    url = f"https://api.census.gov/data/{acs_year}/acs/acs5"
    params = {
        'get': f'NAME,{household_variable}',
        'for': 'tract:*',
        'in': f'state:{state_fips} county:{county_fips}',
        'key': api_key
    }
    
    print(f"Testing with GEOID: {test_geoid}")
    print("Fetching all tracts in county...")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Success! Received {len(data)} rows (including header)")
            if len(data) > 1:
                print(f"  Number of tracts: {len(data) - 1}")
                # Show first few tracts
                headers = data[0]
                print(f"\nFirst 3 tracts:")
                for i, row in enumerate(data[1:4], 1):
                    record = dict(zip(headers, row))
                    tract_code = record.get('tract', 'N/A')
                    households = record.get(household_variable, 'N/A')
                    print(f"  Tract {i}: {tract_code} - {households} households")
                return True
            else:
                print("[WARNING] Response has no data rows")
                return False
        else:
            print(f"[ERROR] Status Code: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("Census API Test Script")
    print("=" * 60)
    
    # Test 1: Check API key
    api_key = test_census_api_key()
    
    if not api_key:
        print("\n❌ Cannot proceed without API key. Please set CENSUS_API_KEY in .env file.")
        sys.exit(1)
    
    # Test 2: Demographic data
    demo_success = test_demographic_api(api_key)
    
    # Test 3: Household income data
    income_success = test_household_income_api(api_key)
    
    # Test 4: Tract-level data
    tract_success = test_tract_data_api(api_key)
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    print(f"Demographic Data: {'[PASS]' if demo_success else '[FAIL]'}")
    print(f"Household Income Data: {'[PASS]' if income_success else '[FAIL]'}")
    print(f"Tract-Level Data: {'[PASS]' if tract_success else '[FAIL]'}")
    
    if demo_success and income_success and tract_success:
        print("\n[OK] All tests passed! Census API is working correctly.")
    else:
        print("\n[ERROR] Some tests failed. Check the errors above.")

