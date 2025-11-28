#!/usr/bin/env python3
"""Check Brevard County, Florida exemption calculations."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient

bq_client = BigQueryClient()
disclosure_table = f"{bq_client.project_id}.sb.disclosure"

print("=" * 80)
print("BREVARD COUNTY, FLORIDA - EXEMPTION ANALYSIS")
print("=" * 80)
print()

# Step 1: Find Brevard County FIPS code
print("Step 1: Finding Brevard County FIPS code...")
sql1 = f"""
SELECT DISTINCT
  LPAD(CAST(geoid5 AS STRING), 5, '0') AS geoid5,
  county,
  state
FROM `{bq_client.project_id}.geo.cbsa_to_county`
WHERE UPPER(county) LIKE '%BREVARD%'
  AND UPPER(state) = 'FLORIDA'
"""

result1 = bq_client.query(sql1)
df1 = result1.to_dataframe()
if len(df1) > 0:
    brevard_fips = df1.iloc[0]['geoid5']
    print(f"Found: {df1.iloc[0]['county']}, {df1.iloc[0]['state']} - FIPS: {brevard_fips}")
    print()
else:
    print("Brevard County not found in geo table")
    brevard_fips = None

if brevard_fips:
    # Step 2: Get lender totals for 2024
    print("Step 2: Calculating lender totals (2024)...")
    sql2 = f"""
    SELECT 
      respondent_id,
      SUM(COALESCE(num_under_100k, 0) + 
          COALESCE(num_100k_250k, 0) + 
          COALESCE(num_250k_1m, 0)) AS total_loans_2024
    FROM `{disclosure_table}`
    WHERE CAST(year AS INT64) = 2024
    GROUP BY respondent_id
    """
    
    # Step 3: Get banks in Brevard County
    print("Step 3: Getting banks operating in Brevard County...")
    sql3 = f"""
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
        AND LPAD(CAST(d.geoid5 AS STRING), 5, '0') = '{brevard_fips}'
      GROUP BY d.respondent_id
    )
    SELECT 
      bb.respondent_id,
      lt.total_loans_2024 AS bank_total_loans_nationwide,
      bb.loans_in_brevard,
      CASE 
        WHEN lt.total_loans_2024 < 1000 THEN 'Exempt'
        ELSE 'Non-Exempt'
      END AS exemption_status
    FROM brevard_banks bb
    INNER JOIN lender_totals lt
      ON bb.respondent_id = lt.respondent_id
    ORDER BY bb.loans_in_brevard DESC
    LIMIT 20
    """
    
    result3 = bq_client.query(sql3)
    df3 = result3.to_dataframe()
    
    print(f"Found {len(df3)} banks operating in Brevard County")
    print()
    print("Top 20 banks by loans in Brevard County:")
    print()
    print(f"{'Respondent ID':<20} {'Nationwide Total':<20} {'Brevard Loans':<20} {'Status':<15}")
    print("-" * 80)
    for _, row in df3.iterrows():
        print(f"{row['respondent_id']:<20} {row['bank_total_loans_nationwide']:<20,} "
              f"{row['loans_in_brevard']:<20,} {row['exemption_status']:<15}")
    print()
    
    # Step 4: Summary
    print("Step 4: Summary statistics...")
    sql4 = f"""
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
    brevard_data AS (
      SELECT 
        d.respondent_id,
        SUM(COALESCE(d.num_under_100k, 0) + 
            COALESCE(d.num_100k_250k, 0) + 
            COALESCE(d.num_250k_1m, 0)) AS loans_in_brevard
      FROM `{disclosure_table}` d
      WHERE CAST(d.year AS INT64) = 2024
        AND LPAD(CAST(d.geoid5 AS STRING), 5, '0') = '{brevard_fips}'
      GROUP BY d.respondent_id
    )
    SELECT 
      COUNT(DISTINCT bd.respondent_id) AS total_banks,
      COUNT(DISTINCT CASE WHEN lt.total_loans_2024 < 1000 THEN bd.respondent_id END) AS exempt_banks,
      COUNT(DISTINCT CASE WHEN lt.total_loans_2024 >= 1000 THEN bd.respondent_id END) AS non_exempt_banks,
      ROUND(100.0 * COUNT(DISTINCT CASE WHEN lt.total_loans_2024 < 1000 THEN bd.respondent_id END) / 
            NULLIF(COUNT(DISTINCT bd.respondent_id), 0), 2) AS pct_exempt_banks,
      SUM(bd.loans_in_brevard) AS total_loans,
      SUM(CASE WHEN lt.total_loans_2024 < 1000 THEN bd.loans_in_brevard ELSE 0 END) AS loans_from_exempt,
      SUM(CASE WHEN lt.total_loans_2024 >= 1000 THEN bd.loans_in_brevard ELSE 0 END) AS loans_from_non_exempt,
      ROUND(100.0 * SUM(CASE WHEN lt.total_loans_2024 < 1000 THEN bd.loans_in_brevard ELSE 0 END) / 
            NULLIF(SUM(bd.loans_in_brevard), 0), 2) AS pct_loans_from_exempt
    FROM brevard_data bd
    INNER JOIN lender_totals lt
      ON bd.respondent_id = lt.respondent_id
    """
    
    result4 = bq_client.query(sql4)
    df4 = result4.to_dataframe()
    
    print("=" * 80)
    print("BREVARD COUNTY SUMMARY")
    print("=" * 80)
    print()
    if len(df4) > 0:
        row = df4.iloc[0]
        print(f"Total Banks: {row['total_banks']:,}")
        print(f"Exempt Banks (<1K loans): {row['exempt_banks']:,}")
        print(f"Non-Exempt Banks (>=1K loans): {row['non_exempt_banks']:,}")
        print(f"% Banks Exempt: {row['pct_exempt_banks']:.1f}%")
        print()
        print(f"Total Loans in County: {row['total_loans']:,}")
        print(f"Loans from Exempt Banks: {row['loans_from_exempt']:,}")
        print(f"Loans from Non-Exempt Banks: {row['loans_from_non_exempt']:,}")
        print(f"% Loans from Exempt Banks: {row['pct_loans_from_exempt']:.1f}%")
        print()
        print("=" * 80)
        print("INTERPRETATION")
        print("=" * 80)
        print()
        if row['pct_exempt_banks'] > 70 and row['pct_loans_from_exempt'] < 30:
            print("✓ This makes sense:")
            print("  - Many small banks (exempt) operate in Brevard")
            print("  - But most loans come from large banks (non-exempt)")
            print("  - High exemption % for BANKS, but low % for LOANS")
        elif row['pct_exempt_banks'] > 70 and row['pct_loans_from_exempt'] > 70:
            print("⚠ This seems unusual:")
            print("  - Most banks are exempt AND most loans are from exempt banks")
            print("  - This might indicate an issue with the calculation")
        else:
            print("Results look reasonable for this county")

