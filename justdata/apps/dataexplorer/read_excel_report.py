#!/usr/bin/env python3
"""
Read the Excel report file to inspect the data.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    import pandas as pd
except ImportError:
    print("pandas not installed. Install with: pip install pandas openpyxl")
    sys.exit(1)

# Excel file path from user
excel_path = r"C:\Users\jrichardson\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\Lender_Analysis_MANUFACTURERS_AND_TRADERS_TRUST_2022-2024_2025-12-22 (1).xlsx"

if not os.path.exists(excel_path):
    print(f"File not found: {excel_path}")
    print("\nPlease provide the correct path to the Excel file.")
    sys.exit(1)

print(f"Reading Excel file: {excel_path}")
print("=" * 80)

try:
    # Read all sheets
    excel_file = pd.ExcelFile(excel_path)
    print(f"\nSheets found: {excel_file.sheet_names}")
    print()
    
    # Look for Section 1 Table 1 (likely in first sheet or named sheet)
    for sheet_name in excel_file.sheet_names:
        print(f"\n{'='*80}")
        print(f"SHEET: {sheet_name}")
        print(f"{'='*80}")
        
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
        print(f"\nColumns: {list(df.columns)}")
        print(f"\nFirst 10 rows:")
        try:
            print(df.head(10).to_string())
        except UnicodeEncodeError:
            # Handle Unicode characters for Windows console
            print(df.head(10).to_string().encode('ascii', 'ignore').decode('ascii'))
        
        # Look for year and total columns
        if 'Year' in df.columns or 'year' in df.columns:
            year_col = 'Year' if 'Year' in df.columns else 'year'
            if 'Total' in df.columns or 'total_originations' in df.columns:
                total_col = 'Total' if 'Total' in df.columns else 'total_originations'
                print(f"\n{'-'*80}")
                print("YEAR TOTALS:")
                print(f"{'-'*80}")
                for _, row in df.iterrows():
                    year = row.get(year_col)
                    total = row.get(total_col)
                    if pd.notna(year) and pd.notna(total):
                        print(f"  {year}: {total:,.0f}")
        
        # For S1-Loan Purpose sheet, calculate totals
        if sheet_name == 'S1-Loan Purpose':
            print(f"\n{'-'*80}")
            print("CALCULATED TOTALS (sum of all loan purposes):")
            print(f"{'-'*80}")
            for _, row in df.iterrows():
                year = row.get('year')
                equity = row.get('Home Equity', 0) or 0
                purchase = row.get('Home Purchase', 0) or 0
                refinance = row.get('Refinance', 0) or 0
                total = equity + purchase + refinance
                if pd.notna(year):
                    print(f"  {year}: {total:,} (Equity: {equity:,}, Purchase: {purchase:,}, Refinance: {refinance:,})")
            print(f"\nEXPECTED TOTALS (from Tableau):")
            print(f"  2022: 25,130")
            print(f"  2023: 16,835")
            print(f"  2024: 19,791")
            print(f"\nDISCREPANCY:")
            for _, row in df.iterrows():
                year = row.get('year')
                equity = row.get('Home Equity', 0) or 0
                purchase = row.get('Home Purchase', 0) or 0
                refinance = row.get('Refinance', 0) or 0
                total = equity + purchase + refinance
                if pd.notna(year):
                    expected = {'2022': 25130, '2023': 16835, '2024': 19791}.get(str(year), 0)
                    diff = expected - total
                    pct = (diff / expected * 100) if expected > 0 else 0
                    print(f"  {year}: Missing {diff:,} loans ({pct:.1f}% of expected)")
        
        print()
    
except Exception as e:
    print(f"Error reading Excel file: {e}")
    import traceback
    traceback.print_exc()

