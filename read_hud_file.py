import pandas as pd
from pathlib import Path
import sys

# Read the HUD Excel file
hud_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\ACS-2020-Low-Mod-Local-Gov-All.xlsx")

print(f"Reading HUD file: {hud_file}")
print(f"File exists: {hud_file.exists()}")

if not hud_file.exists():
    print("File not found!")
    sys.exit(1)

# Read first few rows to understand structure
df = pd.read_excel(hud_file, nrows=10)

print("\n" + "="*80)
print("COLUMNS:")
print("="*80)
for i, col in enumerate(df.columns):
    print(f"{i+1:2d}. {col}")

print("\n" + "="*80)
print("FIRST 5 ROWS:")
print("="*80)
print(df.head().to_string())

print("\n" + "="*80)
print("DATA TYPES:")
print("="*80)
print(df.dtypes)

# Check for state and county code columns
state_cols = [col for col in df.columns if 'state' in col.lower() or 'fips' in col.lower()]
county_cols = [col for col in df.columns if 'county' in col.lower() or 'fips' in col.lower()]

print("\n" + "="*80)
print("POTENTIAL STATE/COUNTY COLUMNS:")
print("="*80)
print(f"State columns: {state_cols}")
print(f"County columns: {county_cols}")

