#!/usr/bin/env python3
"""Check exemption logic - verify calculations are correct."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient

bq_client = BigQueryClient()
disclosure_table = f"{bq_client.project_id}.sb.disclosure"

print("=" * 80)
print("CHECKING EXEMPTION LOGIC")
print("=" * 80)
print()

# First, let's see the overall distribution
print("1. Overall bank exemption status (2024):")
sql1 = f"""
SELECT 
  CASE 
    WHEN total_loans < 1000 THEN 'Exempt (<1K loans)'
    ELSE 'Non-Exempt (>=1K loans)'
  END AS exemption_status,
  COUNT(*) AS num_banks,
  SUM(total_loans) AS total_loans
FROM (
  SELECT 
    respondent_id,
    SUM(COALESCE(num_under_100k, 0) + 
        COALESCE(num_100k_250k, 0) + 
        COALESCE(num_250k_1m, 0)) AS total_loans
  FROM `{disclosure_table}`
  WHERE CAST(year AS INT64) = 2024
  GROUP BY respondent_id
)
GROUP BY exemption_status
ORDER BY exemption_status
"""

result1 = bq_client.query(sql1)
df1 = result1.to_dataframe()
print(df1.to_string())
print()

# Check a specific high-activity county
print("2. Sample high-activity county breakdown:")
sql2 = f"""
WITH lender_totals AS (
  SELECT 
    respondent_id,
    SUM(COALESCE(num_under_100k, 0) + 
        COALESCE(num_100k_250k, 0) + 
        COALESCE(num_250k_1m, 0)) AS total_loans_2024
  FROM `{disclosure_table}`
  WHERE CAST(year AS INT64) = 2024
  GROUP BY respondent_id
),
county_loans AS (
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
  cl.county_name,
  cl.state_name,
  COUNT(DISTINCT cl.respondent_id) AS total_banks,
  COUNT(DISTINCT CASE WHEN lt.total_loans_2024 < 1000 THEN cl.respondent_id END) AS exempt_banks,
  COUNT(DISTINCT CASE WHEN lt.total_loans_2024 >= 1000 THEN cl.respondent_id END) AS non_exempt_banks,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN lt.total_loans_2024 < 1000 THEN cl.respondent_id END) / 
        NULLIF(COUNT(DISTINCT cl.respondent_id), 0), 2) AS pct_exempt,
  SUM(cl.loans_in_county) AS total_loans,
  SUM(CASE WHEN lt.total_loans_2024 < 1000 THEN cl.loans_in_county ELSE 0 END) AS loans_from_exempt,
  SUM(CASE WHEN lt.total_loans_2024 >= 1000 THEN cl.loans_in_county ELSE 0 END) AS loans_from_non_exempt,
  ROUND(100.0 * SUM(CASE WHEN lt.total_loans_2024 < 1000 THEN cl.loans_in_county ELSE 0 END) / 
        NULLIF(SUM(cl.loans_in_county), 0), 2) AS pct_loans_from_exempt
FROM county_loans cl
INNER JOIN lender_totals lt
  ON cl.respondent_id = lt.respondent_id
GROUP BY cl.county_name, cl.state_name
HAVING SUM(cl.loans_in_county) > 100000  -- High activity counties
ORDER BY total_loans DESC
LIMIT 5
"""

result2 = bq_client.query(sql2)
df2 = result2.to_dataframe()
print(df2.to_string())
print()

print("=" * 80)
print("ANALYSIS")
print("=" * 80)
print()
print("Key question: Are high-activity counties showing high exemption %?")
print()
print("If '% Exempt' (banks) is high but '% Loans Exempt' is LOW, that's actually CORRECT:")
print("  - Many small banks (exempt) operate there")
print("  - But most loans come from large banks (non-exempt)")
print()
print("This would explain why high-activity counties show high exemption % for BANKS")
print("but most LOANS still come from non-exempt banks.")
print()

