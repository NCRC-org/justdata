#!/usr/bin/env python3
"""Quick check of Brevard County, Florida."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient

bq_client = BigQueryClient()
disclosure_table = f"{bq_client.project_id}.sb.disclosure"

print("Checking Brevard County, Florida...")
print()

# Simplified query - just get the summary directly
sql = f"""
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
brevard_banks AS (
  SELECT 
    d.respondent_id,
    SUM(COALESCE(d.num_under_100k, 0) + 
        COALESCE(d.num_100k_250k, 0) + 
        COALESCE(d.num_250k_1m, 0)) AS loans_in_brevard
  FROM `{disclosure_table}` d
  WHERE CAST(d.year AS INT64) = 2024
    AND LPAD(CAST(d.geoid5 AS STRING), 5, '0') = '12009'  -- Brevard County, FL FIPS
  GROUP BY d.respondent_id
)
SELECT 
  COUNT(DISTINCT bb.respondent_id) AS total_banks,
  COUNT(DISTINCT CASE WHEN lt.total_loans_2024 < 1000 THEN bb.respondent_id END) AS exempt_banks,
  COUNT(DISTINCT CASE WHEN lt.total_loans_2024 >= 1000 THEN bb.respondent_id END) AS non_exempt_banks,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN lt.total_loans_2024 < 1000 THEN bb.respondent_id END) / 
        NULLIF(COUNT(DISTINCT bb.respondent_id), 0), 2) AS pct_exempt_banks,
  SUM(bb.loans_in_brevard) AS total_loans,
  SUM(CASE WHEN lt.total_loans_2024 < 1000 THEN bb.loans_in_brevard ELSE 0 END) AS loans_from_exempt,
  SUM(CASE WHEN lt.total_loans_2024 >= 1000 THEN bb.loans_in_brevard ELSE 0 END) AS loans_from_non_exempt,
  ROUND(100.0 * SUM(CASE WHEN lt.total_loans_2024 < 1000 THEN bb.loans_in_brevard ELSE 0 END) / 
        NULLIF(SUM(bb.loans_in_brevard), 0), 2) AS pct_loans_from_exempt
FROM brevard_banks bb
INNER JOIN lender_totals lt
  ON bb.respondent_id = lt.respondent_id
"""

try:
    result = bq_client.query(sql)
    df = result.to_dataframe()
    
    if len(df) > 0:
        row = df.iloc[0]
        print("=" * 80)
        print("BREVARD COUNTY, FLORIDA (FIPS: 12009)")
        print("=" * 80)
        print()
        print(f"Total Banks Operating: {row['total_banks']:,}")
        print(f"  - Exempt Banks (<1K loans): {row['exempt_banks']:,}")
        print(f"  - Non-Exempt Banks (>=1K loans): {row['non_exempt_banks']:,}")
        print(f"  - % Banks Exempt: {row['pct_exempt_banks']:.1f}%")
        print()
        print(f"Total Loans in County: {row['total_loans']:,}")
        print(f"  - Loans from Exempt Banks: {row['loans_from_exempt']:,}")
        print(f"  - Loans from Non-Exempt Banks: {row['loans_from_non_exempt']:,}")
        print(f"  - % Loans from Exempt Banks: {row['pct_loans_from_exempt']:.1f}%")
        print()
        print("=" * 80)
        print("ANALYSIS")
        print("=" * 80)
        print()
        if row['pct_exempt_banks'] > 70:
            print(f"⚠ High exemption % ({row['pct_exempt_banks']:.1f}%) for banks")
            if row['pct_loans_from_exempt'] < 30:
                print("✓ But most loans come from non-exempt banks - this is CORRECT")
                print("  Many small banks operate there, but large banks make most loans")
            else:
                print(f"⚠ AND most loans ({row['pct_loans_from_exempt']:.1f}%) from exempt banks")
                print("  This seems unusual - needs verification")
        else:
            print("Results look reasonable")
    else:
        print("No data found for Brevard County")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

