#!/usr/bin/env python3
"""
Check the latest report totals against Tableau figures.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shared.utils.progress_tracker import analysis_results_store, get_analysis_result
import pandas as pd

# Job ID from the latest logs
job_id = "87971692-d5d2-4b65-8493-86b2f6d2008a"

# Expected Tableau totals for Manufacturers and Traders Trust
expected_totals = {
    2022: 25130,
    2023: 16835,
    2024: 19791
}

print("=" * 80)
print("CHECKING REPORT TOTALS AGAINST TABLEAU")
print("=" * 80)
print(f"Job ID: {job_id}")
print()

# Get the report
result = get_analysis_result(job_id)

if not result:
    print("ERROR: Report not found!")
    print(f"Available reports: {list(analysis_results_store.keys())}")
    sys.exit(1)

print("REPORT FOUND")
print()

# Get metadata
metadata = result.get('metadata', {})
lender_info = metadata.get('lender_info', {})

print("LENDER INFORMATION:")
print(f"  Name: {lender_info.get('name', 'N/A')}")
print(f"  LEI: {lender_info.get('lei', 'N/A')}")
print()

# Check all_metros_data (national totals)
all_metros_data = result.get('all_metros_data', [])
if all_metros_data:
    print(f"ALL METROS DATA: {len(all_metros_data)} rows")
    
    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(all_metros_data)
    
    # Sum by year
    if 'year' in df.columns and 'total_originations' in df.columns:
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        df['total_originations'] = pd.to_numeric(df['total_originations'], errors='coerce').fillna(0)
        
        year_totals = df.groupby('year')['total_originations'].sum().to_dict()
        
        print("\nNATIONAL TOTALS (from all_metros_data):")
        print("-" * 60)
        all_match = True
        for year in sorted(year_totals.keys()):
            actual = int(year_totals[year])
            expected = expected_totals.get(int(year), 0)
            match = "✓" if actual == expected else "✗"
            diff = actual - expected
            print(f"  {year}: {actual:,} (Expected: {expected:,}, Diff: {diff:+,}) {match}")
            if actual != expected:
                all_match = False
        
        if all_match:
            print("\n✓ ALL NATIONAL TOTALS MATCH TABLEAU!")
        else:
            print("\n✗ SOME NATIONAL TOTALS DO NOT MATCH TABLEAU")
        
        # Also check by loan purpose
        if 'loan_purpose' in df.columns:
            print("\nNATIONAL TOTALS BY LOAN PURPOSE:")
            print("-" * 60)
            purpose_map = {
                '1': 'Purchase',
                '31': 'Refinance',
                '32': 'Refinance',
                '2': 'Equity',
                '4': 'Equity'
            }
            
            for year in sorted(year_totals.keys()):
                year_df = df[df['year'] == year]
                print(f"\n  Year {year}:")
                for purpose_code, purpose_name in purpose_map.items():
                    purpose_df = year_df[year_df['loan_purpose'] == purpose_code]
                    if not purpose_df.empty:
                        total = int(purpose_df['total_originations'].sum())
                        print(f"    {purpose_name}: {total:,}")
    else:
        print("  WARNING: Missing 'year' or 'total_originations' columns")
        print(f"  Columns: {list(df.columns)}")
else:
    print("WARNING: No all_metros_data found!")

# Check Section 1 Table 1 data
report_data = result.get('report_data', {})
if 'loan_purpose_over_time' in report_data:
    print("\n" + "=" * 80)
    print("SECTION 1 TABLE 1 DATA (from loan_purpose_over_time):")
    print("-" * 60)
    
    table1_data = report_data['loan_purpose_over_time']
    if isinstance(table1_data, list):
        year_totals_table1 = {}
        for row in table1_data:
            year = row.get('year')
            if year:
                year_totals_table1[year] = (
                    row.get('Home Purchase', 0) + 
                    row.get('Refinance', 0) + 
                    row.get('Home Equity', 0)
                )
        
        for year in sorted(year_totals_table1.keys()):
            actual = int(year_totals_table1[year])
            expected = expected_totals.get(int(year), 0)
            match = "✓" if actual == expected else "✗"
            diff = actual - expected
            print(f"  {year}: {actual:,} (Expected: {expected:,}, Diff: {diff:+,}) {match}")

# Check CBSA totals if available
if all_metros_data:
    print("\n" + "=" * 80)
    print("TOP CBSAs (checking first 10):")
    print("-" * 60)
    
    df = pd.DataFrame(all_metros_data)
    
    # Try to get CBSA info
    if 'geoid5' in df.columns:
        # Group by county and sum
        county_totals = df.groupby('geoid5')['total_originations'].sum().sort_values(ascending=False)
        print(f"  Total unique counties: {len(county_totals)}")
        print(f"  Top 10 counties by loan volume:")
        for i, (geoid5, total) in enumerate(county_totals.head(10).items(), 1):
            print(f"    {i}. GEOID {geoid5}: {int(total):,} loans")

print("\n" + "=" * 80)
print("CHECK COMPLETE")
print("=" * 80)

