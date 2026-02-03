#!/usr/bin/env python3
"""
Test if we can get actual county codes from shared.census table for Connecticut tracts.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
from justdata.shared.utils.unified_env import get_unified_config

config = get_unified_config(load_env=False, verbose=False)
PROJECT_ID = config.get('GCP_PROJECT_ID')
client = get_bigquery_client(PROJECT_ID)

print("=" * 80)
print("TESTING TRACT TO COUNTY MAPPING VIA GEO.CENSUS")
print("=" * 80)
print()

# Test: Join HMDA tracts to shared.census to see what county codes we get
query = f"""
SELECT 
    h.activity_year as year,
    CAST(h.county_code AS STRING) as planning_region_code,
    CAST(h.census_tract AS STRING) as census_tract,
    SUBSTR(LPAD(CAST(h.census_tract AS STRING), 11, '0'), 1, 5) as tract_planning_region,
    SUBSTR(LPAD(CAST(c.geoid AS STRING), 11, '0'), 1, 5) as geo_census_geoid5,
    c.geoid5 as geo_census_geoid5_column,
    COUNT(*) as loan_count
FROM `{PROJECT_ID}.hmda.hmda` h
LEFT JOIN `{PROJECT_ID}.shared.census` c
    ON LPAD(CAST(h.census_tract AS STRING), 11, '0') = LPAD(CAST(c.geoid AS STRING), 11, '0')
WHERE h.activity_year = '2024'
  AND CAST(h.county_code AS STRING) LIKE '091%'
  AND h.census_tract IS NOT NULL
  AND CAST(h.action_taken AS FLOAT64) = 1
GROUP BY year, planning_region_code, census_tract, tract_planning_region, geo_census_geoid5, geo_census_geoid5_column
HAVING geo_census_geoid5 IS NOT NULL
ORDER BY loan_count DESC
LIMIT 30
"""

print("Testing tract-to-county mapping via shared.census")
print("-" * 80)
results = execute_query(client, query)
if results:
    print(f"Found {len(results)} records")
    print("\nMapping analysis:")
    print("Planning Region | Tract | Tract PR Code | shared.census geoid5 | shared.census geoid5_col | Loans")
    print("-" * 100)
    
    county_mappings = {}
    for row in results:
        pr_code = row.get('planning_region_code', 'N/A')
        tract = row.get('census_tract', 'N/A')
        tract_pr = row.get('tract_planning_region', 'N/A')
        geo_geoid5 = row.get('geo_census_geoid5', 'N/A')
        geo_geoid5_col = row.get('geo_census_geoid5_column', 'N/A')
        count = int(row.get('loan_count', 0))
        
        print(f"{pr_code:15} | {tract:11} | {tract_pr:13} | {str(geo_geoid5):18} | {str(geo_geoid5_col):21} | {count:,}")
        
        # Track mappings
        if pr_code not in county_mappings:
            county_mappings[pr_code] = {}
        if geo_geoid5_col not in county_mappings[pr_code]:
            county_mappings[pr_code][geo_geoid5_col] = 0
        county_mappings[pr_code][geo_geoid5_col] += count
    
    print("\n" + "=" * 100)
    print("Summary: Planning Region → County mappings (from shared.census)")
    print("-" * 100)
    for pr_code in sorted(county_mappings.keys()):
        print(f"\nPlanning Region {pr_code}:")
        for county, loans in sorted(county_mappings[pr_code].items(), key=lambda x: x[1], reverse=True):
            print(f"  → County {county}: {loans:,} loans")
else:
    print("No results found")
print()

print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)

