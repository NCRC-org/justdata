"""
Process HUD Low-Mod Summary Data Excel file.
Reads the Excel file, creates GEOID5 codes, aggregates by county, and calculates income distributions.
"""

import pandas as pd
from pathlib import Path
import json
import sys

# Paths
hud_source = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\ACS-2020-Low-Mod-Local-Gov-All.xlsx")
data_dir = Path(__file__).parent / "data" / "hud"
data_dir.mkdir(parents=True, exist_ok=True)

print(f"Reading HUD file: {hud_source}")
print(f"File exists: {hud_source.exists()}")

if not hud_source.exists():
    print("ERROR: HUD file not found!")
    sys.exit(1)

# Read the Excel file
print("\nReading Excel file...")
df = pd.read_excel(hud_source)

print(f"\nTotal rows: {len(df):,}")
print(f"\nColumns ({len(df.columns)}):")
for i, col in enumerate(df.columns, 1):
    print(f"  {i:2d}. {col}")

# Display first few rows
print("\n" + "="*80)
print("FIRST 3 ROWS:")
print("="*80)
print(df.head(3).to_string())

# Look for state and county FIPS columns
print("\n" + "="*80)
print("SEARCHING FOR STATE/COUNTY COLUMNS:")
print("="*80)

# Common column name patterns
state_patterns = ['state', 'fips', 'st']
county_patterns = ['county', 'fips', 'co']

state_col = None
county_col = None

for col in df.columns:
    col_lower = str(col).lower()
    if any(pattern in col_lower for pattern in state_patterns) and 'state' in col_lower:
        if state_col is None:
            state_col = col
            print(f"Found state column: {col}")
    if any(pattern in col_lower for pattern in county_patterns) and 'county' in col_lower:
        if county_col is None:
            county_col = col
            print(f"Found county column: {col}")

# If not found by name, try to identify by data type and values
if state_col is None or county_col is None:
    print("\nTrying to identify columns by data type...")
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    for col in numeric_cols[:10]:  # Check first 10 numeric columns
        unique_vals = df[col].dropna().unique()[:5]
        print(f"  {col}: sample values = {unique_vals}")

print("\n" + "="*80)
print("Please review the output above to identify:")
print("  1. State FIPS code column")
print("  2. County FIPS code column")
print("  3. Population/household count columns")
print("  4. Income bracket columns")
print("="*80)

