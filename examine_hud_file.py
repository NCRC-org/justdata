"""
Examine HUD Low-Mod Summary Data Excel file structure.
Run this script to understand the file format before implementing the full processor.
"""

import pandas as pd
from pathlib import Path
import sys

hud_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\ACS-2020-Low-Mod-Local-Gov-All.xlsx")

if not hud_file.exists():
    print(f"ERROR: File not found: {hud_file}")
    sys.exit(1)

print(f"Reading HUD file: {hud_file}")
print("="*80)

# Read first 100 rows to understand structure
df = pd.read_excel(hud_file, nrows=100)

print(f"\nTotal columns: {len(df.columns)}")
print(f"Sample rows loaded: {len(df)}")
print("\n" + "="*80)
print("ALL COLUMNS:")
print("="*80)
for i, col in enumerate(df.columns, 1):
    print(f"{i:3d}. {col}")

print("\n" + "="*80)
print("FIRST 3 ROWS (all columns):")
print("="*80)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 50)
print(df.head(3))

print("\n" + "="*80)
print("COLUMN DATA TYPES:")
print("="*80)
print(df.dtypes)

# Look for key columns
print("\n" + "="*80)
print("SEARCHING FOR KEY COLUMNS:")
print("="*80)

# State/County FIPS
state_cols = [col for col in df.columns if any(term in str(col).lower() for term in ['state', 'st']) and 'fips' in str(col).lower()]
county_cols = [col for col in df.columns if any(term in str(col).lower() for term in ['county', 'co']) and 'fips' in str(col).lower()]

print(f"\nPotential State FIPS columns: {state_cols}")
print(f"Potential County FIPS columns: {county_cols}")

# Population columns
pop_cols = [col for col in df.columns if any(term in str(col).lower() for term in ['pop', 'population', 'persons', 'people'])]
print(f"\nPotential Population columns: {pop_cols}")

# Income-related columns
income_cols = [col for col in df.columns if any(term in str(col).lower() for term in ['income', 'low', 'mod', 'moderate', 'middle', 'upper', 'high', '80%', 'ami'])]
print(f"\nPotential Income columns: {income_cols}")

# Show sample values for key columns
if state_cols:
    print(f"\nSample values from {state_cols[0]}:")
    print(df[state_cols[0]].head(10).tolist())

if county_cols:
    print(f"\nSample values from {county_cols[0]}:")
    print(df[county_cols[0]].head(10).tolist())

print("\n" + "="*80)
print("NEXT STEPS:")
print("="*80)
print("1. Identify the exact column names for:")
print("   - State FIPS code")
print("   - County FIPS code")
print("   - Total population/households")
print("   - Low income (<50% AMI)")
print("   - Moderate income (50-80% AMI)")
print("   - Middle income (80-120% AMI)")
print("   - Upper income (>120% AMI)")
print("\n2. Update hud_data_processor.py with correct column names")
print("3. Run the processor to create county-level aggregated data")

