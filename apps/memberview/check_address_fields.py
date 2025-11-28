#!/usr/bin/env python3
"""Check for address fields in HubSpot companies CSV."""
import pandas as pd
from pathlib import Path

csv_file = Path(r"C:\DREAM\HubSpot\data\raw\hubspot-crm-exports-all-companies-2025-11-14.csv")

print("=" * 80)
print("CHECKING HUBSPOT COMPANIES CSV FOR ADDRESS FIELDS")
print("=" * 80)

df = pd.read_csv(csv_file, nrows=100)

print(f"\nTotal columns: {len(df.columns)}")
print("\nALL COLUMN NAMES:")
for i, col in enumerate(df.columns, 1):
    print(f"  {i:2d}. {col}")

print("\n" + "=" * 80)
print("SEARCHING FOR ADDRESS-RELATED COLUMNS:")
print("=" * 80)

address_keywords = ['address', 'street', 'zip', 'postal', 'line', 'avenue', 'road', 'boulevard', 'drive', 'lane']
address_cols = []

for col in df.columns:
    col_lower = col.lower()
    for keyword in address_keywords:
        if keyword in col_lower:
            address_cols.append(col)
            break

if address_cols:
    print(f"\nFound {len(address_cols)} address-related columns:")
    for col in address_cols:
        non_null = df[col].notna().sum()
        print(f"  - {col}: {non_null}/{len(df)} non-null ({non_null/len(df)*100:.1f}%)")
        
        # Show sample values
        sample_values = df[col].dropna().head(3).tolist()
        if sample_values:
            print(f"    Sample values: {sample_values}")
else:
    print("\nNo address-related columns found with keywords:", address_keywords)

print("\n" + "=" * 80)
print("SAMPLE ROW DATA (first member with data):")
print("=" * 80)

# Find first row with membership status
members_df = df[df['Membership Status'].notna()].head(1)
if len(members_df) > 0:
    row = members_df.iloc[0]
    print("\nFull row data:")
    for col in df.columns:
        val = row[col]
        if pd.notna(val) and str(val).strip():
            print(f"  {col}: {val}")

