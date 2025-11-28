#!/usr/bin/env python3
"""
Test script to check the actual data structure in HMDA table.
"""

import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared.utils.bigquery_client import get_bigquery_client, execute_query
from apps.lendsight.config import PROJECT_ID, DATASET_ID, TABLE_ID

def test_data_structure():
    """Check what the actual data looks like."""
    print("=" * 80)
    print("TESTING DATA STRUCTURE")
    print("=" * 80)
    
    try:
        client = get_bigquery_client(PROJECT_ID)
        
        # Check a sample of raw data
        print("\n1. Sample raw data (first 5 rows):")
        query1 = f"""
        SELECT 
            activity_year,
            state_code,
            county_code,
            lei,
            action_taken,
            loan_purpose,
            occupancy_type
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        LIMIT 5
        """
        
        results1 = execute_query(client, query1)
        for i, row in enumerate(results1, 1):
            print(f"  Row {i}: year={row.get('activity_year')}, state={row.get('state_code')}, county={row.get('county_code')}, action={row.get('action_taken')}")
        
        # Check available years
        print("\n2. Available years:")
        query2 = f"""
        SELECT 
            activity_year,
            COUNT(*) as record_count
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        GROUP BY activity_year
        ORDER BY activity_year DESC
        LIMIT 10
        """
        
        results2 = execute_query(client, query2)
        for row in results2:
            print(f"  Year {row.get('activity_year')}: {row.get('record_count'):,} records")
        
        # Check state codes
        print("\n3. Sample state codes:")
        query3 = f"""
        SELECT 
            state_code,
            COUNT(*) as record_count
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        WHERE activity_year = '2023'
        GROUP BY state_code
        ORDER BY record_count DESC
        LIMIT 10
        """
        
        results3 = execute_query(client, query3)
        for row in results3:
            print(f"  State {row.get('state_code')}: {row.get('record_count'):,} records")
        
        # Check action_taken values
        print("\n4. Action taken values (2023):")
        query4 = f"""
        SELECT 
            action_taken,
            COUNT(*) as record_count
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        WHERE activity_year = '2023'
        GROUP BY action_taken
        ORDER BY record_count DESC
        LIMIT 10
        """
        
        results4 = execute_query(client, query4)
        for row in results4:
            print(f"  Action {row.get('action_taken')}: {row.get('record_count'):,} records")
        
        # Check if we can find Maryland data
        print("\n5. Looking for Maryland (state code 24):")
        query5 = f"""
        SELECT 
            activity_year,
            state_code,
            county_code,
            COUNT(*) as record_count
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        WHERE state_code = '24'
        GROUP BY activity_year, state_code, county_code
        ORDER BY activity_year DESC, record_count DESC
        LIMIT 10
        """
        
        results5 = execute_query(client, query5)
        if results5:
            print(f"  Found {len(results5)} county records for Maryland:")
            for row in results5:
                print(f"    Year {row.get('activity_year')}, County {row.get('county_code')}: {row.get('record_count'):,} records")
        else:
            print("  No Maryland data found with state_code = '24'")
            print("  Trying to find any state code that might be Maryland...")
            
            # Try to find by county name pattern
            query6 = f"""
            SELECT DISTINCT
                state_code,
                county_code
            FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
            WHERE activity_year = '2023'
            LIMIT 20
            """
            results6 = execute_query(client, query6)
            print(f"  Sample state/county codes from 2023:")
            for row in results6[:10]:
                print(f"    State: {row.get('state_code')}, County: {row.get('county_code')}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_data_structure()

