#!/usr/bin/env python3
"""
Detailed test script to debug the HMDA SQL query.
"""

import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared.utils.bigquery_client import get_bigquery_client, execute_query
from apps.lendsight.config import PROJECT_ID, DATASET_ID, TABLE_ID
from apps.lendsight.data_utils import find_exact_county_match

def test_county_matching():
    """Test county name matching."""
    print("=" * 80)
    print("TESTING COUNTY NAME MATCHING")
    print("=" * 80)
    
    test_counties = [
        "Montgomery County, Maryland",
        "Montgomery, Maryland",
        "Montgomery County, MD",
        "Montgomery, MD"
    ]
    
    for county in test_counties:
        print(f"\nTesting: '{county}'")
        matches = find_exact_county_match(county)
        if matches:
            print(f"  Found matches: {matches[:5]}")
        else:
            print(f"  No matches found")

def test_simple_query():
    """Test a simple query to see if data exists."""
    print("\n" + "=" * 80)
    print("TESTING SIMPLE QUERY (no joins)")
    print("=" * 80)
    
    try:
        client = get_bigquery_client(PROJECT_ID)
        
        # Simple query to check if data exists
        query = f"""
        SELECT 
            activity_year,
            state_code,
            county_code,
            COUNT(*) as record_count,
            COUNT(DISTINCT lei) as unique_lenders
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        WHERE activity_year = '2023'
        AND state_code = '24'  -- Maryland
        GROUP BY activity_year, state_code, county_code
        ORDER BY record_count DESC
        LIMIT 10
        """
        
        print("\nExecuting simple query...")
        results = execute_query(client, query)
        
        print(f"\nFound {len(results)} county records for Maryland in 2023:")
        for row in results:
            print(f"  State: {row.get('state_code')}, County: {row.get('county_code')}, Records: {row.get('record_count'):,}, Lenders: {row.get('unique_lenders')}")
        
        return results
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_geoid5_derivation():
    """Test geoid5 derivation."""
    print("\n" + "=" * 80)
    print("TESTING GEOID5 DERIVATION")
    print("=" * 80)
    
    try:
        client = get_bigquery_client(PROJECT_ID)
        
        query = f"""
        SELECT 
            state_code,
            county_code,
            CONCAT(LPAD(state_code, 2, '0'), LPAD(county_code, 3, '0')) as geoid5,
            COUNT(*) as record_count
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        WHERE activity_year = '2023'
        AND state_code = '24'  -- Maryland
        GROUP BY state_code, county_code, geoid5
        ORDER BY record_count DESC
        LIMIT 5
        """
        
        print("\nTesting geoid5 derivation...")
        results = execute_query(client, query)
        
        for row in results:
            print(f"  State: {row.get('state_code')}, County: {row.get('county_code')}, GEOID5: {row.get('geoid5')}, Records: {row.get('record_count'):,}")
        
        return results
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_lenders18_join():
    """Test if lenders18 table exists and can be joined."""
    print("\n" + "=" * 80)
    print("TESTING LENDERS18 TABLE JOIN")
    print("=" * 80)
    
    try:
        client = get_bigquery_client(PROJECT_ID)
        
        # Test if lenders18 table exists
        query = f"""
        SELECT 
            h.lei,
            l.respondent_name,
            COUNT(*) as record_count
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` h
        LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.lenders18` l
            ON h.lei = l.lei
        WHERE h.activity_year = '2023'
        AND h.state_code = '24'  -- Maryland
        GROUP BY h.lei, l.respondent_name
        ORDER BY record_count DESC
        LIMIT 10
        """
        
        print("\nTesting lenders18 join...")
        results = execute_query(client, query)
        
        print(f"\nFound {len(results)} lender records:")
        lenders_with_names = sum(1 for r in results if r.get('respondent_name'))
        print(f"  Lenders with names: {lenders_with_names} / {len(results)}")
        
        for row in results[:5]:
            lei = row.get('lei', 'N/A')[:20] + '...' if row.get('lei') and len(row.get('lei')) > 20 else row.get('lei', 'N/A')
            name = row.get('respondent_name', 'NULL')
            if name and len(name) > 40:
                name = name[:37] + '...'
            print(f"  LEI: {lei:25} Name: {name}")
        
        return results
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nThis might indicate:")
        print("  - lenders18 table doesn't exist in hmda dataset")
        print("  - Table name is different (e.g., lenders_18, lenders)")
        print("  - Table is in a different dataset")
        import traceback
        traceback.print_exc()
        return []

def test_geo_join():
    """Test geo.cbsa_to_county join."""
    print("\n" + "=" * 80)
    print("TESTING GEO.CBSA_TO_COUNTY JOIN")
    print("=" * 80)
    
    try:
        client = get_bigquery_client(PROJECT_ID)
        
        query = f"""
        SELECT 
            CONCAT(LPAD(h.state_code, 2, '0'), LPAD(h.county_code, 3, '0')) as geoid5,
            c.county_state,
            COUNT(*) as record_count
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` h
        LEFT JOIN `{PROJECT_ID}.geo.cbsa_to_county` c
            ON CONCAT(LPAD(h.state_code, 2, '0'), LPAD(h.county_code, 3, '0')) = CAST(c.geoid5 AS STRING)
        WHERE h.activity_year = '2023'
        AND h.state_code = '24'  -- Maryland
        GROUP BY geoid5, c.county_state
        ORDER BY record_count DESC
        LIMIT 10
        """
        
        print("\nTesting geo.cbsa_to_county join...")
        results = execute_query(client, query)
        
        print(f"\nFound {len(results)} county records:")
        counties_with_names = sum(1 for r in results if r.get('county_state'))
        print(f"  Counties with names: {counties_with_names} / {len(results)}")
        
        for row in results[:5]:
            geoid5 = row.get('geoid5', 'N/A')
            county = row.get('county_state', 'NULL')
            print(f"  GEOID5: {geoid5:10} County: {county}")
        
        return results
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == '__main__':
    test_county_matching()
    test_simple_query()
    test_geoid5_derivation()
    test_lenders18_join()
    test_geo_join()

