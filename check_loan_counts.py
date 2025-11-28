#!/usr/bin/env python3
"""Check loan counts to identify the issue."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient

bq_client = BigQueryClient()

print("=" * 80)
print("CHECKING LOAN COUNTS")
print("=" * 80)
print()

# Check total from 1071_1k_lenders table (what we're currently using)
print("1. From 1071_1k_lenders table (current method):")
sql1 = f"""
SELECT 
  CAST(year AS INT64) AS year,
  SUM(COALESCE(num_under_100k, 0) + 
      COALESCE(num_100k_250k, 0) + 
      COALESCE(num_250k_1m, 0)) AS total_loans,
  COUNT(*) AS row_count
FROM `{bq_client.project_id}.misc.1071_1k_lenders`
WHERE CAST(year AS INT64) = 2024
GROUP BY CAST(year AS INT64)
"""
result1 = bq_client.query(sql1)
df1 = result1.to_dataframe()
print(df1.to_string())
print()

# Check total from original disclosure table (direct aggregation)
print("2. From original disclosure table (direct, grouped by lender-year):")
sql2 = f"""
SELECT 
  CAST(year AS INT64) AS year,
  SUM(COALESCE(num_under_100k, 0) + 
      COALESCE(num_100k_250k, 0) + 
      COALESCE(num_250k_1m, 0)) AS total_loans,
  COUNT(DISTINCT respondent_id) AS unique_lenders,
  COUNT(*) AS row_count
FROM `{bq_client.project_id}.sb.disclosure`
WHERE CAST(year AS INT64) = 2024
GROUP BY CAST(year AS INT64)
"""
result2 = bq_client.query(sql2)
df2 = result2.to_dataframe()
print(df2.to_string())
print()

# Check if there's duplication in 1071_1k_lenders
print("3. Checking for duplicates in 1071_1k_lenders (same lender-year-county):")
sql3 = f"""
SELECT 
  CAST(year AS INT64) AS year,
  respondent_id,
  geoid5,
  COUNT(*) AS duplicate_count
FROM `{bq_client.project_id}.misc.1071_1k_lenders`
WHERE CAST(year AS INT64) = 2024
GROUP BY CAST(year AS INT64), respondent_id, geoid5
HAVING COUNT(*) > 1
LIMIT 10
"""
result3 = bq_client.query(sql3)
df3 = result3.to_dataframe()
if len(df3) > 0:
    print("Found duplicates:")
    print(df3.to_string())
else:
    print("No duplicates found (good)")
print()

# Check row counts
print("4. Row count comparison:")
sql4 = f"""
SELECT 
  'disclosure table' AS source,
  CAST(year AS INT64) AS year,
  COUNT(*) AS row_count
FROM `{bq_client.project_id}.sb.disclosure`
WHERE CAST(year AS INT64) = 2024
GROUP BY CAST(year AS INT64)
UNION ALL
SELECT 
  '1071_1k_lenders table' AS source,
  CAST(year AS INT64) AS year,
  COUNT(*) AS row_count
FROM `{bq_client.project_id}.misc.1071_1k_lenders`
WHERE CAST(year AS INT64) = 2024
GROUP BY CAST(year AS INT64)
"""
result4 = bq_client.query(sql4)
df4 = result4.to_dataframe()
print(df4.to_string())
print()

print("=" * 80)

