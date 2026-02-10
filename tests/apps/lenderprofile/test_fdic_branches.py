#!/usr/bin/env python3
"""
Test FDIC BankFind Branch Locations
Shows bank branch footprint - where branches are located.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from justdata.shared.utils.unified_env import ensure_unified_env_loaded
from justdata.apps.lenderprofile.services.fdic_client import FDICClient
from justdata.apps.lenderprofile.processors.identifier_resolver import IdentifierResolver

ensure_unified_env_loaded(verbose=True)

def test_branch_footprint(lender_name: str):
    """Test getting branch locations from FDIC BankFind."""
    print("=" * 80)
    print(f"FDIC BANKFIND BRANCH FOOTPRINT TEST")
    print("=" * 80)
    print(f"\nTesting branch locations for: '{lender_name}'")
    
    # Step 1: Resolve identifiers
    print("\n1. Resolving identifiers...")
    resolver = IdentifierResolver()
    candidates = resolver.get_candidates_with_location(lender_name, limit=1)
    
    if not candidates:
        print("ERROR: Could not find lender")
        return
    
    candidate = candidates[0]
    fdic_cert = candidate.get('fdic_cert')
    institution_name = candidate.get('name')
    
    print(f"   Found: {institution_name}")
    print(f"   FDIC Cert: {fdic_cert}")
    
    if not fdic_cert:
        print("ERROR: No FDIC certificate number found")
        return
    
    # Step 2: Get branch locations
    print(f"\n2. Getting branch locations from FDIC BankFind...")
    fdic_client = FDICClient()
    
    # Try multiple years to see what's available
    years = [2024, 2023, 2022, 2021, 2020]
    branches_by_year = {}
    
    for year in years:
        print(f"\n   Checking {year}...")
        branches = fdic_client.get_branches(fdic_cert, year=year)
        if branches:
            branches_by_year[year] = branches
            print(f"   Found {len(branches)} branches in {year}")
            break
    
    # If no year-specific data, try without year (most recent)
    if not branches_by_year:
        print("\n   Trying most recent data (no year specified)...")
        branches = fdic_client.get_branches(fdic_cert)
        if branches:
            branches_by_year['most_recent'] = branches
            print(f"   Found {len(branches)} branches")
    
    if not branches_by_year:
        print("\n   ERROR: No branch data found")
        print("   This could mean:")
        print("   - The institution doesn't have branches (online-only)")
        print("   - The FDIC cert number is incorrect")
        print("   - The API endpoint structure has changed")
        return
    
    # Step 3: Analyze footprint
    print("\n" + "=" * 80)
    print("BRANCH FOOTPRINT ANALYSIS")
    print("=" * 80)
    
    for year, branches in branches_by_year.items():
        print(f"\n{year}: {len(branches)} branches")
        
        # Group by state
        by_state = {}
        by_city = {}
        total_deposits = 0
        
        for branch in branches:
            state = branch.get('state', '') or branch.get('STALP', '') or branch.get('STATE', '')
            city = branch.get('city', '') or branch.get('CITY', '')
            deposits = branch.get('deposits', 0) or branch.get('DEPOSITS', 0) or 0
            
            if state:
                by_state[state] = by_state.get(state, 0) + 1
            if city and state:
                key = f"{city}, {state}"
                by_city[key] = by_city.get(key, 0) + 1
            
            if deposits:
                total_deposits += deposits
        
        print(f"\n   Geographic Distribution:")
        print(f"   States: {len(by_state)}")
        print(f"   Cities: {len(by_city)}")
        print(f"   Total Deposits: ${total_deposits:,.0f}" if total_deposits > 0 else "   Total Deposits: N/A")
        
        # Top states
        if by_state:
            print(f"\n   Top 10 States by Branch Count:")
            sorted_states = sorted(by_state.items(), key=lambda x: x[1], reverse=True)
            for i, (state, count) in enumerate(sorted_states[:10], 1):
                print(f"   {i:2}. {state}: {count} branches")
        
        # Top cities
        if by_city:
            print(f"\n   Top 10 Cities by Branch Count:")
            sorted_cities = sorted(by_city.items(), key=lambda x: x[1], reverse=True)
            for i, (city, count) in enumerate(sorted_cities[:10], 1):
                print(f"   {i:2}. {city}: {count} branches")
        
        # Sample branch details
        print(f"\n   Sample Branch Locations (first 5):")
        for i, branch in enumerate(branches[:5], 1):
            name = branch.get('name', '') or branch.get('OFFNAME', '') or 'N/A'
            address = branch.get('address', '') or branch.get('ADDRESS', '') or 'N/A'
            city = branch.get('city', '') or branch.get('CITY', '') or 'N/A'
            state = branch.get('state', '') or branch.get('STALP', '') or 'N/A'
            zip_code = branch.get('zip', '') or branch.get('ZIP', '') or 'N/A'
            county = branch.get('county', '') or branch.get('COUNTY', '') or ''
            deposits = branch.get('deposits', 0) or branch.get('DEPOSITS', 0) or 0
            
            print(f"   {i}. {name}")
            print(f"      {address}, {city}, {state} {zip_code}")
            if county:
                print(f"      County: {county}")
            if deposits:
                print(f"      Deposits: ${deposits:,.0f}")
            if branch.get('latitude') and branch.get('longitude'):
                print(f"      Coordinates: {branch.get('latitude')}, {branch.get('longitude')}")
        
        # Show all available fields from first branch
        if branches:
            print(f"\n   Available Data Fields (from first branch):")
            first_branch = branches[0]
            for key in sorted(first_branch.keys())[:20]:  # Show first 20 fields
                value = first_branch[key]
                if value:
                    print(f"      {key}: {value}")

if __name__ == '__main__':
    lender_name = sys.argv[1] if len(sys.argv) > 1 else "Fifth Third Bank"
    test_branch_footprint(lender_name)

