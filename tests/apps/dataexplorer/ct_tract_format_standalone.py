#!/usr/bin/env python3
"""
Test Connecticut tract format in HMDA data to understand how to extract county codes.
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
print("TESTING CONNECTICUT TRACT FORMAT IN HMDA DATA")
print("=" * 80)
print()

# Test 1: Check tract format for Connecticut 2024 data
query1 = f"""
SELECT 
    h.activity_year as year,
    CAST(h.county_code AS STRING) as county_code,
    CAST(h.census_tract AS STRING) as census_tract,
    LENGTH(CAST(h.census_tract AS STRING)) as tract_length,
    SUBSTR(LPAD(CAST(h.census_tract AS STRING), 11, '0'), 1, 5) as extracted_county_11,
    SUBSTR(LPAD(CAST(h.census_tract AS STRING), 6, '0'), 1, 1) as first_digit_6,
    COUNT(*) as loan_count
FROM `{PROJECT_ID}.hmda.hmda` h
WHERE h.activity_year = '2024'
  AND CAST(h.county_code AS STRING) LIKE '091%'
  AND h.census_tract IS NOT NULL
  AND CAST(h.action_taken AS FLOAT64) = 1
GROUP BY year, county_code, census_tract, tract_length, extracted_county_11, first_digit_6
ORDER BY loan_count DESC
LIMIT 20
"""

print("TEST 1: Sample Connecticut 2024 tract formats")
print("-" * 80)
results1 = execute_query(client, query1)
if results1:
    print(f"Found {len(results1)} sample records")
    print("\nFormat analysis:")
    for row in results1:
        year = row.get('year')
        county_code = row.get('county_code', 'N/A')
        tract = row.get('census_tract', 'N/A')
        length = row.get('tract_length', 0)
        extracted_11 = row.get('extracted_county_11', 'N/A')
        first_digit = row.get('first_digit_6', 'N/A')
        count = int(row.get('loan_count', 0))
        print(f"  County: {county_code}, Tract: {tract} (len={length}), Extracted (11-digit): {extracted_11}, First digit (6-digit): {first_digit}, Loans: {count}")
else:
    print("No results found")
print()

# Test 2: Check if we can join to shared.census to get county from tract
query2 = f"""
SELECT 
    h.activity_year as year,
    CAST(h.county_code AS STRING) as planning_region_code,
    CAST(h.census_tract AS STRING) as census_tract,
    SUBSTR(LPAD(CAST(c.geoid AS STRING), 11, '0'), 1, 5) as actual_county_from_tract,
    COUNT(*) as loan_count
FROM `{PROJECT_ID}.hmda.hmda` h
LEFT JOIN `{PROJECT_ID}.shared.census` c
    ON LPAD(CAST(h.census_tract AS STRING), 11, '0') = LPAD(CAST(c.geoid AS STRING), 11, '0')
WHERE h.activity_year = '2024'
  AND CAST(h.county_code AS STRING) LIKE '091%'
  AND h.census_tract IS NOT NULL
  AND CAST(h.action_taken AS FLOAT64) = 1
GROUP BY year, planning_region_code, census_tract, actual_county_from_tract
HAVING actual_county_from_tract IS NOT NULL
ORDER BY loan_count DESC
LIMIT 20
"""

print("TEST 2: County extraction from tract via shared.census join")
print("-" * 80)
results2 = execute_query(client, query2)
if results2:
    print(f"Found {len(results2)} records with tract-to-county mapping")
    print("\nMapping analysis:")
    for row in results2:
        year = row.get('year')
        planning_region = row.get('planning_region_code', 'N/A')
        tract = row.get('census_tract', 'N/A')
        actual_county = row.get('actual_county_from_tract', 'N/A')
        count = int(row.get('loan_count', 0))
        print(f"  Planning Region: {planning_region}, Tract: {tract}, Actual County: {actual_county}, Loans: {count}")
else:
    print("No results found - tract join may not work")
print()

# Test 3: Check tract format distribution
query3 = f"""
SELECT 
    LENGTH(CAST(h.census_tract AS STRING)) as tract_length,
    COUNT(DISTINCT CAST(h.census_tract AS STRING)) as distinct_tracts,
    COUNT(*) as total_loans
FROM `{PROJECT_ID}.hmda.hmda` h
WHERE h.activity_year = '2024'
  AND CAST(h.county_code AS STRING) LIKE '091%'
  AND h.census_tract IS NOT NULL
  AND CAST(h.action_taken AS FLOAT64) = 1
GROUP BY tract_length
ORDER BY tract_length
"""

print("TEST 3: Tract length distribution")
print("-" * 80)
results3 = execute_query(client, query3)
if results3:
    print("Tract length distribution:")
    for row in results3:
        length = row.get('tract_length', 0)
        distinct = int(row.get('distinct_tracts', 0))
        total = int(row.get('total_loans', 0))
        print(f"  Length {length}: {distinct:,} distinct tracts, {total:,} total loans")
else:
    print("No results found")
print()

print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)

