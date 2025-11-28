#!/usr/bin/env python3
"""Check if Connecticut data exists in the disclosure table for 2024."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient

bq_client = BigQueryClient()
disclosure_table = f"{bq_client.project_id}.sb.disclosure"

print("Checking Connecticut data for 2024...")
print()

# Check if Connecticut counties exist
sql = f"""
SELECT 
  g.state AS state_name,
  COUNT(DISTINCT LPAD(CAST(d.geoid5 AS STRING), 5, '0')) AS num_counties,
  COUNT(DISTINCT d.respondent_id) AS num_banks,
  SUM(COALESCE(d.num_under_100k, 0) + 
      COALESCE(d.num_100k_250k, 0) + 
      COALESCE(d.num_250k_1m, 0)) AS total_loans
FROM `{disclosure_table}` d
LEFT JOIN `{bq_client.project_id}.geo.cbsa_to_county` g 
  ON LPAD(CAST(d.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
WHERE CAST(d.year AS INT64) = 2024
  AND d.geoid5 IS NOT NULL
  AND UPPER(g.state) = 'CONNECTICUT'
GROUP BY g.state
"""

result = bq_client.query(sql)
df = result.to_dataframe()

if len(df) > 0:
    print("Connecticut data found:")
    print(df.to_string())
    print()
    
    # Check individual counties
    sql2 = f"""
    SELECT 
      LPAD(CAST(d.geoid5 AS STRING), 5, '0') AS geoid5,
      g.county AS county_name,
      g.state AS state_name,
      COUNT(DISTINCT d.respondent_id) AS num_banks
    FROM `{disclosure_table}` d
    LEFT JOIN `{bq_client.project_id}.geo.cbsa_to_county` g 
      ON LPAD(CAST(d.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
    WHERE CAST(d.year AS INT64) = 2024
      AND d.geoid5 IS NOT NULL
      AND UPPER(g.state) = 'CONNECTICUT'
    GROUP BY geoid5, g.county, g.state
    ORDER BY g.county
    """
    
    result2 = bq_client.query(sql2)
    df2 = result2.to_dataframe()
    print(f"Connecticut counties with data: {len(df2)}")
    print(df2.to_string())
else:
    print("No Connecticut data found in 2024")
    print()
    print("Checking if Connecticut exists in geo table...")
    
    sql3 = f"""
    SELECT DISTINCT state, COUNT(*) as num_counties
    FROM `{bq_client.project_id}.geo.cbsa_to_county`
    WHERE UPPER(state) = 'CONNECTICUT'
    GROUP BY state
    """
    result3 = bq_client.query(sql3)
    df3 = result3.to_dataframe()
    if len(df3) > 0:
        print("Connecticut exists in geo table:")
        print(df3.to_string())
        print()
        print("But no disclosure data for 2024. Checking other years...")
        
        sql4 = f"""
        SELECT 
          CAST(d.year AS INT64) AS year,
          COUNT(DISTINCT LPAD(CAST(d.geoid5 AS STRING), 5, '0')) AS num_counties
        FROM `{disclosure_table}` d
        LEFT JOIN `{bq_client.project_id}.geo.cbsa_to_county` g 
          ON LPAD(CAST(d.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
        WHERE d.geoid5 IS NOT NULL
          AND UPPER(g.state) = 'CONNECTICUT'
        GROUP BY CAST(d.year AS INT64)
        ORDER BY year
        """
        result4 = bq_client.query(sql4)
        df4 = result4.to_dataframe()
        if len(df4) > 0:
            print("Connecticut data by year:")
            print(df4.to_string())
        else:
            print("No Connecticut data in any year")

