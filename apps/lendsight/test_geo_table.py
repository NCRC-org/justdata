#!/usr/bin/env python3
"""
Test script to check the geo.cbsa_to_county table structure.
"""

import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared.utils.bigquery_client import get_bigquery_client, execute_query
from apps.lendsight.config import PROJECT_ID

def test_geo_table():
    """Check the geo.cbsa_to_county table structure."""
    print("=" * 80)
    print("TESTING GEO.CBSA_TO_COUNTY TABLE")
    print("=" * 80)
    
    try:
        client = get_bigquery_client(PROJECT_ID)
        
        # Check sample data
        print("\n1. Sample geo.cbsa_to_county data:")
        query1 = f"""
        SELECT 
            geoid5,
            county_state,
            CAST(geoid5 AS STRING) as geoid5_string
        FROM `{PROJECT_ID}.geo.cbsa_to_county`
        WHERE county_state LIKE '%Montgomery%'
        LIMIT 10
        """
        
        results1 = execute_query(client, query1)
        print(f"  Found {len(results1)} Montgomery counties:")
        for row in results1:
            print(f"    GEOID5: {row.get('geoid5')} (type: {type(row.get('geoid5')).__name__}), County: {row.get('county_state')}")
        
        # Check if county_code from HMDA matches geoid5
        print("\n2. Testing join between HMDA county_code and geo.geoid5:")
        query2 = f"""
        SELECT 
            h.county_code as hmda_county_code,
            CAST(h.county_code AS STRING) as hmda_county_code_str,
            c.geoid5 as geo_geoid5,
            CAST(c.geoid5 AS STRING) as geo_geoid5_str,
            c.county_state,
            COUNT(*) as match_count
        FROM `{PROJECT_ID}.hmda.hmda` h
        LEFT JOIN `{PROJECT_ID}.geo.cbsa_to_county` c
            ON CAST(h.county_code AS STRING) = CAST(c.geoid5 AS STRING)
        WHERE h.activity_year = '2023'
        AND h.county_code IS NOT NULL
        GROUP BY h.county_code, c.geoid5, c.county_state
        HAVING match_count > 0
        ORDER BY match_count DESC
        LIMIT 10
        """
        
        results2 = execute_query(client, query2)
        print(f"  Found {len(results2)} matching records:")
        for row in results2:
            print(f"    HMDA county: {row.get('hmda_county_code')}, GEO geoid5: {row.get('geo_geoid5')}, County: {row.get('county_state')}, Matches: {row.get('match_count'):,}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_geo_table()

