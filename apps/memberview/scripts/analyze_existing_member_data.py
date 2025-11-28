"""Analyze existing HubSpot member data to inform enrichment searches."""
import pandas as pd
from pathlib import Path

csv_file = Path(r"C:\DREAM\HubSpot\data\raw\hubspot-crm-exports-all-companies-2025-11-14.csv")

print("=" * 80)
print("ANALYZING EXISTING HUBSPOT MEMBER DATA")
print("=" * 80)

df = pd.read_csv(csv_file, low_memory=False)
members = df[df['Membership Status'].notna()].copy()

print(f"\nTotal members: {len(members)}")
print(f"Total companies: {len(df)}")

print("\n" + "=" * 80)
print("DATA AVAILABILITY FOR MEMBERS")
print("=" * 80)

# Check each field
fields_to_check = [
    'Company name',
    'City',
    'State/Region',
    'County',
    'Phone Number',
    'Country/Region',
    'Industry'
]

for field in fields_to_check:
    if field in members.columns:
        count = members[field].notna().sum()
        pct = count / len(members) * 100
        print(f"  {field:20s}: {count:4d} ({pct:5.1f}%)")

# Check for website field (might be named differently)
website_cols = [col for col in members.columns if 'website' in col.lower() or 'domain' in col.lower() or 'url' in col.lower()]
if website_cols:
    print("\nWebsite-related columns found:")
    for col in website_cols:
        count = members[col].notna().sum()
        pct = count / len(members) * 100
        print(f"  {col:20s}: {count:4d} ({pct:5.1f}%)")
else:
    print("\nNo website column found in data")

print("\n" + "=" * 80)
print("SAMPLE MEMBER RECORDS WITH DATA")
print("=" * 80)

# Show 5 sample members with good data
samples = members[members['Company name'].notna()].head(5)
for idx, row in samples.iterrows():
    print(f"\nMember {idx}:")
    print(f"  Name: {row.get('Company name', 'N/A')}")
    print(f"  Status: {row.get('Membership Status', 'N/A')}")
    print(f"  City: {row.get('City', 'N/A')}")
    print(f"  State: {row.get('State/Region', 'N/A')}")
    print(f"  County: {row.get('County', 'N/A')}")
    print(f"  Phone: {row.get('Phone Number', 'N/A')}")
    print(f"  Industry: {row.get('Industry', 'N/A')}")

print("\n" + "=" * 80)
print("SEARCH STRATEGY RECOMMENDATIONS")
print("=" * 80)

name_available = members['Company name'].notna().sum()
city_available = members['City'].notna().sum()
state_available = members['State/Region'].notna().sum()
county_available = members['County'].notna().sum()

print(f"\nFor website searches, we can use:")
print(f"  - Company name: {name_available}/{len(members)} ({name_available/len(members)*100:.1f}%) - ALWAYS AVAILABLE")
print(f"  - City: {city_available}/{len(members)} ({city_available/len(members)*100:.1f}%) - USEFUL")
print(f"  - State: {state_available}/{len(members)} ({state_available/len(members)*100:.1f}%) - USEFUL")
print(f"  - County: {county_available}/{len(members)} ({county_available/len(members)*100:.1f}%) - FALLBACK")

print(f"\nSearch query priority:")
print(f"  1. If city+state available ({min(city_available, state_available)} members): '{{name}} {{city}} {{state}} official website'")
print(f"  2. If only state available ({state_available - min(city_available, state_available)} members): '{{name}} {{state}} official website'")
print(f"  3. If only name available ({len(members) - state_available} members): '{{name}} official website'")




