#!/usr/bin/env python3
"""
Verify that our query matches Tableau's totals for Manufacturers and Traders Trust.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query, escape_sql_string
from justdata.shared.utils.unified_env import get_unified_config

# Expected Tableau totals
expected_totals = {
    2022: 25130,
    2023: 16835,
    2024: 19791
}

# Lender info
subject_lei = "WWB2V0FCW3A0EE3ZJN75"  # Manufacturers and Traders Trust
years = [2022, 2023, 2024]

# Filters matching Tableau query
# Tableau filters: action_taken=1, total_units IN (1,2,3,4), construction_method=1, occupancy_type=1
# Note: Tableau doesn't filter by loan_type in the WHERE clause, but we should check both

print("=" * 80)
print("VERIFYING QUERY TOTALS AGAINST TABLEAU")
print("=" * 80)
print(f"Lender LEI: {subject_lei}")
print(f"Years: {years}")
print()

config = get_unified_config(load_env=False, verbose=False)
PROJECT_ID = config.get('GCP_PROJECT_ID')
client = get_bigquery_client(PROJECT_ID)

# Test 1: Simple COUNT query (matching Tableau's approach)
print("TEST 1: Simple COUNT query (matching Tableau structure)")
print("-" * 80)

years_str = "', '".join(map(str, years))

# Query matching Tableau's structure - using INNER JOIN with cbsa_to_county
simple_query = f"""
SELECT 
    h.activity_year as year,
    COUNT(*) as total_loans
FROM `{PROJECT_ID}.hmda.hmda` h
INNER JOIN `{PROJECT_ID}.geo.cbsa_to_county` c
    ON CAST(h.county_code AS STRING) = CAST(c.geoid5 AS STRING)
INNER JOIN `{PROJECT_ID}.hmda.lenders18` l
    ON h.lei = l.lei
WHERE h.activity_year IN ('{years_str}')
  AND CAST(CAST(h.action_taken AS FLOAT64) AS INT64) = 1
  AND h.total_units IN ('1', '2', '3', '4')
  AND h.construction_method = '1'
  AND h.occupancy_type = '1'
  AND h.lei = '{escape_sql_string(subject_lei)}'
  AND (h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')
GROUP BY h.activity_year
ORDER BY h.activity_year
"""

print("Executing simple COUNT query...")
results = execute_query(client, simple_query)

if results:
    print("\nRESULTS:")
    all_match = True
    for row in results:
        year = int(row.get('year', 0))
        actual = int(row.get('total_loans', 0))
        expected = expected_totals.get(year, 0)
        match = "OK" if actual == expected else "MISMATCH"
        diff = actual - expected
        print(f"  Year {year}: {actual:,} (Expected: {expected:,}, Diff: {diff:+,}) {match}")
        if actual != expected:
            all_match = False
    
    if all_match:
        print("\n[SUCCESS] ALL TOTALS MATCH TABLEAU!")
    else:
        print("\n[WARNING] SOME TOTALS DO NOT MATCH TABLEAU")
else:
    print("ERROR: No results returned")

# Test 2: Check with loan_type filter (our default includes loan_type)
print("\n" + "=" * 80)
print("TEST 2: Query with loan_type filter (our default)")
print("-" * 80)

query_with_loan_type = f"""
SELECT 
    h.activity_year as year,
    COUNT(*) as total_loans
FROM `{PROJECT_ID}.hmda.hmda` h
INNER JOIN `{PROJECT_ID}.geo.cbsa_to_county` c
    ON CAST(h.county_code AS STRING) = CAST(c.geoid5 AS STRING)
INNER JOIN `{PROJECT_ID}.hmda.lenders18` l
    ON h.lei = l.lei
WHERE h.activity_year IN ('{years_str}')
  AND CAST(CAST(h.action_taken AS FLOAT64) AS INT64) = 1
  AND h.total_units IN ('1', '2', '3', '4')
  AND h.construction_method = '1'
  AND h.occupancy_type = '1'
  AND h.loan_type IN ('1', '2', '3', '4')
  AND h.lei = '{escape_sql_string(subject_lei)}'
  AND (h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')
GROUP BY h.activity_year
ORDER BY h.activity_year
"""

print("Executing query with loan_type filter...")
results2 = execute_query(client, query_with_loan_type)

if results2:
    print("\nRESULTS (with loan_type filter):")
    for row in results2:
        year = int(row.get('year', 0))
        actual = int(row.get('total_loans', 0))
        expected = expected_totals.get(year, 0)
        match = "OK" if actual == expected else "MISMATCH"
        diff = actual - expected
        print(f"  Year {year}: {actual:,} (Expected: {expected:,}, Diff: {diff:+,}) {match}")

# Test 3: Check breakdown by loan purpose
print("\n" + "=" * 80)
print("TEST 3: Breakdown by loan purpose")
print("-" * 80)

purpose_query = f"""
SELECT 
    h.activity_year as year,
    CASE 
        WHEN h.loan_purpose = '1' THEN 'Home Purchase'
        WHEN h.loan_purpose IN ('31', '32') THEN 'Refinance and Cash-Out Refi'
        WHEN h.loan_purpose IN ('2', '4') THEN 'Home Improvement and Home Equity'
        ELSE 'Other'
    END as loan_purpose_group,
    COUNT(*) as total_loans
FROM `{PROJECT_ID}.hmda.hmda` h
INNER JOIN `{PROJECT_ID}.geo.cbsa_to_county` c
    ON CAST(h.county_code AS STRING) = CAST(c.geoid5 AS STRING)
INNER JOIN `{PROJECT_ID}.hmda.lenders18` l
    ON h.lei = l.lei
WHERE h.activity_year IN ('{years_str}')
  AND CAST(CAST(h.action_taken AS FLOAT64) AS INT64) = 1
  AND h.total_units IN ('1', '2', '3', '4')
  AND h.construction_method = '1'
  AND h.occupancy_type = '1'
  AND h.lei = '{escape_sql_string(subject_lei)}'
  AND (h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')
GROUP BY h.activity_year, loan_purpose_group
ORDER BY h.activity_year, loan_purpose_group
"""

print("Executing loan purpose breakdown query...")
results3 = execute_query(client, purpose_query)

if results3:
    print("\nRESULTS (by loan purpose):")
    year_totals = {}
    for row in results3:
        year = int(row.get('year', 0))
        purpose = row.get('loan_purpose_group', 'Unknown')
        loans = int(row.get('total_loans', 0))
        year_totals[year] = year_totals.get(year, 0) + loans
        print(f"  {year} - {purpose}: {loans:,}")
    
    print("\nTOTALS BY YEAR:")
    for year in sorted(year_totals.keys()):
        total = year_totals[year]
        expected = expected_totals.get(year, 0)
        match = "OK" if total == expected else "MISMATCH"
        print(f"  {year}: {total:,} (Expected: {expected:,}) {match}")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)

