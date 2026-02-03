#!/usr/bin/env python3
"""
Check if Connecticut HMDA data is being excluded due to cbsa_to_county JOIN issues.
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
print("CHECKING CONNECTICUT HMDA DATA AND CBSA_TO_COUNTY MAPPING")
print("=" * 80)
print()

# Test 1: Check if Connecticut counties exist in cbsa_to_county table
print("TEST 1: Checking cbsa_to_county table for Connecticut")
print("-" * 80)

query1 = f"""
SELECT DISTINCT
    CAST(geoid5 AS STRING) as geoid5,
    county,
    state,
    county_state,
    cbsa_code,
    CBSA as cbsa_name
FROM `{PROJECT_ID}.shared.cbsa_to_county`
WHERE state = 'Connecticut' OR state = 'CT' OR CAST(geoid5 AS STRING) LIKE '09%'
ORDER BY geoid5
"""

results1 = execute_query(client, query1)
if results1:
    print(f"Found {len(results1)} Connecticut entries in cbsa_to_county:")
    for row in results1:
        print(f"  GEOID5: {row.get('geoid5')}, County: {row.get('county')}, State: {row.get('state')}, CBSA: {row.get('cbsa_name', 'N/A')}")
else:
    print("  WARNING: No Connecticut entries found in cbsa_to_county table!")
print()

# Test 2: Check HMDA data for Connecticut (without JOIN)
print("TEST 2: Checking HMDA data for Connecticut (direct query, no JOIN)")
print("-" * 80)

query2 = f"""
SELECT 
    h.activity_year as year,
    CAST(h.county_code AS STRING) as county_code,
    COUNT(*) as total_loans
FROM `{PROJECT_ID}.hmda.hmda` h
WHERE h.activity_year IN ('2022', '2023', '2024')
  AND CAST(h.action_taken AS FLOAT64) = 1
  AND h.total_units IN ('1', '2', '3', '4')
  AND h.construction_method = '1'
  AND h.occupancy_type = '1'
  AND CAST(h.county_code AS STRING) LIKE '09%'
GROUP BY h.activity_year, county_code
ORDER BY h.activity_year, county_code
"""

results2 = execute_query(client, query2)
if results2:
    print(f"Found {len(results2)} Connecticut county/year combinations in HMDA:")
    year_totals = {}
    for row in results2:
        year = int(row.get('year', 0))
        county = row.get('county_code', 'Unknown')
        loans = int(row.get('total_loans', 0))
        year_totals[year] = year_totals.get(year, 0) + loans
        print(f"  Year {year}, County {county}: {loans:,} loans")
    
    print("\n  Totals by year:")
    for year in sorted(year_totals.keys()):
        print(f"    {year}: {year_totals[year]:,} loans")
else:
    print("  WARNING: No Connecticut HMDA data found!")
print()

# Test 3: Check HMDA data WITH JOIN to cbsa_to_county
print("TEST 3: Checking HMDA data WITH JOIN to cbsa_to_county")
print("-" * 80)

query3 = f"""
SELECT 
    h.activity_year as year,
    CAST(h.county_code AS STRING) as county_code,
    c.county_state,
    COUNT(*) as total_loans
FROM `{PROJECT_ID}.hmda.hmda` h
LEFT JOIN `{PROJECT_ID}.shared.cbsa_to_county` c
    ON CAST(h.county_code AS STRING) = CAST(c.geoid5 AS STRING)
WHERE h.activity_year IN ('2022', '2023', '2024')
  AND CAST(h.action_taken AS FLOAT64) = 1
  AND h.total_units IN ('1', '2', '3', '4')
  AND h.construction_method = '1'
  AND h.occupancy_type = '1'
  AND CAST(h.county_code AS STRING) LIKE '09%'
GROUP BY h.activity_year, county_code, c.county_state
ORDER BY h.activity_year, county_code
"""

results3 = execute_query(client, query3)
if results3:
    print(f"Found {len(results3)} Connecticut county/year combinations (with JOIN):")
    year_totals_with_join = {}
    null_county_state_count = 0
    for row in results3:
        year = int(row.get('year', 0))
        county = row.get('county_code', 'Unknown')
        county_state = row.get('county_state')
        loans = int(row.get('total_loans', 0))
        year_totals_with_join[year] = year_totals_with_join.get(year, 0) + loans
        if county_state is None:
            null_county_state_count += loans
        print(f"  Year {year}, County {county}, county_state: {county_state or 'NULL'}: {loans:,} loans")
    
    print("\n  Totals by year (with JOIN):")
    for year in sorted(year_totals_with_join.keys()):
        print(f"    {year}: {year_totals_with_join[year]:,} loans")
    
    if null_county_state_count > 0:
        print(f"\n  WARNING: {null_county_state_count:,} loans have NULL county_state (JOIN failed)")
        print("  These loans would be EXCLUDED if we filter by county_state!")
else:
    print("  WARNING: No Connecticut HMDA data found with JOIN!")
print()

# Test 4: Compare totals
print("TEST 4: Comparing totals (with vs without JOIN)")
print("-" * 80)
if results2 and results3:
    for year in sorted(set(list(year_totals.keys()) + list(year_totals_with_join.keys()))):
        without_join = year_totals.get(year, 0)
        with_join = year_totals_with_join.get(year, 0)
        diff = without_join - with_join
        if diff > 0:
            print(f"  Year {year}: {without_join:,} (without JOIN) vs {with_join:,} (with JOIN) - Missing {diff:,} loans")
        else:
            print(f"  Year {year}: {without_join:,} (without JOIN) vs {with_join:,} (with JOIN) - Match")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)

