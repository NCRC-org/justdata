#!/usr/bin/env python3
"""
Create county-level data formatted for DataWrapper mapping.
Includes bank exemption percentages and loan distributions by county for 2024.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient
import pandas as pd


def create_county_map_data():
    """Create county-level data formatted for DataWrapper."""
    print("=" * 80)
    print("CREATING COUNTY MAP DATA FOR DATAWRAPPER")
    print("=" * 80)
    print()
    
    bq_client = BigQueryClient()
    disclosure_table = f"{bq_client.project_id}.sb.disclosure"
    
    print("Querying county-level data for 2024...")
    print()
    
    # Optimized query - calculate lender totals first, then join
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
      cd.geoid5 AS fips_code,
      cd.county_name,
      cd.state_name,
      CONCAT(cd.county_name, ', ', cd.state_name) AS county_state_full,
      COUNT(DISTINCT cd.respondent_id) AS total_banks,
      COUNT(DISTINCT CASE WHEN lt.total_loans_2024 < 1000 THEN cd.respondent_id END) AS exempt_banks,
      COUNT(DISTINCT CASE WHEN lt.total_loans_2024 >= 1000 THEN cd.respondent_id END) AS non_exempt_banks,
      ROUND(100.0 * COUNT(DISTINCT CASE WHEN lt.total_loans_2024 < 1000 THEN cd.respondent_id END) / 
            NULLIF(COUNT(DISTINCT cd.respondent_id), 0), 2) AS pct_exempt,
      SUM(CASE WHEN lt.total_loans_2024 < 1000 THEN cd.loans_in_county ELSE 0 END) AS loans_from_exempt_banks,
      SUM(cd.loans_in_county) AS total_loans_in_county,
      ROUND(100.0 * SUM(CASE WHEN lt.total_loans_2024 < 1000 THEN cd.loans_in_county ELSE 0 END) / 
            NULLIF(SUM(cd.loans_in_county), 0), 2) AS pct_loans_from_exempt_banks
    FROM county_data cd
    INNER JOIN lender_totals lt
      ON cd.respondent_id = lt.respondent_id
    GROUP BY cd.geoid5, cd.county_name, cd.state_name
    HAVING COUNT(DISTINCT cd.respondent_id) > 0
    ORDER BY cd.state_name, cd.county_name
    """
    
    result = bq_client.query(sql)
    df = result.to_dataframe()
    
    print(f"Found {len(df)} counties with bank data")
    print()
    
    # Format for DataWrapper
    # DataWrapper works best with:
    # - FIPS codes (5-digit) for county mapping
    # - Clean column names
    # - No special characters
    
    # Create DataWrapper-ready format
    dw_df = pd.DataFrame({
        'FIPS Code': df['fips_code'],
        'County': df['county_name'],
        'State': df['state_name'],
        'County, State': df['county_state_full'],
        'Total Banks': df['total_banks'],
        'Exempt Banks (<1K loans)': df['exempt_banks'],
        'Non-Exempt Banks (>=1K loans)': df['non_exempt_banks'],
        'Pct Exempt': df['pct_exempt'],
        'Loans from Exempt Banks': df['loans_from_exempt_banks'],
        'Total Loans in County': df['total_loans_in_county'],
        'Pct Loans from Exempt Banks': df['pct_loans_from_exempt_banks']
    })
    
    # Fill NaN with 0 for numeric columns
    numeric_cols = ['Total Banks', 'Exempt Banks (<1K loans)', 'Non-Exempt Banks (>=1K loans)', 
                    'Pct Exempt', 'Loans from Exempt Banks', 'Total Loans in County', 
                    'Pct Loans from Exempt Banks']
    for col in numeric_cols:
        dw_df[col] = dw_df[col].fillna(0)
    
    # Summary statistics
    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Total counties: {len(dw_df):,}")
    print(f"Counties with 80%+ exempt: {len(dw_df[dw_df['Pct Exempt'] >= 80]):,}")
    print(f"Counties with 90%+ exempt: {len(dw_df[dw_df['Pct Exempt'] >= 90]):,}")
    print(f"Average % exempt (unweighted): {dw_df['Pct Exempt'].mean():.1f}%")
    print(f"Total loans from exempt banks: {dw_df['Loans from Exempt Banks'].sum():,.0f}")
    print()
    
    # Create Excel file formatted for DataWrapper
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_file = f"county_map_data_2024_{timestamp}.xlsx"
    
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # Main sheet - DataWrapper ready format
        dw_df.to_excel(writer, sheet_name='DataWrapper Format', index=False)
        
        # Instructions sheet
        instructions = [
            ["DataWrapper Import Instructions"],
            [""],
            ["1. Go to datawrapper.de and create a new map"],
            ["2. Choose 'United States - Counties' as the map type"],
            ["3. Click 'Upload Data' and select this Excel file"],
            ["4. Select the 'DataWrapper Format' sheet"],
            ["5. Choose 'FIPS Code' as the geographic identifier column"],
            [""],
            ["Available Metrics to Map:"],
            ["- Pct Exempt: Percentage of banks that would be exempt (<1K loans)"],
            ["- Exempt Banks (<1K loans): Number of exempt banks"],
            ["- Total Banks: Total number of banks in county"],
            ["- Loans from Exempt Banks: Number of loans from exempt banks"],
            ["- Pct Loans from Exempt Banks: Percentage of loans from exempt banks"],
            [""],
            ["Note: FIPS Code is the 5-digit county FIPS code required by DataWrapper"],
            ["Format: State FIPS (2 digits) + County FIPS (3 digits) = 5 digits"],
        ]
        instructions_df = pd.DataFrame(instructions)
        instructions_df.to_excel(writer, sheet_name='Instructions', index=False, header=False)
        
        # Summary sheet
        summary_data = {
            'Metric': [
                'Total Counties',
                'Counties with 80%+ Exempt',
                'Counties with 90%+ Exempt',
                'Average % Exempt (unweighted)',
                'Average % Exempt (weighted by banks)',
                'Total Loans from Exempt Banks',
                'Total Banks (all counties)',
                'Total Exempt Banks (all counties)'
            ],
            'Value': [
                len(dw_df),
                len(dw_df[dw_df['Pct Exempt'] >= 80]),
                len(dw_df[dw_df['Pct Exempt'] >= 90]),
                dw_df['Pct Exempt'].mean(),
                (dw_df['Exempt Banks (<1K loans)'].sum() / dw_df['Total Banks'].sum() * 100),
                dw_df['Loans from Exempt Banks'].sum(),
                dw_df['Total Banks'].sum(),
                dw_df['Exempt Banks (<1K loans)'].sum()
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
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
    print("DATAWRAPPER READY!")
    print("=" * 80)
    print()
    print("The file includes:")
    print("  - DataWrapper Format sheet: Ready to import (use FIPS Code column)")
    print("  - Instructions sheet: Step-by-step import guide")
    print("  - Summary sheet: Overall statistics")
    print()
    print("Key columns for mapping:")
    print("  - FIPS Code: 5-digit county FIPS (required by DataWrapper)")
    print("  - Pct Exempt: Percentage of banks exempt (good for color mapping)")
    print("  - Exempt Banks: Number of exempt banks (good for bubble maps)")
    print()


if __name__ == '__main__':
    create_county_map_data()

