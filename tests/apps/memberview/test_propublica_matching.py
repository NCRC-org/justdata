"""
Test ProPublica API matching with HubSpot company data.
Tests matching 10 companies using name, city, and state.
"""

import sys
from pathlib import Path
import pandas as pd

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from justdata.apps.memberview.utils.propublica_client import ProPublicaClient

def load_sample_companies(n=10):
    """Load sample companies from HubSpot data."""
    # Try to find companies file
    hubspot_data_paths = [
        PROJECT_ROOT / "HubSpot" / "data" / "raw" / "hubspot-crm-exports-all-companies-2025-11-14.csv",
        Path("C:/DREAM/HubSpot/data/raw/hubspot-crm-exports-all-companies-2025-11-14.csv"),
        Path("../HubSpot/data/raw/hubspot-crm-exports-all-companies-2025-11-14.csv"),
    ]
    
    companies_file = None
    for path in hubspot_data_paths:
        if path.exists():
            companies_file = path
            break
    
    if not companies_file:
        print("ERROR: Companies file not found. Tried:")
        for path in hubspot_data_paths:
            print(f"  - {path}")
        return None
    
    print(f"Loading companies from: {companies_file}")
    df = pd.read_csv(companies_file, low_memory=False)
    
    print(f"Total companies: {len(df):,}")
    
    # Filter to companies with membership status
    if 'Membership Status' in df.columns:
        df_members = df[df['Membership Status'].notna()].copy()
        print(f"Companies with membership status: {len(df_members):,}")
    else:
        df_members = df.copy()
    
    # Get sample - prioritize companies with city/state if available
    # Check what address fields exist
    address_fields = {
        'city': [c for c in df_members.columns if 'city' in c.lower()],
        'state': [c for c in df_members.columns if 'state' in c.lower() and 'status' not in c.lower()],
        'name': [c for c in df_members.columns if 'company' in c.lower() and 'name' in c.lower()],
    }
    
    print(f"\nAvailable fields:")
    for field_type, fields in address_fields.items():
        if fields:
            print(f"  {field_type}: {fields[0]}")
    
    # Get sample companies
    sample = df_members.head(n).copy()
    
    return sample, address_fields

def test_propublica_matching():
    """Test ProPublica API matching with sample companies."""
    print("=" * 80)
    print("PROPUBLICA API MATCHING TEST")
    print("Testing 10 HubSpot companies against IRS Form 990 data")
    print("=" * 80)
    
    # Load sample companies
    result = load_sample_companies(10)
    if not result:
        return
    
    sample_companies, address_fields = result
    
    # Initialize ProPublica client
    client = ProPublicaClient(rate_limit_delay=0.5)
    
    # Get field names
    name_col = address_fields['name'][0] if address_fields['name'] else 'Company name'
    city_col = address_fields['city'][0] if address_fields['city'] else None
    state_col = address_fields['state'][0] if address_fields['state'] else None
    
    print(f"\nUsing fields:")
    print(f"  Name: {name_col}")
    print(f"  City: {city_col if city_col else 'NOT AVAILABLE'}")
    print(f"  State: {state_col if state_col else 'NOT AVAILABLE'}")
    
    print("\n" + "=" * 80)
    print("MATCHING RESULTS")
    print("=" * 80)
    
    results = []
    
    for idx, company in sample_companies.iterrows():
        company_name = str(company[name_col]) if pd.notna(company.get(name_col)) else None
        city = str(company[city_col]) if city_col and pd.notna(company.get(city_col)) else None
        state = str(company[state_col]) if state_col and pd.notna(company.get(state_col)) else None
        
        if not company_name or company_name == 'nan':
            print(f"\n[{idx+1}] SKIPPED: No company name")
            results.append({
                'company_name': 'N/A',
                'city': city,
                'state': state,
                'match_found': False,
                'reason': 'No company name'
            })
            continue
        
        print(f"\n[{idx+1}] Searching: {company_name}")
        if city:
            print(f"     City: {city}")
        if state:
            print(f"     State: {state}")
        
        # Search ProPublica
        try:
            # Try with state and city if available
            org = client.find_organization_by_name(company_name, state=state, city=city)
            
            if org:
                ein = org.get('ein', 'N/A')
                org_name = org.get('name', 'N/A')
                org_state = org.get('state', 'N/A')
                org_city = org.get('city', 'N/A')
                
                print(f"     ✓ MATCH FOUND!")
                print(f"        EIN: {ein}")
                print(f"        Name: {org_name}")
                print(f"        Location: {org_city}, {org_state}")
                
                # Get financials if EIN available
                if ein and ein != 'N/A':
                    financials = client.get_organization_financials(ein)
                    if financials:
                        revenue = financials.get('total_revenue', 'N/A')
                        expenses = financials.get('total_expenses', 'N/A')
                        print(f"        Revenue: ${revenue:,}" if isinstance(revenue, (int, float)) else f"        Revenue: {revenue}")
                        print(f"        Expenses: ${expenses:,}" if isinstance(expenses, (int, float)) else f"        Expenses: {expenses}")
                
                results.append({
                    'company_name': company_name,
                    'city': city,
                    'state': state,
                    'match_found': True,
                    'ein': ein,
                    'matched_name': org_name,
                    'matched_city': org_city,
                    'matched_state': org_state,
                    'revenue': financials.get('total_revenue') if financials else None,
                })
            else:
                print(f"     ✗ NO MATCH FOUND")
                results.append({
                    'company_name': company_name,
                    'city': city,
                    'state': state,
                    'match_found': False,
                    'reason': 'No match in ProPublica'
                })
        
        except Exception as e:
            print(f"     ✗ ERROR: {e}")
            results.append({
                'company_name': company_name,
                'city': city,
                'state': state,
                'match_found': False,
                'reason': f'Error: {str(e)}'
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total = len(results)
    matched = sum(1 for r in results if r.get('match_found'))
    match_rate = (matched / total * 100) if total > 0 else 0
    
    print(f"\nTotal companies tested: {total}")
    print(f"Matches found: {matched}")
    print(f"Match rate: {match_rate:.1f}%")
    
    # Show matches
    if matched > 0:
        print(f"\nSuccessful matches:")
        for r in results:
            if r.get('match_found'):
                print(f"  - {r.get('company_name', '')[:50]}")
                print(f"    EIN: {r.get('ein', 'N/A')}")
                if r.get('revenue'):
                    print(f"    Revenue: ${r.get('revenue'):,}")
    
    # Show non-matches
    non_matches = [r for r in results if not r.get('match_found')]
    if non_matches:
        print(f"\nNon-matches ({len(non_matches)}):")
        for r in non_matches:
            print(f"  - {r.get('company_name')[:50]}")
            print(f"    Reason: {r.get('reason', 'Unknown')}")
    
    return results

if __name__ == "__main__":
    test_propublica_matching()

