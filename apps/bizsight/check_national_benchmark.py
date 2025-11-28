#!/usr/bin/env python3
"""Check if national benchmark has income category data."""

import json
from pathlib import Path

national_file = Path(__file__).parent.parent / 'data' / 'national.json'

if not national_file.exists():
    print(f"ERROR: {national_file} does not exist!")
    exit(1)

with open(national_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 80)
print("NATIONAL BENCHMARK FILE CHECK")
print("=" * 80)
print(f"\nFile: {national_file}")
print(f"Total keys: {len(data)}")
print(f"\nAll keys:")
for key in sorted(data.keys()):
    print(f"  - {key}")

print("\n" + "=" * 80)
print("INCOME CATEGORY FIELDS CHECK")
print("=" * 80)

income_fields = [
    'pct_loans_low_income',
    'pct_loans_moderate_income',
    'pct_loans_middle_income',
    'pct_loans_upper_income',
    'pct_amount_low_income',
    'pct_amount_moderate_income',
    'pct_amount_middle_income',
    'pct_amount_upper_income',
    'low_income_loans',
    'moderate_income_loans',
    'middle_income_loans',
    'upper_income_loans',
    'low_income_amount',
    'moderate_income_amount',
    'middle_income_amount',
    'upper_income_amount'
]

missing = []
present = []

for field in income_fields:
    if field in data:
        present.append(field)
        print(f"✓ {field}: {data[field]}")
    else:
        missing.append(field)
        print(f"✗ {field}: MISSING")

print("\n" + "=" * 80)
if missing:
    print(f"ERROR: {len(missing)} income category fields are MISSING!")
    print("Missing fields:", missing)
else:
    print("SUCCESS: All income category fields are present!")
print("=" * 80)

