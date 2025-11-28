#!/usr/bin/env python3
"""
Test script to verify the HMDA mortgage report SQL query works correctly.
"""

import os
import sys

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared.utils.bigquery_client import get_bigquery_client, execute_query
from apps.lendsight.config import PROJECT_ID, DATASET_ID, TABLE_ID
from apps.lendsight.data_utils import execute_mortgage_query

def test_sql_query():
    """Test the mortgage report SQL query with a sample county and year."""
    try:
        print("=" * 80)
        print("TESTING HMDA MORTGAGE REPORT SQL QUERY")
        print("=" * 80)
        
        # Test with a common county - let's use a small one first
        # Try "Montgomery County, Maryland" or similar
        test_county = "Montgomery County, Maryland"
        test_year = 2023
        
        print(f"\nTest Parameters:")
        print(f"  County: {test_county}")
        print(f"  Year: {test_year}")
        print(f"  Project: {PROJECT_ID}")
        print(f"  Dataset: {DATASET_ID}")
        print(f"  Table: {TABLE_ID}")
        
        print("\n" + "=" * 80)
        print("Executing query...")
        print("=" * 80)
        
        # Read the SQL template
        sql_template_path = os.path.join(
            os.path.dirname(__file__),
            'sql_templates',
            'mortgage_report.sql'
        )
        
        with open(sql_template_path, 'r', encoding='utf-8') as f:
            sql_template = f.read()
        
        # Execute the query
        results = execute_mortgage_query(
            sql_template=sql_template,
            county=test_county,
            year=test_year
        )
        
        print(f"\n[OK] Query executed successfully!")
        print(f"  Returned {len(results)} rows")
        
        if results:
            print("\n" + "=" * 80)
            print("SAMPLE RESULTS (first 5 rows):")
            print("=" * 80)
            
            # Show first few results
            for i, row in enumerate(results[:5], 1):
                print(f"\nRow {i}:")
                for key, value in row.items():
                    # Truncate long values
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:47] + "..."
                    print(f"  {key:30} = {value}")
            
            # Show summary statistics
            print("\n" + "=" * 80)
            print("SUMMARY STATISTICS:")
            print("=" * 80)
            
            total_originations = sum(row.get('total_originations', 0) for row in results)
            unique_lenders = len(set(row.get('lei', '') for row in results if row.get('lei')))
            unique_counties = len(set(row.get('county_state', '') for row in results if row.get('county_state')))
            lenders_with_names = sum(1 for row in results if row.get('lender_name'))
            
            print(f"  Total originations: {total_originations:,}")
            print(f"  Unique lenders (LEI): {unique_lenders}")
            print(f"  Unique counties: {unique_counties}")
            print(f"  Lenders with names: {lenders_with_names} / {unique_lenders}")
            
            if lenders_with_names < unique_lenders:
                print(f"\n  [WARNING] {unique_lenders - lenders_with_names} lenders missing names")
                print("     This might indicate the lenders18 table join needs adjustment")
            
            # Check for geoid5
            geoid5_count = sum(1 for row in results if row.get('geoid5'))
            print(f"  Rows with geoid5: {geoid5_count} / {len(results)}")
            
            if geoid5_count < len(results):
                print(f"  [WARNING] {len(results) - geoid5_count} rows missing geoid5")
        
        else:
            print("\n[WARNING] No results returned. This could mean:")
            print("   - The county name doesn't match exactly")
            print("   - No data for this county/year combination")
            print("   - There's an issue with the query")
        
        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        
        return results
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    test_sql_query()

