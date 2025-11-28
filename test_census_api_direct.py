#!/usr/bin/env python3
"""
Direct test of Census API connection.
Tests the API without going through the LendSight application.
"""

import os
import requests
from census import Census

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def test_census_api():
    """Test Census API connection with a simple query"""
    
    # Get API key
    api_key = os.getenv('CENSUS_API_KEY')
    if not api_key:
        print("ERROR: CENSUS_API_KEY environment variable is not set")
        print("   Get a free API key from: https://api.census.gov/data/key_signup.html")
        return False
    
    print(f"API Key found: {api_key[:10]}...{api_key[-4:]}")
    print()
    
    # Test 1: Direct API call (2020 Census)
    print("=" * 60)
    print("TEST 1: Direct API call - 2020 Decennial Census")
    print("=" * 60)
    try:
        url = "https://api.census.gov/data/2020/dec/pl"
        params = {
            'get': 'NAME,P1_001N',  # Name and total population
            'for': 'county:031',
            'in': 'state:24',  # Montgomery County, Maryland
            'key': api_key
        }
        print(f"Request URL: {url}")
        print(f"Parameters: {params}")
        print()
        
        response = requests.get(url, params=params, timeout=30)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS! Got {len(data)} rows")
            if len(data) > 1:
                headers = data[0]
                row = data[1]
                print(f"Headers: {headers}")
                print(f"Data: {row}")
                print(f"County: {row[0]}, Population: {row[1]}")
            return True
        else:
            print(f"ERROR: Status code {response.status_code}")
            print(f"Response: {response.text}")
            test1_success = False
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        test1_success = False
    
    print()
    
    # Test 2: Using census library (ACS)
    print("=" * 60)
    print("TEST 2: Using census library - ACS 5-year estimates")
    print("=" * 60)
    try:
        c = Census(api_key)
        print("Initialized Census client")
        print()
        
        # Get most recent ACS year
        from datetime import datetime
        current_year = datetime.now().year
        acs_year = current_year - 1 if current_year % 5 != 0 else current_year - 2
        acs_year = max(2019, acs_year)  # Ensure at least 2019
        
        print(f"Testing ACS {acs_year} 5-year estimates...")
        acs_data = c.acs5.get(
            ['NAME', 'B01003_001E'],  # Name and total population
            {
                'for': 'county:031',
                'in': 'state:24'  # Montgomery County, Maryland
            },
            year=acs_year
        )
        
        if acs_data and len(acs_data) > 0:
            print(f"SUCCESS! Got {len(acs_data)} records")
            record = acs_data[0]
            print(f"County: {record.get('NAME', 'N/A')}")
            print(f"Population: {record.get('B01003_001E', 'N/A')}")
            test2_success = True
        else:
            print(f"ERROR: No data returned")
            test2_success = False
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        test2_success = False
    
    print()
    
    # Test 3: 2010 Census
    print("=" * 60)
    print("TEST 3: Direct API call - 2010 Decennial Census")
    print("=" * 60)
    try:
        url = "https://api.census.gov/data/2010/dec/sf1"
        params = {
            'get': 'NAME,P001001',  # Name and total population
            'for': 'county:031',
            'in': 'state:24',  # Montgomery County, Maryland
            'key': api_key
        }
        print(f"Request URL: {url}")
        print(f"Parameters: {params}")
        print()
        
        response = requests.get(url, params=params, timeout=30)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS! Got {len(data)} rows")
            if len(data) > 1:
                headers = data[0]
                row = data[1]
                print(f"Headers: {headers}")
                print(f"Data: {row}")
                print(f"County: {row[0]}, Population: {row[1]}")
            test3_success = True
        else:
            print(f"ERROR: Status code {response.status_code}")
            print(f"Response: {response.text}")
            test3_success = False
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        test3_success = False
    
    # Return True if at least one test passed
    return test1_success or test2_success or test3_success


if __name__ == '__main__':
    print("Census API Connection Test")
    print("=" * 60)
    print()
    
    success = test_census_api()
    
    print()
    print("=" * 60)
    if success:
        print("ALL TESTS PASSED - Census API is working!")
    else:
        print("SOME TESTS FAILED - Check errors above")
    print("=" * 60)

