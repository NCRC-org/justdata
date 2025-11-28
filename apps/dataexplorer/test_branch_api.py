#!/usr/bin/env python3
"""
Quick test script to check what the branch analysis API actually returns.
Run this to verify the data structure matches what the frontend expects.
"""

import requests
import json

# Test with a simple request (adjust geoids as needed)
test_data = {
    "geoids": ["48201"],  # Harris County, TX
    "data_type": "branches",
    "years": [2020, 2021, 2022, 2023, 2024, 2025]
}

print("=" * 80)
print("Testing Branch Analysis API")
print("=" * 80)
print(f"\nRequest: {json.dumps(test_data, indent=2)}\n")

try:
    response = requests.post(
        "http://127.0.0.1:8085/api/area/branches/analysis",
        json=test_data,
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}\n")
    
    if response.status_code == 200:
        data = response.json()
        print("Response Structure:")
        print(f"  success: {data.get('success')}")
        print(f"  data keys: {list(data.get('data', {}).keys())}")
        
        income_neighborhood = data.get('data', {}).get('income_neighborhood', [])
        print(f"\nIncome & Neighborhood Table:")
        print(f"  Number of rows: {len(income_neighborhood)}")
        if income_neighborhood:
            print(f"  First row: {json.dumps(income_neighborhood[0], indent=4)}")
            print(f"  Indicators found:")
            for row in income_neighborhood[:5]:
                print(f"    - {row.get('indicator')}")
        
        summary = data.get('data', {}).get('summary', [])
        print(f"\nSummary Table:")
        print(f"  Number of rows: {len(summary)}")
        if summary:
            print(f"  First row: {json.dumps(summary[0], indent=4)}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)

