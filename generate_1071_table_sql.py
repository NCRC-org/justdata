#!/usr/bin/env python3
"""
Generate SQL to populate the 1071_1k_Lenders table.
Run this SQL in BigQuery console where you have write permissions.
"""

import sys
import os

# Add the apps directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient


def generate_sql():
    """Generate the SQL query to populate the table."""
    bq_client = BigQueryClient()
    project_id = bq_client.project_id
    
    years = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
    year_list = ", ".join(str(y) for y in years)
    year_filter = f"AND CAST(d.year AS INT64) IN ({year_list})"
    
    min_loans = 1000
    min_avg_thousands = 10  # $10,000 in thousands
    
    sql = f"""
-- Populate 1071_1k_Lenders table
-- This query identifies lenders with >= 1000 loans in consecutive years
-- and excludes credit card lenders (average loan amount < $10,000 per year)

CREATE OR REPLACE TABLE `{project_id}.misc.1071_1k_Lenders` AS
WITH 
-- Exclude credit card lenders (average loan amount < $10,000 for that year)
-- Note: amounts in disclosure table are in thousands (000s)
-- Calculate average loan amount PER YEAR per lender
lender_avg_loan_amount_by_year AS (
  SELECT 
    d.respondent_id,
    CAST(d.year AS INT64) AS year,
    -- Calculate average loan amount per lender for THIS YEAR
    -- Amounts are in thousands, so result is also in thousands
    SAFE_DIVIDE(
      SUM(COALESCE(d.amt_under_100k, 0) + 
          COALESCE(d.amt_100k_250k, 0) + 
          COALESCE(d.amt_250k_1m, 0)),
      NULLIF(SUM(COALESCE(d.num_under_100k, 0) + 
                 COALESCE(d.num_100k_250k, 0) + 
                 COALESCE(d.num_250k_1m, 0)), 0)
    ) AS avg_loan_amount_thousands
  FROM `{project_id}.sb.disclosure` d
  WHERE d.year IS NOT NULL
    AND d.respondent_id IS NOT NULL
    {year_filter}
  GROUP BY d.respondent_id, CAST(d.year AS INT64)
  HAVING avg_loan_amount_thousands >= {min_avg_thousands}
),
loan_counts AS (
  SELECT 
    d.respondent_id,
    CAST(d.year AS INT64) AS year,
    -- Sum loan counts across all size categories
    SUM(COALESCE(d.num_under_100k, 0) + 
        COALESCE(d.num_100k_250k, 0) + 
        COALESCE(d.num_250k_1m, 0)) AS loans_in_year
  FROM `{project_id}.sb.disclosure` d
  INNER JOIN lender_avg_loan_amount_by_year lavg
    ON d.respondent_id = lavg.respondent_id
    AND CAST(d.year AS INT64) = lavg.year
  WHERE d.year IS NOT NULL
    AND d.respondent_id IS NOT NULL
    {year_filter}
  GROUP BY d.respondent_id, CAST(d.year AS INT64)
),
qualified AS (
  SELECT 
    curr.respondent_id,
    curr.year
  FROM loan_counts curr
  INNER JOIN loan_counts prev
    ON curr.respondent_id = prev.respondent_id 
    AND curr.year = prev.year + 1
  WHERE curr.loans_in_year >= {min_loans} 
    AND prev.loans_in_year >= {min_loans}
)
SELECT 
  d.*,
  l.sb_lender as lender_name,
  g.county_state,
  g.county as county_name,
  g.state as state_name,
  CASE 
    WHEN q.respondent_id IS NOT NULL THEN 'Qualifies'
    ELSE 'Does Not Qualify'
  END AS qualification_status
FROM `{project_id}.sb.disclosure` d
LEFT JOIN `{project_id}.sb.lenders` l 
  ON d.respondent_id = l.sb_resid
LEFT JOIN `{project_id}.geo.cbsa_to_county` g 
  ON LPAD(CAST(d.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
LEFT JOIN qualified q
  ON d.respondent_id = q.respondent_id 
  AND CAST(d.year AS INT64) = q.year
INNER JOIN lender_avg_loan_amount_by_year lavg
  ON d.respondent_id = lavg.respondent_id
  AND CAST(d.year AS INT64) = lavg.year
WHERE d.year IS NOT NULL
  AND d.respondent_id IS NOT NULL
  {year_filter}
ORDER BY d.respondent_id, d.year, g.county_state
"""
    
    return sql


if __name__ == '__main__':
    print("=" * 80)
    print("SQL QUERY FOR 1071_1k_Lenders TABLE")
    print("=" * 80)
    print()
    print("Copy and paste this SQL into BigQuery console:")
    print()
    print("-" * 80)
    sql = generate_sql()
    print(sql)
    print("-" * 80)
    print()
    print("=" * 80)
    print("INSTRUCTIONS:")
    print("=" * 80)
    print("1. Open BigQuery console: https://console.cloud.google.com/bigquery")
    print("2. Select project: hdma1-242116")
    print("3. Click 'Compose new query'")
    print("4. Paste the SQL above")
    print("5. Click 'Run'")
    print("6. The table will be populated in: hdma1-242116.misc.1071_1k_Lenders")
    print("=" * 80)

