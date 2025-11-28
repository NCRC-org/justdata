#!/usr/bin/env python3
"""
Analyze bank exemptions by county for 2024.
Shows how many banks and what percentage would be exempt (<1,000 loans) by county.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient
import pandas as pd


def analyze_bank_exemptions_by_county():
    """Analyze bank exemptions by county for 2024."""
    print("=" * 80)
    print("BANK EXEMPTIONS BY COUNTY ANALYSIS - 2024")
    print("=" * 80)
    print()
    
    bq_client = BigQueryClient()
    disclosure_table = f"{bq_client.project_id}.sb.disclosure"
    
    print("Querying data...")
    print()
    
    # First, get total loans per lender (across all counties) for 2024
    sql = f"""
    WITH lender_total_loans_2024 AS (
      SELECT 
        respondent_id,
        SUM(COALESCE(num_under_100k, 0) + 
            COALESCE(num_100k_250k, 0) + 
            COALESCE(num_250k_1m, 0)) AS total_loans_2024
      FROM `{disclosure_table}`
      WHERE CAST(year AS INT64) = 2024
      GROUP BY respondent_id
    ),
    -- Get counties where each bank operates (has loans)
    lender_counties AS (
      SELECT DISTINCT
        d.respondent_id,
        LPAD(CAST(d.geoid5 AS STRING), 5, '0') AS geoid5,
        g.county_state,
        g.county AS county_name,
        g.state AS state_name
      FROM `{disclosure_table}` d
      LEFT JOIN `{bq_client.project_id}.geo.cbsa_to_county` g 
        ON LPAD(CAST(d.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
      WHERE CAST(d.year AS INT64) = 2024
        AND d.geoid5 IS NOT NULL
    )
    SELECT 
      lc.geoid5,
      lc.county_state,
      lc.county_name,
      lc.state_name,
      COUNT(DISTINCT lc.respondent_id) AS total_banks_in_county,
      COUNT(DISTINCT CASE WHEN ltl.total_loans_2024 < 1000 THEN lc.respondent_id END) AS exempt_banks_in_county,
      COUNT(DISTINCT CASE WHEN ltl.total_loans_2024 >= 1000 THEN lc.respondent_id END) AS non_exempt_banks_in_county,
      ROUND(100.0 * COUNT(DISTINCT CASE WHEN ltl.total_loans_2024 < 1000 THEN lc.respondent_id END) / 
            NULLIF(COUNT(DISTINCT lc.respondent_id), 0), 2) AS pct_exempt
    FROM lender_counties lc
    INNER JOIN lender_total_loans_2024 ltl
      ON lc.respondent_id = ltl.respondent_id
    GROUP BY lc.geoid5, lc.county_state, lc.county_name, lc.state_name
    HAVING COUNT(DISTINCT lc.respondent_id) > 0
    ORDER BY pct_exempt DESC, total_banks_in_county DESC
    """
    
    result = bq_client.query(sql)
    df = result.to_dataframe()
    
    print(f"Found {len(df)} counties with bank data")
    print()
    
    # Summary statistics
    total_counties = len(df)
    counties_80_90_pct = len(df[df['pct_exempt'] >= 80])
    counties_90_plus_pct = len(df[df['pct_exempt'] >= 90])
    
    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Total counties with bank data: {total_counties:,}")
    print(f"Counties with 80-90% exempt: {len(df[(df['pct_exempt'] >= 80) & (df['pct_exempt'] < 90)]):,}")
    print(f"Counties with 90%+ exempt: {counties_90_plus_pct:,}")
    print(f"Counties with 80%+ exempt: {counties_80_90_pct:,}")
    print()
    
    # Show top counties by exemption percentage
    print("=" * 80)
    print("TOP 20 COUNTIES BY EXEMPTION PERCENTAGE")
    print("=" * 80)
    print()
    top_counties = df.head(20)
    print(f"{'County':<30} {'State':<10} {'Total Banks':<15} {'Exempt':<15} {'% Exempt':<15}")
    print("-" * 80)
    for _, row in top_counties.iterrows():
        print(f"{row['county_name']:<30} {row['state_name']:<10} {row['total_banks_in_county']:<15,} "
              f"{row['exempt_banks_in_county']:<15,} {row['pct_exempt']:<15.1f}%")
    print()
    
    # Export to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"bank_exemptions_by_county_2024_{timestamp}.csv"
    df.to_csv(csv_file, index=False)
    print(f"✓ Exported to: {csv_file}")
    print()
    
    # Also create Excel with summary
    excel_file = f"bank_exemptions_by_county_2024_{timestamp}.xlsx"
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # All counties
        df.to_excel(writer, sheet_name='All Counties', index=False)
        
        # Summary sheet
        summary_data = {
            'Metric': [
                'Total Counties with Bank Data',
                'Counties with 80-90% Exempt',
                'Counties with 90%+ Exempt',
                'Counties with 80%+ Exempt',
                'Average % Exempt (weighted by banks)',
                'Average % Exempt (unweighted)'
            ],
            'Value': [
                total_counties,
                len(df[(df['pct_exempt'] >= 80) & (df['pct_exempt'] < 90)]),
                counties_90_plus_pct,
                counties_80_90_pct,
                (df['exempt_banks_in_county'].sum() / df['total_banks_in_county'].sum() * 100),
                df['pct_exempt'].mean()
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Top 50 by exemption %
        top_50 = df.head(50)
        top_50.to_excel(writer, sheet_name='Top 50 Counties', index=False)
    
    print(f"✓ Excel file created: {excel_file}")
    print()
    
    # Move to Downloads
    import shutil
    from pathlib import Path
    downloads_path = Path.home() / 'Downloads' / excel_file
    shutil.move(excel_file, downloads_path)
    print(f"✓ Moved to Downloads: {downloads_path}")
    print()
    
    print("=" * 80)


if __name__ == '__main__':
    analyze_bank_exemptions_by_county()

