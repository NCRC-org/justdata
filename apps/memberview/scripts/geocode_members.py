#!/usr/bin/env python3
"""
Pre-geocode all member locations and save coordinates.
This should be run once to populate coordinates for all members.
"""
import sys
from pathlib import Path

# Add parent directories to path
BASE_DIR = Path(__file__).parent.parent
JUSTDATA_BASE = BASE_DIR.parent.parent
sys.path.insert(0, str(JUSTDATA_BASE))

from apps.memberview.data_utils import MemberDataLoader
from apps.memberview.utils.geocoder import Geocoder
import pandas as pd
import json

def geocode_all_members():
    """Geocode all member locations and save to file."""
    print("=" * 80)
    print("GEOCODING MEMBER LOCATIONS")
    print("=" * 80)
    
    # Initialize data loader
    loader = MemberDataLoader()
    
    # Get all members
    print("\nLoading members...")
    members_df = loader.get_members()
    print(f"Found {len(members_df):,} members")
    
    # Find location columns in companies
    city_col = None
    state_col = None
    name_col = None
    country_col = None
    record_id_col = None
    
    for col in members_df.columns:
        col_lower = col.lower()
        if col_lower == 'city':
            city_col = col
        elif ('state' in col_lower or 'region' in col_lower) and 'country' not in col_lower:
            if not state_col:
                state_col = col
        elif 'company' in col_lower and 'name' in col_lower:
            name_col = col
        elif 'country' in col_lower and 'region' in col_lower:
            country_col = col
        elif 'record id' in col_lower:
            record_id_col = col
    
    if not city_col or not state_col:
        print("ERROR: Could not find city or state columns")
        return False
    
    print(f"Using columns: City='{city_col}', State='{state_col}'")
    if name_col:
        print(f"  Company Name='{name_col}'")
    if record_id_col:
        print(f"  Record ID='{record_id_col}'")
    
    # Get address data from deals table
    print("\nLoading deals data to get company addresses...")
    deals = loader.load_deals()
    
    # Find company ID column in deals
    company_id_col_deals = None
    for col in deals.columns:
        if 'associated_company_ids_(primary)' in col.lower() or ('associated company' in col.lower() and 'primary' in col.lower()):
            company_id_col_deals = col
            break
    
    if not company_id_col_deals:
        print("WARNING: Could not find company ID column in deals")
    else:
        print(f"Found company ID column in deals: '{company_id_col_deals}'")
        # Check if address fields exist
        has_address = 'company_address' in deals.columns
        has_zip = 'company_zip' in deals.columns
        print(f"  Has company_address: {has_address}")
        print(f"  Has company_zip: {has_zip}")
        
        if has_address:
            address_count = deals['company_address'].notna().sum()
            print(f"  Addresses in deals: {address_count}/{len(deals)} ({address_count/len(deals)*100:.1f}%)")
    
    # Initialize geocoder with cache
    cache_file = BASE_DIR / "data" / "geocoding_cache.json"
    geocoder = Geocoder(cache_file=cache_file)
    
    print(f"\nGeocoding cache: {cache_file}")
    print(f"Cache contains {len(geocoder.cache)} locations")
    
    # Geocode each member individually (not just unique locations) to use full address
    print("\nGeocoding member locations (this may take a while due to rate limits)...")
    print("Using full address (company name + city + state) for better accuracy")
    location_coords = {}
    total = len(members_df)
    
    # Create mapping of company ID to address/zip from deals
    company_address_map = {}
    if company_id_col_deals and 'company_address' in deals.columns:
        print("\nBuilding company address map from deals...")
        for _, deal_row in deals.iterrows():
            company_id = str(deal_row[company_id_col_deals]).replace('.0', '').strip() if pd.notna(deal_row[company_id_col_deals]) else ''
            if not company_id:
                continue
            
            # Get address and zip from deal
            deal_address = str(deal_row.get('company_address', '')).strip() if pd.notna(deal_row.get('company_address')) else ''
            deal_zip = str(deal_row.get('company_zip', '')).strip() if pd.notna(deal_row.get('company_zip')) else ''
            
            # Store if we have address data (prefer first non-empty value)
            if company_id not in company_address_map and (deal_address or deal_zip):
                company_address_map[company_id] = {
                    'address': deal_address,
                    'zip': deal_zip
                }
        
        print(f"Found addresses for {len(company_address_map)} companies in deals table")
    
    for idx, (_, row) in enumerate(members_df.iterrows(), 1):
        member_id = str(row[record_id_col]).strip() if record_id_col and pd.notna(row[record_id_col]) else ''
        city = str(row[city_col]).strip() if pd.notna(row[city_col]) else ''
        state = str(row[state_col]).strip() if pd.notna(row[state_col]) else ''
        company_name = str(row[name_col]).strip() if name_col and pd.notna(row[name_col]) else ''
        country = str(row[country_col]).strip() if country_col and pd.notna(row[country_col]) else 'USA'
        
        if not city or not state:
            continue
        
        # Get address from deals table if available
        address = ''
        zip_code = ''
        if member_id in company_address_map:
            address = company_address_map[member_id].get('address', '')
            zip_code = company_address_map[member_id].get('zip', '')
        
        # Build full address string for geocoding (order: street address, city, state, zip, country)
        address_parts = []
        if address:
            address_parts.append(address)
        if city:
            address_parts.append(city)
        if state:
            address_parts.append(state)
        if zip_code:
            address_parts.append(zip_code)
        if country:
            address_parts.append(country)
        
        full_address = ', '.join(address_parts) if address_parts else None
        
        # Create cache key
        if full_address:
            location_key = full_address.lower()
        else:
            location_key = f"{city}|{state}".lower()
        
        # Skip if already geocoded
        if location_key in location_coords:
            continue
        
        display_addr = full_address if full_address else f"{city}, {state}"
        print(f"[{idx}/{total}] Geocoding: {display_addr[:60]}...", end=' ')
        
        # Use full address for geocoding (includes street address if available from deals)
        coords = geocoder.geocode(
            city=city if city else None,
            state=state if state else None,
            country=country if country else 'USA',
            address=full_address if full_address else None,
            company_name=None  # Don't include company name - address is more specific
        )
        
        if coords:
            location_coords[location_key] = coords
            print(f"✓ ({coords[0]:.4f}, {coords[1]:.4f})")
        else:
            print("✗ Failed")
    
    print(f"\nSuccessfully geocoded {len(location_coords):,} locations")
    
    # Save coordinates to file
    coords_file = BASE_DIR / "data" / "member_coordinates.json"
    coords_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(coords_file, 'w') as f:
        json.dump(location_coords, f, indent=2)
    
    print(f"\nSaved coordinates to: {coords_file}")
    
    # Add coordinates to members dataframe
    print("\nAdding coordinates to member data...")
    members_df['lat'] = None
    members_df['lng'] = None
    
    for idx, row in members_df.iterrows():
        member_id = str(row[record_id_col]).strip() if record_id_col and pd.notna(row[record_id_col]) else ''
        city = str(row[city_col]).strip() if pd.notna(row[city_col]) else ''
        state = str(row[state_col]).strip() if pd.notna(row[state_col]) else ''
        country = str(row[country_col]).strip() if country_col and pd.notna(row[country_col]) else 'USA'
        
        # Get address from deals if available
        address = ''
        zip_code = ''
        if member_id in company_address_map:
            address = company_address_map[member_id].get('address', '')
            zip_code = company_address_map[member_id].get('zip', '')
        
        # Build full address to match cache key (same order as geocoding: address, city, state, zip, country)
        address_parts = []
        if address:
            address_parts.append(address)
        if city:
            address_parts.append(city)
        if state:
            address_parts.append(state)
        if zip_code:
            address_parts.append(zip_code)
        if country:
            address_parts.append(country)
        
        full_address = ', '.join(address_parts) if address_parts else None
        
        # Try full address first, then fall back to city|state
        key = full_address.lower() if full_address else f"{city}|{state}".lower()
        
        if key in location_coords:
            lat, lng = location_coords[key]
            members_df.at[idx, 'lat'] = lat
            members_df.at[idx, 'lng'] = lng
        else:
            # Try city|state as fallback
            fallback_key = f"{city}|{state}".lower()
            if fallback_key in location_coords:
                lat, lng = location_coords[fallback_key]
                members_df.at[idx, 'lat'] = lat
                members_df.at[idx, 'lng'] = lng
    
    # Count members with coordinates
    members_with_coords = members_df['lat'].notna().sum()
    print(f"Members with coordinates: {members_with_coords:,} ({members_with_coords/len(members_df)*100:.1f}%)")
    
    # Save members with coordinates
    members_file = BASE_DIR / "data" / "members_with_coordinates.csv"
    members_df.to_csv(members_file, index=False)
    print(f"Saved members data to: {members_file}")
    
    print("\n" + "=" * 80)
    print("GEOCODING COMPLETE")
    print("=" * 80)
    print(f"Total members: {len(members_df):,}")
    print(f"Members with coordinates: {members_with_coords:,}")
    print(f"Members without coordinates: {len(members_df) - members_with_coords:,}")
    
    return True

if __name__ == "__main__":
    success = geocode_all_members()
    sys.exit(0 if success else 1)

