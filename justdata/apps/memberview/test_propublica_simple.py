"""
Simple test of ProPublica API with 10 HubSpot companies.
Run this from the MemberView_Standalone directory.
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
print("PROPUBLICA API MATCHING TEST - 10 COMPANIES")
print("Testing HubSpot companies against IRS Form 990 data")
print("NOTE: Many companies may be for-profit (no Form 990)")
print("=" * 80)
print(f"\nLoading: {companies_file.name}")

# Load companies
df = pd.read_csv(companies_file, low_memory=False)
print(f"Total companies: {len(df):,}")

# Get 10 sample companies with membership status
if 'Membership Status' in df.columns:
    df_members = df[df['Membership Status'].notna()].copy()
    print(f"Companies with membership status: {len(df_members):,}")
    df_sample = df_members.head(10).copy()
else:
    df_sample = df.head(10).copy()
    print("WARNING: No 'Membership Status' column - using all companies")

print(f"\nTesting {len(df_sample)} companies")

# Analyze schema - find which fields are populated
print("\n" + "=" * 80)
print("SCHEMA ANALYSIS - Field Population")
print("=" * 80)

column_stats = []
for col in df_sample.columns:
    non_null = df_sample[col].notna().sum()
    pct = (non_null / len(df_sample)) * 100
    column_stats.append((col, non_null, pct))

# Sort by population
column_stats.sort(key=lambda x: x[2], reverse=True)

print("\nColumn population (for sample):")
for col, count, pct in column_stats:
    if pct > 0:
        print(f"  {col:<50} | {count:>2}/{len(df_sample)} ({pct:>5.1f}%)")

# Find address fields - prioritize well-populated ones
name_col = 'Company name' if 'Company name' in df_sample.columns else df_sample.columns[0]
city_col = None
state_col = None

# Find best populated city/state fields
for col, count, pct in column_stats:
    col_lower = col.lower()
    if 'city' in col_lower and city_col is None and pct > 0:
        city_col = col
    if 'state' in col_lower and 'status' not in col_lower and state_col is None and pct > 0:
        state_col = col

print(f"\nSelected fields for matching:")
print(f"  Name: {name_col}")
print(f"  City: {city_col if city_col else 'NOT FOUND'}")
print(f"  State: {state_col if state_col else 'NOT FOUND'}")

# Initialize client
client = ProPublicaClient(rate_limit_delay=0.6)

print("\n" + "=" * 80)
print("MATCHING RESULTS")
print("=" * 80)

results = []

for idx, row in df_sample.iterrows():
    name = str(row[name_col]) if pd.notna(row.get(name_col)) else None
    city = str(row[city_col]) if city_col and pd.notna(row.get(city_col)) else None
    state = str(row[state_col]) if state_col and pd.notna(row.get(state_col)) else None
    
    if not name or name == 'nan':
        print(f"\n[{idx+1}] SKIP: No name")
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
            
            print(f"     MATCH: {org_name}")
            print(f"     EIN: {ein}")
            print(f"     Location: {org_city}, {org_state}")
            
            # Get financials
            if ein and ein != 'N/A':
                financials = client.get_organization_financials(ein)
                if financials:
                    rev = financials.get('total_revenue')
                    exp = financials.get('total_expenses')
                    if rev:
                        print(f"     Revenue: ${rev:,}")
                    if exp:
                        print(f"     Expenses: ${exp:,}")
            
            results.append({'name': name, 'matched': True, 'ein': ein})
        else:
            print(f"     NO MATCH (may be for-profit or name mismatch)")
            results.append({'name': name, 'matched': False})
    
    except Exception as e:
        print(f"     ERROR: {e}")
        results.append({'name': name, 'matched': False, 'error': str(e)})

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
matched = sum(1 for r in results if r.get('matched'))
total = len(results)
match_rate = (matched/total*100) if total > 0 else 0

print(f"\nTotal tested: {total}")
print(f"Matches found: {matched}")
print(f"Match rate: {match_rate:.1f}%")
print(f"\nNote: Low match rate is expected because:")
print(f"  - Many NCRC members are for-profit businesses (no Form 990)")
print(f"  - Only nonprofits file Form 990 with IRS")
print(f"  - Name variations may cause misses")

if matched > 0:
    print(f"\nSuccessful matches:")
    for r in results:
        if r.get('matched'):
            print(f"  - {r.get('name', 'N/A')[:60]}")
            if r.get('ein'):
                print(f"    EIN: {r.get('ein')}")

if __name__ == "__main__":
    pass

