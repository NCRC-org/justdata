#!/usr/bin/env python3
"""
Analyze distribution of loans from exempt banks (<1,000 loans) by county for 2024.
Shows where the 176,360 loans are located.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient
import pandas as pd


def analyze_loans_from_exempt_banks():
    """Analyze loans from exempt banks by county for 2024."""
    print("=" * 80)
    print("LOANS FROM EXEMPT BANKS BY COUNTY - 2024")
    print("=" * 80)
    print()
    
    bq_client = BigQueryClient()
    disclosure_table = f"{bq_client.project_id}.sb.disclosure"
    
    print("Querying data...")
    print()
    
    # Get lenders with <1,000 loans total in 2024
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
      HAVING total_loans_2024 < 1000
    ),
    -- Get loans from exempt banks by county
    exempt_loans_by_county AS (
      SELECT 
        LPAD(CAST(d.geoid5 AS STRING), 5, '0') AS geoid5,
        g.county_state,
        g.county AS county_name,
        g.state AS state_name,
        SUM(COALESCE(d.num_under_100k, 0) + 
            COALESCE(d.num_100k_250k, 0) + 
            COALESCE(d.num_250k_1m, 0)) AS loans_from_exempt_banks,
        COUNT(DISTINCT d.respondent_id) AS num_exempt_banks_in_county
      FROM `{disclosure_table}` d
      INNER JOIN lender_total_loans_2024 etl
        ON d.respondent_id = etl.respondent_id
      LEFT JOIN `{bq_client.project_id}.geo.cbsa_to_county` g 
        ON LPAD(CAST(d.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
      WHERE CAST(d.year AS INT64) = 2024
        AND d.geoid5 IS NOT NULL
      GROUP BY geoid5, g.county_state, g.county, g.state
    )
    SELECT 
      *,
      ROUND(100.0 * loans_from_exempt_banks / 
            (SELECT SUM(loans_from_exempt_banks) FROM exempt_loans_by_county), 2) AS pct_of_total_exempt_loans
    FROM exempt_loans_by_county
    ORDER BY loans_from_exempt_banks DESC
    """
    
    result = bq_client.query(sql)
    df = result.to_dataframe()
    
    total_loans = df['loans_from_exempt_banks'].sum()
    
    print(f"Total loans from exempt banks: {total_loans:,}")
    print(f"Counties with exempt bank loans: {len(df):,}")
    print()
    
    # Summary statistics
    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Total loans from exempt banks: {total_loans:,}")
    print(f"Counties with exempt bank loans: {len(df):,}")
    print(f"Average loans per county: {df['loans_from_exempt_banks'].mean():,.0f}")
    print(f"Median loans per county: {df['loans_from_exempt_banks'].median():,.0f}")
    print(f"Top 10 counties account for: {df.head(10)['pct_of_total_exempt_loans'].sum():.1f}% of exempt loans")
    print(f"Top 50 counties account for: {df.head(50)['pct_of_total_exempt_loans'].sum():.1f}% of exempt loans")
    print()
    
    # Show top counties
    print("=" * 80)
    print("TOP 20 COUNTIES BY EXEMPT BANK LOANS")
    print("=" * 80)
    print()
    top_counties = df.head(20)
    print(f"{'County':<30} {'State':<10} {'Loans':<15} {'% of Total':<15} {'# Banks':<15}")
    print("-" * 80)
    for _, row in top_counties.iterrows():
        print(f"{row['county_name']:<30} {row['state_name']:<10} "
              f"{row['loans_from_exempt_banks']:<15,} "
              f"{row['pct_of_total_exempt_loans']:<15.2f}% "
              f"{row['num_exempt_banks_in_county']:<15,}")
    print()
    
    # Export to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"exempt_bank_loans_by_county_2024_{timestamp}.csv"
    df.to_csv(csv_file, index=False)
    print(f"✓ Exported to: {csv_file}")
    print()
    
    # Create Excel with multiple sheets
    excel_file = f"exempt_bank_loans_by_county_2024_{timestamp}.xlsx"
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # All counties
        df.to_excel(writer, sheet_name='All Counties', index=False)
        
        # Summary sheet
        summary_data = {
            'Metric': [
                'Total Loans from Exempt Banks',
                'Total Counties',
                'Average Loans per County',
                'Median Loans per County',
                'Top 10 Counties % of Total',
                'Top 50 Counties % of Total'
            ],
            'Value': [
                total_loans,
                len(df),
                df['loans_from_exempt_banks'].mean(),
                df['loans_from_exempt_banks'].median(),
                df.head(10)['pct_of_total_exempt_loans'].sum(),
                df.head(50)['pct_of_total_exempt_loans'].sum()
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Top 50 counties
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
    analyze_loans_from_exempt_banks()

