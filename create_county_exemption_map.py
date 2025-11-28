#!/usr/bin/env python3
"""
Create county-level map data showing bank exemptions for 2024.
Formatted for DataWrapper with FIPS codes.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient
import pandas as pd


def create_county_exemption_map():
    """Create county-level exemption map data for DataWrapper."""
    print("=" * 80)
    print("CREATING COUNTY EXEMPTION MAP DATA FOR 2024")
    print("=" * 80)
    print()
    print("Note: Mapping by operating counties (where banks have loans)")
    print("      Headquarters location would require additional data source")
    print()
    
    bq_client = BigQueryClient()
    disclosure_table = f"{bq_client.project_id}.sb.disclosure"
    
    print("Querying data...")
    print("⏳ This may take several minutes for large datasets...")
    print()
    print("Step 1/3: Calculating lender totals for 2023 and 2024...")
    import time
    start_time = time.time()
    
    # Calculate lender totals for both 2023 and 2024 to determine exemption
    # Exempt if: <1,000 loans in BOTH 2023 AND 2024
    sql = f"""
    WITH lender_totals_by_year AS (
      SELECT 
        respondent_id,
        CAST(year AS INT64) AS year,
        SUM(COALESCE(num_under_100k, 0) + 
            COALESCE(num_100k_250k, 0) + 
            COALESCE(num_250k_1m, 0)) AS total_loans
      FROM `{disclosure_table}`
      WHERE CAST(year AS INT64) IN (2023, 2024)
      GROUP BY respondent_id, CAST(year AS INT64)
    ),
    lender_exemption_status AS (
      SELECT 
        respondent_id,
        COALESCE(MAX(CASE WHEN year = 2023 THEN total_loans END), 0) AS total_loans_2023,
        COALESCE(MAX(CASE WHEN year = 2024 THEN total_loans END), 0) AS total_loans_2024,
        CASE 
          WHEN COALESCE(MAX(CASE WHEN year = 2023 THEN total_loans END), 0) < 1000 
           AND COALESCE(MAX(CASE WHEN year = 2024 THEN total_loans END), 0) < 1000
          THEN 1  -- Exempt (both years <1,000)
          ELSE 0   -- Not exempt
        END AS is_exempt
      FROM lender_totals_by_year
      GROUP BY respondent_id
    ),
    county_lender_data AS (
      SELECT 
        LPAD(CAST(d.geoid5 AS STRING), 5, '0') AS geoid5,
        g.county AS county_name,
        g.state AS state_name,
        d.respondent_id,
        SUM(COALESCE(d.num_under_100k, 0) + 
            COALESCE(d.num_100k_250k, 0) + 
            COALESCE(d.num_250k_1m, 0)) AS loans_in_county,
        -- Loan amounts in thousands (will multiply by 1000 for dollars)
        SUM(COALESCE(d.amt_under_100k, 0) + 
            COALESCE(d.amt_100k_250k, 0) + 
            COALESCE(d.amt_250k_1m, 0)) AS loan_dollars_in_county_thousands
      FROM `{disclosure_table}` d
      LEFT JOIN `{bq_client.project_id}.geo.cbsa_to_county` g 
        ON LPAD(CAST(d.geoid5 AS STRING), 5, '0') = LPAD(CAST(g.geoid5 AS STRING), 5, '0')
      WHERE CAST(d.year AS INT64) = 2024
        AND d.geoid5 IS NOT NULL
      GROUP BY geoid5, g.county, g.state, d.respondent_id
    )
    SELECT 
      cld.geoid5 AS fips_code,
      cld.county_name,
      cld.state_name,
      CONCAT(cld.county_name, ', ', cld.state_name) AS county_state,
      COUNT(DISTINCT cld.respondent_id) AS total_banks,
      COUNT(DISTINCT CASE WHEN les.is_exempt = 1 THEN cld.respondent_id END) AS exempt_banks,
      COUNT(DISTINCT CASE WHEN les.is_exempt = 0 THEN cld.respondent_id END) AS non_exempt_banks,
      ROUND(100.0 * COUNT(DISTINCT CASE WHEN les.is_exempt = 1 THEN cld.respondent_id END) / 
            NULLIF(COUNT(DISTINCT cld.respondent_id), 0), 2) AS pct_exempt,
      SUM(CASE WHEN les.is_exempt = 1 THEN cld.loans_in_county ELSE 0 END) AS loans_from_exempt_banks,
      SUM(cld.loans_in_county) AS total_loans_in_county,
      ROUND(100.0 * SUM(CASE WHEN les.is_exempt = 1 THEN cld.loans_in_county ELSE 0 END) / 
            NULLIF(SUM(cld.loans_in_county), 0), 2) AS pct_loans_from_exempt,
      -- Loan dollars (amounts) from exempt banks (in thousands, will convert to dollars)
      SUM(CASE WHEN les.is_exempt = 1 THEN cld.loan_dollars_in_county_thousands ELSE 0 END) AS loan_dollars_from_exempt_thousands,
      SUM(cld.loan_dollars_in_county_thousands) AS total_loan_dollars_thousands,
      ROUND(100.0 * SUM(CASE WHEN les.is_exempt = 1 THEN cld.loan_dollars_in_county_thousands ELSE 0 END) / 
            NULLIF(SUM(cld.loan_dollars_in_county_thousands), 0), 2) AS pct_loan_dollars_from_exempt
    FROM county_lender_data cld
    INNER JOIN lender_exemption_status les
      ON cld.respondent_id = les.respondent_id
    GROUP BY cld.geoid5, cld.county_name, cld.state_name
    HAVING COUNT(DISTINCT cld.respondent_id) > 0
    ORDER BY cld.state_name, cld.county_name
    """
    
    try:
        print("Step 2/3: Executing query (this may take 2-5 minutes)...")
        query_job = bq_client.query(sql)
        
        # Wait for query with progress updates
        print("⏳ Waiting for query to complete...")
        elapsed = 0
        while not query_job.done():
            time.sleep(10)  # Check every 10 seconds
            elapsed += 10
            if elapsed % 30 == 0:  # Print every 30 seconds
                print(f"  Still running... ({elapsed // 60}m {elapsed % 60}s elapsed)")
        
        query_job.result()  # This will raise an exception if the job failed
        query_time = time.time() - start_time
        print(f"✓ Query completed in {query_time // 60:.0f}m {query_time % 60:.0f}s")
        print()
        
        print("Step 3/3: Fetching results and creating Excel file...")
        df = query_job.to_dataframe()
        
        print(f"✓ Found {len(df)} counties with bank data")
        print()
        
        # Format for DataWrapper - clean column names
        # Ensure FIPS codes are strings with exactly 5 digits (leading zeros preserved)
        fips_series = df['fips_code'].astype(str).str.strip()
        # Remove any decimal points if present (from float conversion)
        fips_series = fips_series.str.replace('.0', '', regex=False)
        # Pad to 5 digits with leading zeros
        fips_series = fips_series.str.zfill(5)
        
        # Convert loan dollars from thousands to actual dollars
        loan_dollars_exempt = (df['loan_dollars_from_exempt_thousands'].fillna(0) * 1000).astype(int)
        loan_dollars_total = (df['total_loan_dollars_thousands'].fillna(0) * 1000).astype(int)
        
        # Create DataFrame with all required columns, clearly labeled
        dw_df = pd.DataFrame({
            'FIPS': fips_series,  # String format with leading zeros
            'County': df['county_name'],
            'State': df['state_name'],
            'County_State': df['county_state'],
            # Total metrics
            'Total_Banks': df['total_banks'].fillna(0).astype(int),
            'Total_Loans': df['total_loans_in_county'].fillna(0).astype(int),
            'Total_Loan_Dollars': loan_dollars_total,
            # Exempt metrics
            'Exempt_Banks': df['exempt_banks'].fillna(0).astype(int),
            'Exempt_Loans': df['loans_from_exempt_banks'].fillna(0).astype(int),
            'Exempt_Loan_Dollars': loan_dollars_exempt,
            # Additional info
            'NonExempt_Banks': df['non_exempt_banks'].fillna(0).astype(int),
            'Pct_Exempt': df['pct_exempt'].fillna(0).round(2),
            'Pct_Loans_Exempt': df['pct_loans_from_exempt'].fillna(0).round(2),
            'Pct_Loan_Dollars_Exempt': df['pct_loan_dollars_from_exempt'].fillna(0).round(2)
        })
        
        # Verify Connecticut FIPS codes
        ct_counties = dw_df[dw_df['State'] == 'Connecticut']
        if len(ct_counties) > 0:
            print(f"Connecticut counties found: {len(ct_counties)}")
            print("Sample FIPS codes:")
            print(ct_counties[['FIPS', 'County', 'State']].head(10).to_string())
            print()
        
        # Summary
        total_counties = len(dw_df)
        counties_80_90 = len(dw_df[(dw_df['Pct_Exempt'] >= 80) & (dw_df['Pct_Exempt'] < 90)])
        counties_90_plus = len(dw_df[dw_df['Pct_Exempt'] >= 90])
        avg_pct_exempt = dw_df['Pct_Exempt'].mean()
        weighted_pct = (dw_df['Exempt_Banks'].sum() / dw_df['Total_Banks'].sum() * 100) if dw_df['Total_Banks'].sum() > 0 else 0
        
        print("=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)
        print(f"Total counties with bank data: {total_counties:,}")
        print(f"Counties with 80-90% exempt: {counties_80_90:,}")
        print(f"Counties with 90%+ exempt: {counties_90_plus:,}")
        print(f"Counties with 80%+ exempt: {len(dw_df[dw_df['Pct_Exempt'] >= 80]):,}")
        print(f"Average % exempt (unweighted): {avg_pct_exempt:.1f}%")
        print(f"Overall % exempt (weighted by banks): {weighted_pct:.1f}%")
        print(f"Total exempt banks: {dw_df['Exempt_Banks'].sum():,}")
        print(f"Total banks: {dw_df['Total_Banks'].sum():,}")
        print()
        
        # Create Excel file
        print("  Creating Excel file...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_file = f"county_exemption_map_2024_{timestamp}.xlsx"
        
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            # DataWrapper format - main sheet
            # Write FIPS as text to preserve leading zeros
            dw_df_excel = dw_df.copy()
            dw_df_excel['FIPS'] = "'" + dw_df_excel['FIPS'].astype(str) + "'"  # Add apostrophe prefix to force text format
            dw_df_excel.to_excel(writer, sheet_name='DataWrapper', index=False)
            
            # Also create a CSV-friendly version without apostrophes (for direct CSV export)
            dw_df.to_excel(writer, sheet_name='DataWrapper_CSV', index=False)
            
            # Instructions
            instructions = [
                ["DataWrapper Import Instructions"],
                [""],
                ["1. Go to datawrapper.de and click 'Create a chart'"],
                ["2. Select 'Map' and choose 'United States - Counties'"],
                ["3. Click 'Upload Data' and select this Excel file"],
                ["4. Select the 'DataWrapper' sheet"],
                ["5. In 'Select a column', choose 'FIPS' as the geographic identifier"],
                ["6. Choose 'Pct_Exempt' or 'Exempt_Banks' as the data column to visualize"],
                [""],
                ["IMPORTANT - FIPS Code Format:"],
                ["- FIPS codes are stored as text with leading zeros (e.g., '09110' for Connecticut)"],
                ["- If DataWrapper doesn't recognize them, try:"],
                ["  a) Export 'DataWrapper_CSV' sheet to CSV and upload that instead"],
                ["  b) Or manually format FIPS column as 'Text' in Excel before uploading"],
                ["  c) Or use the FIPS codes directly: they should be 5-digit strings"],
                [""],
                ["Column Descriptions:"],
                [""],
                ["TOTAL METRICS (2024 data only):"],
                ["- Total_Banks: Total number of banks operating in county"],
                ["- Total_Loans: Total number of loans in county (2024)"],
                ["- Total_Loan_Dollars: Total loan dollar amounts in county (2024)"],
                [""],
                ["EXEMPT METRICS (2024 data only, from exempt banks):"],
                ["- Exempt_Banks: Number of banks with <1,000 loans in BOTH 2023 AND 2024"],
                ["- Exempt_Loans: Number of loans from exempt banks in county (2024)"],
                ["- Exempt_Loan_Dollars: Loan dollar amounts from exempt banks in county (2024)"],
                [""],
                ["ADDITIONAL INFO:"],
                ["- FIPS: 5-digit county FIPS code (required for DataWrapper mapping)"],
                ["- NonExempt_Banks: Number of banks that are NOT exempt"],
                ["- Pct_Exempt: Percentage of banks that would be exempt"],
                ["- Pct_Loans_Exempt: Percentage of loans from exempt banks"],
                ["- Pct_Loan_Dollars_Exempt: Percentage of loan dollars from exempt banks"],
                [""],
                ["Exemption Rule: Banks with <1,000 total loans nationwide in BOTH 2023 AND 2024 are exempt"],
                ["      (Must have <1,000 loans in both consecutive years to be exempt in 2024)"],
                ["Note: Data shows banks by operating counties (where they have loans)"],
            ]
            instructions_df = pd.DataFrame(instructions)
            instructions_df.to_excel(writer, sheet_name='Instructions', index=False, header=False)
            
            # Summary
            summary_data = {
                'Metric': [
                    'Total Counties',
                    'Counties with 80-90% Exempt',
                    'Counties with 90%+ Exempt',
                    'Counties with 80%+ Exempt',
                    'Average % Exempt (unweighted)',
                    'Overall % Exempt (weighted)',
                    'Total Banks',
                    'Total Exempt Banks'
                ],
                'Value': [
                    total_counties,
                    counties_80_90,
                    counties_90_plus,
                    len(dw_df[dw_df['Pct_Exempt'] >= 80]),
                    round(avg_pct_exempt, 2),
                    round(weighted_pct, 2),
                    int(dw_df['Total_Banks'].sum()),
                    int(dw_df['Exempt_Banks'].sum())
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Top counties by exemption % - include all key metrics
            top_counties = dw_df.nlargest(50, 'Pct_Exempt')[
                ['County', 'State', 'Total_Banks', 'Total_Loans', 'Total_Loan_Dollars',
                 'Exempt_Banks', 'Exempt_Loans', 'Exempt_Loan_Dollars', 'Pct_Exempt']
            ]
            top_counties.to_excel(writer, sheet_name='Top 50 Counties', index=False)
        
        print(f"✓ Excel file created: {excel_file}")
        print()
        
        # Move to Downloads
        print("  Moving file to Downloads folder...")
        import shutil
        from pathlib import Path
        downloads_path = Path.home() / 'Downloads' / excel_file
        shutil.move(excel_file, downloads_path)
        print(f"✓ File saved to Downloads: {downloads_path}")
        print()
        
        total_time = time.time() - start_time
        print(f"✓ Total time: {total_time // 60:.0f}m {total_time % 60:.0f}s")
        print()
        
        print("=" * 80)
        print("READY FOR DATAWRAPPER!")
        print("=" * 80)
        print()
        print("The 'DataWrapper' sheet is formatted for direct import.")
        print("Use 'FIPS' column as geographic identifier.")
        print("Use 'Pct_Exempt' for color mapping or 'Exempt_Banks' for bubble maps.")
        print()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    create_county_exemption_map()

