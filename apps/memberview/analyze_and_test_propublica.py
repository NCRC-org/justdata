"""
Analyze companies schema and test ProPublica API matching.
Shows which fields are populated and tests 10 companies.
"""

import sys
from pathlib import Path
import pandas as pd

# Add utils to path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from utils.propublica_client import ProPublicaClient

# Find companies file
companies_paths = [
    BASE_DIR.parent.parent / "HubSpot" / "data" / "raw" / "hubspot-crm-exports-all-companies-2025-11-14.csv",
    Path("C:/DREAM/HubSpot/data/raw/hubspot-crm-exports-all-companies-2025-11-14.csv"),
    Path("../HubSpot/data/raw/hubspot-crm-exports-all-companies-2025-11-14.csv"),
]

companies_file = None
for p in companies_paths:
    if p.exists():
        companies_file = p
        break

if not companies_file:
    print("ERROR: Companies file not found")
    sys.exit(1)

print("=" * 80)
print("COMPANIES SCHEMA ANALYSIS & PROPUBLICA TEST")
print("=" * 80)
print(f"\nLoading: {companies_file.name}")

# Load full companies dataset
df = pd.read_csv(companies_file, low_memory=False)
print(f"Total companies: {len(df):,}")

# Filter to members
if 'Membership Status' in df.columns:
    df_members = df[df['Membership Status'].notna()].copy()
    print(f"Companies with membership status: {len(df_members):,}")
else:
    df_members = df.copy()
    print("WARNING: No 'Membership Status' column")

# Analyze schema for members
print("\n" + "=" * 80)
print("SCHEMA ANALYSIS - Field Population for Members")
print("=" * 80)

column_stats = []
for col in df_members.columns:
    non_null = df_members[col].notna().sum()
    pct = (non_null / len(df_members)) * 100
    column_stats.append((col, non_null, pct))

# Sort by population
column_stats.sort(key=lambda x: x[2], reverse=True)

print("\nAll columns (sorted by population %):")
print(f"{'Column Name':<50} | {'Populated':<10} | {'%':<6}")
print("-" * 70)

for col, count, pct in column_stats:
    if pct > 0:  # Only show populated columns
        print(f"{col:<50} | {count:>8,} | {pct:>5.1f}%")

# Identify key fields
print("\n" + "=" * 80)
print("KEY FIELDS FOR PROPUBLICA MATCHING")
print("=" * 80)

name_col = None
city_col = None
state_col = None

for col, count, pct in column_stats:
    col_lower = col.lower()
    
    if 'company' in col_lower and 'name' in col_lower and not name_col:
        name_col = col
        print(f"\nCompany Name: {col}")
        print(f"  Population: {count:,} ({pct:.1f}%)")
    
    if 'city' in col_lower and not city_col:
        city_col = col
        print(f"\nCity: {col}")
        print(f"  Population: {count:,} ({pct:.1f}%)")
    
    if 'state' in col_lower and 'status' not in col_lower and not state_col:
        state_col = col
        print(f"\nState: {col}")
        print(f"  Population: {count:,} ({pct:.1f}%)")

if not name_col:
    name_col = df_members.columns[0]
    print(f"\nCompany Name: {name_col} (using first column)")

# Get 10 sample companies
df_sample = df_members.head(10).copy()

print("\n" + "=" * 80)
print("PROPUBLICA API MATCHING TEST")
print("Testing 10 companies (many may be for-profit - no Form 990)")
print("=" * 80)

# Initialize client
client = ProPublicaClient(rate_limit_delay=0.6)

results = []

for idx, row in df_sample.iterrows():
    name = str(row[name_col]) if pd.notna(row.get(name_col)) else None
    city = str(row[city_col]) if city_col and pd.notna(row.get(city_col)) else None
    state = str(row[state_col]) if state_col and pd.notna(row.get(state_col)) else None
    
    if not name or name == 'nan':
        print(f"\n[{idx+1}] SKIP: No company name")
        continue
    
    print(f"\n[{idx+1}] {name}")
    if city:
        print(f"     City: {city}")
    if state:
        print(f"     State: {state}")
    
    try:
        org = client.find_organization_by_name(name, state=state, city=city)
        
        if org:
            ein = org.get('ein', 'N/A')
            org_name = org.get('name', 'N/A')
            org_city = org.get('city', 'N/A')
            org_state = org.get('state', 'N/A')
            
            print(f"     MATCH FOUND!")
            print(f"        Matched Name: {org_name}")
            print(f"        EIN: {ein}")
            print(f"        Location: {org_city}, {org_state}")
            
            # Get financials
            if ein and ein != 'N/A':
                financials = client.get_organization_financials(ein)
                if financials:
                    rev = financials.get('total_revenue')
                    exp = financials.get('total_expenses')
                    if rev:
                        print(f"        Revenue: ${rev:,}")
                    if exp:
                        print(f"        Expenses: ${exp:,}")
            
            results.append({
                'name': name,
                'matched': True,
                'ein': ein,
                'matched_name': org_name
            })
        else:
            print(f"     NO MATCH")
            print(f"        (May be for-profit business or name mismatch)")
            results.append({
                'name': name,
                'matched': False
            })
    
    except Exception as e:
        print(f"     ERROR: {e}")
        results.append({
            'name': name,
            'matched': False,
            'error': str(e)
        })

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

matched = sum(1 for r in results if r.get('matched'))
total = len(results)
match_rate = (matched/total*100) if total > 0 else 0

print(f"\nTotal tested: {total}")
print(f"Matches found: {matched}")
print(f"Match rate: {match_rate:.1f}%")

print(f"\nNote: Low match rate is expected because:")
print(f"  - Many NCRC members are FOR-PROFIT businesses")
print(f"  - Only NONPROFITS file Form 990 with IRS")
print(f"  - For-profit companies won't appear in ProPublica database")

if matched > 0:
    print(f"\nSuccessful matches (nonprofits found):")
    for r in results:
        if r.get('matched'):
            print(f"  - {r.get('name', 'N/A')[:60]}")
            print(f"    EIN: {r.get('ein', 'N/A')}")
            print(f"    Matched as: {r.get('matched_name', 'N/A')}")

non_matches = [r for r in results if not r.get('matched')]
if non_matches:
    print(f"\nNon-matches ({len(non_matches)} companies):")
    print(f"  (These are likely for-profit businesses)")
    for r in non_matches[:5]:  # Show first 5
        print(f"  - {r.get('name', 'N/A')[:60]}")

print("\n" + "=" * 80)
print("SCHEMA SUMMARY")
print("=" * 80)
print(f"\nWell-populated fields (>50%):")
for col, count, pct in column_stats:
    if pct > 50:
        print(f"  {col:<50} | {pct:>5.1f}%")

if __name__ == "__main__":
    pass

