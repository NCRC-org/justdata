#!/usr/bin/env python3
"""
Generate the 6 required tables for 1071 analysis and export to Excel.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient
import pandas as pd


def generate_table_1(bq_client, table_id):
    """Table 1: Bank Size Analysis - All Lending"""
    # Query original disclosure table directly to avoid duplication
    disclosure_table = f"{bq_client.project_id}.sb.disclosure"
    sql = f"""
    WITH lender_loans_by_year AS (
      SELECT 
        CAST(year AS INT64) AS year,
        respondent_id,
        SUM(COALESCE(num_under_100k, 0) + 
            COALESCE(num_100k_250k, 0) + 
            COALESCE(num_250k_1m, 0)) AS total_loans
      FROM `{disclosure_table}`
      WHERE CAST(year AS INT64) IN (2018, 2019, 2020, 2021, 2022, 2023, 2024)
      GROUP BY CAST(year AS INT64), respondent_id
    ),
    bank_counts AS (
      SELECT 
        year,
        COUNT(DISTINCT respondent_id) AS all_banks,
        COUNT(DISTINCT CASE WHEN total_loans < 1000 THEN respondent_id END) AS banks_under_1k,
        SUM(CASE WHEN total_loans < 1000 THEN total_loans ELSE 0 END) AS loans_from_banks_under_1k,
        SUM(total_loans) AS all_bank_loans
      FROM lender_loans_by_year
      GROUP BY year
    )
    SELECT 
      year AS Year,
      banks_under_1k AS large_banks_under_1k,
      all_banks AS all_large_banks,
      loans_from_banks_under_1k AS loans_of_banks_under_1k,
      all_bank_loans AS all_large_bank_loans
    FROM bank_counts
    ORDER BY year
    """
    result = bq_client.query(sql)
    df = result.to_dataframe()
    # Rename columns to match requirements
    df.columns = ['Year', '# Large Banks <1 K loans', '# All large banks', 
                   '# loans of banks < 1k', '# all large bank loans']
    return df


def generate_table_2(bq_client, table_id):
    """Table 2: Business Revenue Analysis - All Lending"""
    # Query original disclosure table directly to avoid duplication
    disclosure_table = f"{bq_client.project_id}.sb.disclosure"
    sql = f"""
    SELECT 
      CAST(year AS INT64) AS Year,
      SUM(COALESCE(numsbrev_under_1m, 0)) AS loans_to_biz_under_1m,
      SUM(COALESCE(num_under_100k, 0) + 
          COALESCE(num_100k_250k, 0) + 
          COALESCE(num_250k_1m, 0) - 
          COALESCE(numsbrev_under_1m, 0)) AS loans_to_biz_over_1m
    FROM `{disclosure_table}`
    WHERE CAST(year AS INT64) IN (2018, 2019, 2020, 2021, 2022, 2023, 2024)
    GROUP BY CAST(year AS INT64)
    ORDER BY Year
    """
    result = bq_client.query(sql)
    df = result.to_dataframe()
    # Rename columns to match requirements
    df.columns = ['Year', '# loans to biz <$1 mill rev', '# loans to biz >$1 mil.']
    return df


def generate_table_3(bq_client, table_id):
    """Table 3: Combined Bank Size + Business Revenue - All Lending"""
    # Query original disclosure table directly to avoid duplication
    disclosure_table = f"{bq_client.project_id}.sb.disclosure"
    sql = f"""
    WITH lender_loans_by_year AS (
      SELECT 
        CAST(year AS INT64) AS year,
        respondent_id,
        SUM(COALESCE(num_under_100k, 0) + 
            COALESCE(num_100k_250k, 0) + 
            COALESCE(num_250k_1m, 0)) AS total_loans
      FROM `{disclosure_table}`
      WHERE CAST(year AS INT64) IN (2018, 2019, 2020, 2021, 2022, 2023, 2024)
      GROUP BY CAST(year AS INT64), respondent_id
    ),
    banks_over_1k AS (
      SELECT DISTINCT year, respondent_id
      FROM lender_loans_by_year
      WHERE total_loans >= 1000
    )
    SELECT 
      CAST(t.year AS INT64) AS Year,
      SUM(COALESCE(t.numsbrev_under_1m, 0)) AS loans_banks_over_1k_to_biz_under_1m,
      SUM(COALESCE(t.num_under_100k, 0) + 
          COALESCE(t.num_100k_250k, 0) + 
          COALESCE(t.num_250k_1m, 0) - 
          COALESCE(t.numsbrev_under_1m, 0)) AS loans_banks_over_1k_to_biz_over_1m
    FROM `{disclosure_table}` t
    INNER JOIN banks_over_1k b
      ON CAST(t.year AS INT64) = b.year 
      AND t.respondent_id = b.respondent_id
    WHERE CAST(t.year AS INT64) IN (2018, 2019, 2020, 2021, 2022, 2023, 2024)
    GROUP BY CAST(t.year AS INT64)
    ORDER BY Year
    """
    result = bq_client.query(sql)
    df = result.to_dataframe()
    # Rename columns to match requirements
    df.columns = ['Year', '#loans banks > 1 K to biz <1 mil', '# loans banks > 1 K to biz >1 mil']
    return df


def generate_table_4(bq_client, table_id):
    """Table 4: Bank Size Analysis - Non-Credit Card Lending Only"""
    # Query original disclosure table and filter by credit card status
    disclosure_table = f"{bq_client.project_id}.sb.disclosure"
    sql = f"""
    WITH lender_avg_loan AS (
      SELECT 
        respondent_id,
        CAST(year AS INT64) AS year,
        SAFE_DIVIDE(
          SUM(COALESCE(amt_under_100k, 0) + COALESCE(amt_100k_250k, 0) + COALESCE(amt_250k_1m, 0)),
          NULLIF(SUM(COALESCE(num_under_100k, 0) + COALESCE(num_100k_250k, 0) + COALESCE(num_250k_1m, 0)), 0)
        ) AS avg_loan_amount_thousands
      FROM `{disclosure_table}`
      WHERE CAST(year AS INT64) IN (2018, 2019, 2020, 2021, 2022, 2023, 2024)
      GROUP BY respondent_id, CAST(year AS INT64)
    ),
    lender_loans_by_year AS (
      SELECT 
        CAST(d.year AS INT64) AS year,
        d.respondent_id,
        SUM(COALESCE(d.num_under_100k, 0) + 
            COALESCE(d.num_100k_250k, 0) + 
            COALESCE(d.num_250k_1m, 0)) AS total_loans
      FROM `{disclosure_table}` d
      INNER JOIN lender_avg_loan lavg
        ON d.respondent_id = lavg.respondent_id
        AND CAST(d.year AS INT64) = lavg.year
      WHERE CAST(d.year AS INT64) IN (2018, 2019, 2020, 2021, 2022, 2023, 2024)
        AND (lavg.avg_loan_amount_thousands IS NULL OR lavg.avg_loan_amount_thousands >= 10)
      GROUP BY CAST(d.year AS INT64), d.respondent_id
    ),
    bank_counts AS (
      SELECT 
        year,
        COUNT(DISTINCT respondent_id) AS all_banks,
        COUNT(DISTINCT CASE WHEN total_loans < 1000 THEN respondent_id END) AS banks_under_1k,
        SUM(CASE WHEN total_loans < 1000 THEN total_loans ELSE 0 END) AS loans_from_banks_under_1k,
        SUM(total_loans) AS all_bank_loans
      FROM lender_loans_by_year
      GROUP BY year
    )
    SELECT 
      year AS Year,
      banks_under_1k AS large_banks_under_1k,
      all_banks AS all_large_banks,
      loans_from_banks_under_1k AS loans_of_banks_under_1k,
      all_bank_loans AS all_large_bank_loans
    FROM bank_counts
    ORDER BY year
    """
    result = bq_client.query(sql)
    df = result.to_dataframe()
    # Rename columns to match requirements
    df.columns = ['Year', '# Large Banks <1 K loans', '# All large banks', 
                   '# loans of banks < 1k', '# all large bank loans']
    return df


def generate_table_5(bq_client, table_id):
    """Table 5: Business Revenue Analysis - Non-Credit Card Lending Only"""
    # Query original disclosure table and filter by credit card status
    disclosure_table = f"{bq_client.project_id}.sb.disclosure"
    sql = f"""
    WITH lender_avg_loan AS (
      SELECT 
        respondent_id,
        CAST(year AS INT64) AS year,
        SAFE_DIVIDE(
          SUM(COALESCE(amt_under_100k, 0) + COALESCE(amt_100k_250k, 0) + COALESCE(amt_250k_1m, 0)),
          NULLIF(SUM(COALESCE(num_under_100k, 0) + COALESCE(num_100k_250k, 0) + COALESCE(num_250k_1m, 0)), 0)
        ) AS avg_loan_amount_thousands
      FROM `{disclosure_table}`
      WHERE CAST(year AS INT64) IN (2018, 2019, 2020, 2021, 2022, 2023, 2024)
      GROUP BY respondent_id, CAST(year AS INT64)
    )
    SELECT 
      CAST(d.year AS INT64) AS Year,
      SUM(COALESCE(d.numsbrev_under_1m, 0)) AS loans_to_biz_under_1m,
      SUM(COALESCE(d.num_under_100k, 0) + 
          COALESCE(d.num_100k_250k, 0) + 
          COALESCE(d.num_250k_1m, 0) - 
          COALESCE(d.numsbrev_under_1m, 0)) AS loans_to_biz_over_1m
    FROM `{disclosure_table}` d
    INNER JOIN lender_avg_loan lavg
      ON d.respondent_id = lavg.respondent_id
      AND CAST(d.year AS INT64) = lavg.year
    WHERE CAST(d.year AS INT64) IN (2018, 2019, 2020, 2021, 2022, 2023, 2024)
      AND (lavg.avg_loan_amount_thousands IS NULL OR lavg.avg_loan_amount_thousands >= 10)
    GROUP BY CAST(d.year AS INT64)
    ORDER BY Year
    """
    result = bq_client.query(sql)
    df = result.to_dataframe()
    # Rename columns to match requirements
    df.columns = ['Year', '# loans to biz <$1 mill rev', '# loans to biz >$1 mil.']
    return df


def generate_table_6(bq_client, table_id):
    """Table 6: Combined Bank Size + Business Revenue - Non-Credit Card Lending Only"""
    # Query original disclosure table and filter by credit card status
    disclosure_table = f"{bq_client.project_id}.sb.disclosure"
    sql = f"""
    WITH lender_avg_loan AS (
      SELECT 
        respondent_id,
        CAST(year AS INT64) AS year,
        SAFE_DIVIDE(
          SUM(COALESCE(amt_under_100k, 0) + COALESCE(amt_100k_250k, 0) + COALESCE(amt_250k_1m, 0)),
          NULLIF(SUM(COALESCE(num_under_100k, 0) + COALESCE(num_100k_250k, 0) + COALESCE(num_250k_1m, 0)), 0)
        ) AS avg_loan_amount_thousands
      FROM `{disclosure_table}`
      WHERE CAST(year AS INT64) IN (2018, 2019, 2020, 2021, 2022, 2023, 2024)
      GROUP BY respondent_id, CAST(year AS INT64)
    ),
    lender_loans_by_year AS (
      SELECT 
        CAST(d.year AS INT64) AS year,
        d.respondent_id,
        SUM(COALESCE(d.num_under_100k, 0) + 
            COALESCE(d.num_100k_250k, 0) + 
            COALESCE(d.num_250k_1m, 0)) AS total_loans
      FROM `{disclosure_table}` d
      INNER JOIN lender_avg_loan lavg
        ON d.respondent_id = lavg.respondent_id
        AND CAST(d.year AS INT64) = lavg.year
      WHERE CAST(d.year AS INT64) IN (2018, 2019, 2020, 2021, 2022, 2023, 2024)
        AND (lavg.avg_loan_amount_thousands IS NULL OR lavg.avg_loan_amount_thousands >= 10)
      GROUP BY CAST(d.year AS INT64), d.respondent_id
    ),
    banks_over_1k AS (
      SELECT DISTINCT year, respondent_id
      FROM lender_loans_by_year
      WHERE total_loans >= 1000
    )
    SELECT 
      CAST(t.year AS INT64) AS Year,
      SUM(COALESCE(t.numsbrev_under_1m, 0)) AS loans_banks_over_1k_to_biz_under_1m,
      SUM(COALESCE(t.num_under_100k, 0) + 
          COALESCE(t.num_100k_250k, 0) + 
          COALESCE(t.num_250k_1m, 0) - 
          COALESCE(t.numsbrev_under_1m, 0)) AS loans_banks_over_1k_to_biz_over_1m
    FROM `{disclosure_table}` t
    INNER JOIN banks_over_1k b
      ON CAST(t.year AS INT64) = b.year 
      AND t.respondent_id = b.respondent_id
    INNER JOIN lender_avg_loan lavg
      ON t.respondent_id = lavg.respondent_id
      AND CAST(t.year AS INT64) = lavg.year
    WHERE CAST(t.year AS INT64) IN (2018, 2019, 2020, 2021, 2022, 2023, 2024)
      AND (lavg.avg_loan_amount_thousands IS NULL OR lavg.avg_loan_amount_thousands >= 10)
    GROUP BY CAST(t.year AS INT64)
    ORDER BY Year
    """
    result = bq_client.query(sql)
    df = result.to_dataframe()
    # Rename columns to match requirements
    df.columns = ['Year', '#loans banks > 1 K to biz <1 mil', '# loans banks > 1 K to biz >1 mil']
    return df


def main():
    print("=" * 80)
    print("GENERATING 1071 EXCEL TABLES")
    print("=" * 80)
    print()
    
    bq_client = BigQueryClient()
    table_id = f"{bq_client.project_id}.misc.1071_1k_lenders"
    
    print(f"Source table: {table_id}")
    print()
    
    # Generate all tables
    tables = {}
    
    print("Generating Table 1: Bank Size Analysis (All Lending)...")
    tables['Table 1'] = generate_table_1(bq_client, table_id)
    print(f"  ✓ {len(tables['Table 1'])} rows")
    
    print("Generating Table 2: Business Revenue Analysis (All Lending)...")
    tables['Table 2'] = generate_table_2(bq_client, table_id)
    print(f"  ✓ {len(tables['Table 2'])} rows")
    
    print("Generating Table 3: Combined Analysis (All Lending)...")
    tables['Table 3'] = generate_table_3(bq_client, table_id)
    print(f"  ✓ {len(tables['Table 3'])} rows")
    
    print("Generating Table 4: Bank Size Analysis (Non-Card Only)...")
    tables['Table 4'] = generate_table_4(bq_client, table_id)
    print(f"  ✓ {len(tables['Table 4'])} rows")
    
    print("Generating Table 5: Business Revenue Analysis (Non-Card Only)...")
    tables['Table 5'] = generate_table_5(bq_client, table_id)
    print(f"  ✓ {len(tables['Table 5'])} rows")
    
    print("Generating Table 6: Combined Analysis (Non-Card Only)...")
    tables['Table 6'] = generate_table_6(bq_client, table_id)
    print(f"  ✓ {len(tables['Table 6'])} rows")
    
    print()
    print("Creating Excel file...")
    
    # Create Excel file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_file = f"1071_Analysis_Tables_{timestamp}.xlsx"
    
    # Notes content
    notes_content = [
        ["1071 Analysis Tables - Notes"],
        [""],
        ["Data Source:"],
        ["- Source Table: sb.disclosure (original disclosure table, not 1071_1k_lenders)"],
        ["- Years: 2018-2024"],
        ["- All queries use original disclosure table to avoid duplication issues"],
        [""],
        ["Table Definitions:"],
        ["- Tables 1-3: All lending (card and non-card)"],
        ["- Tables 4-6: Non-credit card lending only (average loan amount >= $10,000 per year)"],
        [""],
        ["Key Definitions:"],
        ["- Large Banks: All banks/lenders in the disclosure table"],
        ["- Loan Counts: Sum of num_under_100k + num_100k_250k + num_250k_1m"],
        ["- Business Revenue: Uses numsbrev_under_1m field for <$1M, calculated for >$1M"],
        ["- Credit Card Lenders: Average loan amount < $10,000 per year"],
        [""],
        ["Table 1: Bank Size Analysis"],
        ["- Counts banks by loan volume threshold (<1K loans vs all banks)"],
        ["- Shows total loans from each category"],
        [""],
        ["Table 2: Business Revenue Analysis"],
        ["- Counts loans by business revenue size (<$1M vs >$1M)"],
        [""],
        ["Table 3: Combined Analysis"],
        ["- Loans from banks with >1,000 loans, by business revenue"],
        [""],
        ["Tables 4-6: Same as Tables 1-3 but filtered to non-credit card lenders only"],
        [""],
        ["Important:"],
        ["- All numbers represent LOAN COUNTS (number of loans), not loan amounts"],
        ["- Queries use original disclosure table to ensure accurate counts"],
        ["- Data aggregated at lender-year level to avoid duplication"],
    ]
    
    # Create Excel file with proper structure
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # Write data tables
        for sheet_name, df in tables.items():
            # Ensure sheet name is valid (max 31 chars, no invalid characters)
            safe_sheet_name = sheet_name[:31] if len(sheet_name) > 31 else sheet_name
            df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
            print(f"  ✓ Created sheet: {safe_sheet_name}")
        
        # Write Notes sheet
        notes_df = pd.DataFrame(notes_content)
        notes_df.to_excel(writer, sheet_name='Notes', index=False, header=False)
        print(f"  ✓ Created sheet: Notes")
    
    # Reopen and fix workbook structure to prevent repair messages
    wb = openpyxl.load_workbook(excel_file)
    # Ensure all sheets have proper structure
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        # Auto-adjust column widths for Notes sheet
        if sheet_name == 'Notes':
            for column in ws.columns:
                max_length = 0
                column_letter = get_column_letter(column[0].column)
                for cell in column:
                    try:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 100)
                ws.column_dimensions[column_letter].width = adjusted_width
    wb.save(excel_file)
    wb.close()
    
    print()
    print("=" * 80)
    print(f"✓ Excel file created: {excel_file}")
    print("=" * 80)
    print()
    print("Summary:")
    for sheet_name, df in tables.items():
        print(f"  {sheet_name}: {len(df)} rows, {len(df.columns)} columns")
    print("  Notes: Methodology and definitions")
    print()
    
    # Move to Downloads folder
    import shutil
    from pathlib import Path
    downloads_path = Path.home() / 'Downloads' / excel_file
    shutil.move(excel_file, downloads_path)
    print(f"✓ File moved to Downloads: {downloads_path}")
    print()


if __name__ == '__main__':
    main()

