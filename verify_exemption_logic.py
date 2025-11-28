#!/usr/bin/env python3
"""Verify the exemption calculation logic to check for errors."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient

bq_client = BigQueryClient()
disclosure_table = f"{bq_client.project_id}.sb.disclosure"

print("=" * 80)
print("VERIFYING EXEMPTION CALCULATION LOGIC")
print("=" * 80)
print()

# Check a few specific counties to see what's happening
print("Checking sample counties with high lending activity...")
print()

# Get top counties by total loans
sql = f"""
WITH lender_totals_2024 AS (
  SELECT 
    respondent_id,
    SUM(COALESCE(num_under_100k, 0) + 
        COALESCE(num_100k_250k, 0) + 
        COALESCE(num_250k_1m, 0)) AS total_loans_2024
  FROM `{disclosure_table}`
  WHERE CAST(year AS INT64) = 2024
  GROUP BY respondent_id
),
county_data AS (
  SELECT 
    LPAD(CAST(d.geoid5 AS STRING), 5, '0') AS geoid5,
    g.county AS county_name,
    g.state AS state_name,
    d.respondent_id,
    SUM(COALESCE(d.num_under_100k, 0) + 
        COALESCE(d.num_100k_250k, 0) + 
        COALESCE(d.num_250k_1m, 0)) AS loans_in_county
  FROM `{disclosure_table}` d
  LEFT JOIN `{bq_client.project_id}.geo.cbsa_to_county` g 
    ON LPAD(CAST(d.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
  WHERE CAST(d.year AS INT64) = 2024
    AND d.geoid5 IS NOT NULL
  GROUP BY geoid5, g.county, g.state, d.respondent_id
)
SELECT 
  cd.geoid5,
  cd.county_name,
  cd.state_name,
  COUNT(DISTINCT cd.respondent_id) AS total_banks,
  COUNT(DISTINCT CASE WHEN lt.total_loans_2024 < 1000 THEN cd.respondent_id END) AS exempt_banks,
  COUNT(DISTINCT CASE WHEN lt.total_loans_2024 >= 1000 THEN cd.respondent_id END) AS non_exempt_banks,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN lt.total_loans_2024 < 1000 THEN cd.respondent_id END) / 
        NULLIF(COUNT(DISTINCT cd.respondent_id), 0), 2) AS pct_exempt,
  SUM(cd.loans_in_county) AS total_loans_in_county,
  SUM(CASE WHEN lt.total_loans_2024 < 1000 THEN cd.loans_in_county ELSE 0 END) AS loans_from_exempt,
  SUM(CASE WHEN lt.total_loans_2024 >= 1000 THEN cd.loans_in_county ELSE 0 END) AS loans_from_non_exempt,
  ROUND(100.0 * SUM(CASE WHEN lt.total_loans_2024 < 1000 THEN cd.loans_in_county ELSE 0 END) / 
        NULLIF(SUM(cd.loans_in_county), 0), 2) AS pct_loans_from_exempt
FROM county_data cd
INNER JOIN lender_totals_2024 lt
  ON cd.respondent_id = lt.respondent_id
GROUP BY cd.geoid5, cd.county_name, cd.state_name
HAVING COUNT(DISTINCT cd.respondent_id) > 0
  AND SUM(cd.loans_in_county) > 50000  -- High lending activity counties
ORDER BY total_loans_in_county DESC
LIMIT 10
"""

result = bq_client.query(sql)
df = result.to_dataframe()

print("Top 10 counties by total loans in 2024:")
print()
print(f"{'County':<30} {'State':<15} {'Total':<12} {'Exempt':<12} {'Non-Exempt':<12} {'% Exempt':<12} {'Total Loans':<15} {'% Loans Exempt':<15}")
print("-" * 120)
for _, row in df.iterrows():
    print(f"{row['county_name']:<30} {row['state_name']:<15} "
          f"{row['total_banks']:<12,} {row['exempt_banks']:<12,} {row['non_exempt_banks']:<12,} "
          f"{row['pct_exempt']:<12.1f}% {row['total_loans_in_county']:<15,} {row['pct_loans_from_exempt']:<15.1f}%")
print()

print("=" * 80)
print("ANALYSIS")
print("=" * 80)
print()
print("Key insight: Compare '% Exempt' (banks) vs '% Loans Exempt' (loans)")
print()
print("If '% Exempt' is high but '% Loans Exempt' is low, it means:")
print("  - Many small banks (exempt) operate there")
print("  - But most loans come from large banks (non-exempt)")
print()
print("This would be CORRECT - small banks are exempt, large banks are not.")
print()
print("If both are high, that might indicate an issue with the calculation.")
print()

