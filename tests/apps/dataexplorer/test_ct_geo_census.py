#!/usr/bin/env python3
"""
Test if shared.census table has planning region codes for Connecticut tracts.
This will tell us if we can use it to map 2022-2023 legacy county codes to planning regions.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
from justdata.shared.utils.unified_env import get_unified_config

config = get_unified_config(load_env=False, verbose=False)
PROJECT_ID = config.get('GCP_PROJECT_ID')
client = get_bigquery_client(PROJECT_ID)

print("=" * 80)
print("TESTING GEO.CENSUS FOR CONNECTICUT PLANNING REGION CODES")
print("=" * 80)
print()

# Test: Check if shared.census has planning region codes for Connecticut tracts
query = f"""
SELECT 
    SUBSTR(LPAD(CAST(geoid AS STRING), 11, '0'), 1, 5) as geoid5,
    COUNT(DISTINCT geoid) as distinct_tracts,
    COUNT(*) as total_records
FROM `{PROJECT_ID}.shared.census`
WHERE SUBSTR(LPAD(CAST(geoid AS STRING), 11, '0'), 1, 2) = '09'  -- Connecticut
GROUP BY geoid5
ORDER BY geoid5
"""

print("Checking shared.census for Connecticut GEOID5 codes:")
print("-" * 80)
results = execute_query(client, query)
if results:
    print(f"Found {len(results)} distinct GEOID5 codes in shared.census for Connecticut")
    print("\nGEOID5 codes found:")
    print("GEOID5 | Distinct Tracts | Total Records")
    print("-" * 50)
    
    planning_regions = []
    legacy_counties = []
    
    for row in results:
        geoid5 = row.get('geoid5', 'N/A')
        tracts = int(row.get('distinct_tracts', 0))
        records = int(row.get('total_records', 0))
        print(f"{geoid5:6} | {tracts:15,} | {records:13,}")
        
        if geoid5.startswith('091'):
            planning_regions.append(geoid5)
        elif geoid5.startswith('090'):
            legacy_counties.append(geoid5)
    
    print("\n" + "=" * 80)
    print("Summary:")
    print("-" * 80)
    print(f"Planning region codes (091xx): {len(planning_regions)}")
    if planning_regions:
        print(f"  Codes: {', '.join(sorted(planning_regions))}")
    print(f"Legacy county codes (090xx): {len(legacy_counties)}")
    if legacy_counties:
        print(f"  Codes: {', '.join(sorted(legacy_counties))}")
    
    if planning_regions and legacy_counties:
        print("\n✓ shared.census has BOTH planning regions AND legacy counties")
        print("  This means we can map 2022-2023 data using tract lookups!")
    elif planning_regions and not legacy_counties:
        print("\n✓ shared.census has ONLY planning regions")
        print("  We can use tract lookups to map 2022-2023 legacy counties to planning regions")
    elif legacy_counties and not planning_regions:
        print("\n✗ shared.census has ONLY legacy counties")
        print("  We'll need a different mapping approach")
    else:
        print("\n? Unexpected: No Connecticut codes found")
else:
    print("No results found")
print()

print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)

