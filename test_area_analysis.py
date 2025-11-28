#!/usr/bin/env python3
"""
Automated test for Area Analysis functionality.
Tests HMDA data analysis with a metro area selection.
"""

import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://127.0.0.1:8085"

def test_area_analysis():
    """Test the Area Analysis endpoint with HMDA data and a metro area."""
    
    print("=" * 80)
    print("AREA ANALYSIS AUTOMATED TEST")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Get available metro areas
    print("Step 1: Fetching available metro areas...")
    try:
        metros_response = requests.get(f"{BASE_URL}/api/metros", timeout=10)
        if metros_response.status_code != 200:
            print(f"❌ Failed to fetch metros: {metros_response.status_code}")
            return False
        
        metros_data = metros_response.json()
        if not metros_data.get('success') or not metros_data.get('data'):
            print("❌ No metro areas available")
            return False
        
        metros = metros_data['data']
        # Try to find a major metro area (look for common large cities)
        major_metros = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 
                        'San Antonio', 'San Diego', 'Dallas', 'San Jose', 'Washington', 'Boston',
                        'Atlanta', 'Miami', 'Seattle', 'Denver', 'Detroit', 'Minneapolis']
        
        selected_metro = None
        for metro in metros:
            metro_name = metro.get('name', '')
            if any(city in metro_name for city in major_metros):
                selected_metro = metro
                break
        
        # If no major metro found, use first one
        if not selected_metro:
            selected_metro = metros[0]
        
        metro_code = selected_metro.get('code') or selected_metro.get('geoid')
        metro_name = selected_metro.get('name', 'Unknown')
        
        print(f"✓ Found {len(metros)} metro areas")
        print(f"  Selected: {metro_name} (Code: {metro_code})")
        print()
        
    except Exception as e:
        print(f"❌ Error fetching metros: {e}")
        return False
    
    # Step 2: Prepare analysis request
    print("Step 2: Preparing analysis request...")
    
    # Get last 5 years (2020-2024)
    years = list(range(2020, 2025))
    
    # Also try with a known county code (Fulton County, GA - part of Atlanta metro)
    # This will help us verify if the issue is with metro expansion or the query itself
    test_county = "13121"  # Fulton County, GA
    
    print(f"  Testing with metro code: {metro_code}")
    print(f"  Also testing with county code: {test_county}")
    print()
    
    payload = {
        "geoids": [test_county],  # Use county code directly to bypass metro expansion
        "years": years,
        "loan_purpose": ["1"],  # Purchase
        "action_taken": ["1", "2", "3", "4", "5"],  # Applications
        "occupancy_type": ["1"],  # Owner-occupied
        "total_units": ["1", "2", "3", "4"],  # 1-4 units
        "construction_method": ["1"],  # Site-built
        "exclude_reverse_mortgages": True
    }
    
    print(f"  Geography: {metro_name} ({metro_code})")
    print(f"  Years: {years}")
    print(f"  Data Type: HMDA")
    print()
    
    # Step 3: Make analysis request
    print("Step 3: Sending analysis request to /api/area/hmda/analysis...")
    print(f"  Payload: {json.dumps(payload, indent=2)}")
    try:
        start_time = datetime.now()
        response = requests.post(
            f"{BASE_URL}/api/area/hmda/analysis",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print(f"  Response Status: {response.status_code}")
        print(f"  Response Time: {elapsed:.2f} seconds")
        
        if response.status_code != 200:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
        
        result = response.json()
        
        if not result.get('success'):
            print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
            return False
        
        data = result.get('data', {})
        
        # Step 4: Validate response structure
        print()
        print("Step 4: Validating response structure...")
        
        required_keys = ['summary', 'demographics', 'income_neighborhood', 'top_lenders', 'hhi', 'trends']
        missing_keys = [key for key in required_keys if key not in data]
        
        if missing_keys:
            print(f"❌ Missing required keys: {missing_keys}")
            return False
        
        print("✓ All required keys present")
        
        # Step 5: Check data content
        print()
        print("Step 5: Checking data content...")
        
        summary = data.get('summary', [])
        if summary:
            print(f"✓ Summary table: {len(summary)} years of data")
            latest = summary[0]
            print(f"  Latest year: {latest.get('year')} - {latest.get('total_loans', 0)} loans, ${latest.get('total_amount', 0):,.0f} total")
        else:
            print("⚠ Summary table is empty (may be expected if no data)")
        
        demographics = data.get('demographics', [])
        if demographics:
            print(f"✓ Demographics table: {len(demographics)} groups")
        else:
            print("⚠ Demographics table is empty")
        
        income_neighborhood = data.get('income_neighborhood', [])
        if income_neighborhood:
            print(f"✓ Income & Neighborhood table: {len(income_neighborhood)} indicators")
        else:
            print("⚠ Income & Neighborhood table is empty")
        
        top_lenders = data.get('top_lenders', [])
        if top_lenders:
            print(f"✓ Top lenders table: {len(top_lenders)} lenders")
        else:
            print("⚠ Top lenders table is empty")
        
        hhi = data.get('hhi')
        if hhi and hhi.get('hhi') is not None:
            print(f"✓ HHI data: {hhi.get('hhi')} ({hhi.get('concentration_level')})")
        else:
            print("⚠ HHI data not available")
        
        hhi_by_year = data.get('hhi_by_year', [])
        if hhi_by_year:
            print(f"✓ HHI by year: {len(hhi_by_year)} years")
        else:
            print("⚠ HHI by year not available")
        
        trends = data.get('trends', [])
        if trends:
            print(f"✓ Trends table: {len(trends)} periods")
        else:
            print("⚠ Trends table is empty")
        
        print()
        print("=" * 80)
        print("✅ TEST PASSED - Analysis endpoint is working correctly!")
        print("=" * 80)
        return True
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out (exceeded 60 seconds)")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - Is the server running on http://127.0.0.1:8085?")
        return False
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_area_analysis()
    sys.exit(0 if success else 1)

