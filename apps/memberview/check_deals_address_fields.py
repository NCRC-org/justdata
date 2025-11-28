#!/usr/bin/env python3
"""Check for address fields in HubSpot deals data."""
import pandas as pd
from pathlib import Path

deals_file = Path(r"C:\DREAM\HubSpot\data\processed\20251114_123117_all-deals_processed.parquet")

print("=" * 80)
print("CHECKING HUBSPOT DEALS DATA FOR ADDRESS FIELDS")
print("=" * 80)

df = pd.read_parquet(deals_file)

print(f"\nTotal columns: {len(df.columns)}")

# Search for address-related columns
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
    for col in address_cols[:20]:  # Show first 20
        non_null = df[col].notna().sum()
        print(f"  - {col}: {non_null}/{len(df)} non-null ({non_null/len(df)*100:.1f}%)")
        
        # Show sample values
        sample_values = df[col].dropna().head(2).tolist()
        if sample_values:
            print(f"    Sample: {sample_values}")
else:
    print("\nNo address-related columns found in deals table")

# Also check company-related address fields
print("\n" + "=" * 80)
print("COMPANY-RELATED ADDRESS FIELDS IN DEALS:")
print("=" * 80)

company_address_cols = [col for col in df.columns if 'company' in col.lower() and any(kw in col.lower() for kw in address_keywords)]
if company_address_cols:
    for col in company_address_cols:
        non_null = df[col].notna().sum()
        print(f"  - {col}: {non_null}/{len(df)} non-null ({non_null/len(df)*100:.1f}%)")
else:
    print("No company address fields found in deals table")

