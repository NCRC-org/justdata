#!/usr/bin/env python3
"""
Check membership status for HubSpot companies to find current/grace period members.
"""

import asyncio
import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add the project root to the path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from apps.hubspot.client import HubSpotClient


async def get_company_with_properties(
    client: HubSpotClient,
    company_id: str
) -> Dict[str, Any]:
    """Get a company with all its properties."""
    try:
        company = await client.get_company(company_id)
        return company
    except Exception as e:
        print(f"  Error getting company {company_id}: {e}")
        return {}


async def main():
    """Check membership status for the companies we found."""
    print("=" * 80)
    print("CHECKING MEMBERSHIP STATUS FOR NCRC MEMBER COMPANIES")
    print("=" * 80)
    print()
    
    # Initialize client
    access_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
    if not access_token:
        print("ERROR: HUBSPOT_ACCESS_TOKEN environment variable not set")
        return
    
    client = HubSpotClient(access_token=access_token)
    
    # Load the companies we found
    companies_file = Path("hubspot_companies_search_results_20251125_125030.json")
    if not companies_file.exists():
        print(f"ERROR: {companies_file} not found")
        return
    
    with open(companies_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    companies = data.get("companies", [])
    print(f"Found {len(companies)} companies to check")
    print()
    
    # Check each company's membership status
    current_grace_members = []
    other_members = []
    
    for i, company in enumerate(companies, 1):
        company_id = company.get("id")
        company_name = company.get("properties", {}).get("name", "Unknown")
        
        print(f"[{i}/{len(companies)}] Checking: {company_name}")
        
        # Get full company details with all properties
        full_company = await get_company_with_properties(client, company_id)
        
        if not full_company:
            continue
        
        props = full_company.get("properties", {})
        
        # Look for membership status fields
        membership_status = None
        status_fields = [
            "membership_status",
            "membership_status_when_renewing",
            "membership_type",
            "ncrc_membership_status",
            "member_status",
            "status"
        ]
        
        for field in status_fields:
            if field in props and props[field]:
                membership_status = props[field]
                break
        
        # Also check all properties for membership-related fields
        all_props = list(props.keys())
        membership_fields = [k for k in all_props if 'member' in k.lower() or 'status' in k.lower()]
        
        company_info = {
            "id": company_id,
            "name": company_name,
            "domain": props.get("domain", "N/A"),
            "membership_status": membership_status or "Not specified",
            "all_membership_fields": {k: props.get(k) for k in membership_fields if props.get(k)},
            "all_properties": props
        }
        
        # Check if status indicates current or grace period
        status_lower = str(membership_status or "").lower()
        if any(term in status_lower for term in ["current", "grace", "active"]):
            current_grace_members.append(company_info)
            print(f"  ✓ Current/Grace Period Member")
        else:
            other_members.append(company_info)
            print(f"  - Status: {membership_status or 'Not specified'}")
        
        print()
    
    # Print summary
    print("=" * 80)
    print("MEMBERSHIP STATUS SUMMARY")
    print("=" * 80)
    print(f"Current/Grace Period Members: {len(current_grace_members)}")
    print(f"Other Status/Not Specified: {len(other_members)}")
    print()
    
    # Save results
    output_dir = Path(__file__).parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    results = {
        "current_grace_members": current_grace_members,
        "other_members": other_members,
        "timestamp": datetime.now().isoformat()
    }
    
    json_file = output_dir / f"membership_status_check_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"Results saved to: {json_file}")
    
    # Print current/grace period members
    if current_grace_members:
        print()
        print("CURRENT/GRACE PERIOD MEMBERS:")
        print("-" * 80)
        for company in current_grace_members:
            print(f"  • {company['name']}")
            print(f"    Status: {company['membership_status']}")
            print(f"    Domain: {company['domain']}")
            print(f"    HubSpot ID: {company['id']}")
            if company['all_membership_fields']:
                print(f"    Membership Fields: {company['all_membership_fields']}")
            print()
    
    # Check specifically for ANHD
    print("=" * 80)
    print("ANHD SPECIFIC CHECK")
    print("=" * 80)
    anhd_companies = [c for c in current_grace_members + other_members if 'anhd' in c['name'].lower() or 'neighborhood' in c['name'].lower() and 'housing' in c['name'].lower()]
    
    if anhd_companies:
        print(f"Found {len(anhd_companies)} ANHD-related company/companies:")
        for company in anhd_companies:
            print(f"  • {company['name']}")
            print(f"    Status: {company['membership_status']}")
            print(f"    Domain: {company['domain']}")
            print(f"    HubSpot ID: {company['id']}")
            print()
    else:
        print("ANHD not found in the companies list")
        print("Searching specifically for ANHD...")
        
        # Search for ANHD specifically
        filters = [
            {
                "propertyName": "name",
                "operator": "CONTAINS_TOKEN",
                "value": "ANHD"
            }
        ]
        try:
            anhd_results = await client.search_companies(filters, limit=10)
            if anhd_results:
                print(f"Found {len(anhd_results)} ANHD company/companies:")
                for company in anhd_results:
                    props = company.get("properties", {})
                    print(f"  • {props.get('name', 'N/A')}")
                    print(f"    Domain: {props.get('domain', 'N/A')}")
                    print(f"    HubSpot ID: {company.get('id')}")
                    # Get full details
                    full_company = await get_company_with_properties(client, company.get('id'))
                    if full_company:
                        full_props = full_company.get("properties", {})
                        membership_fields = {k: full_props.get(k) for k in full_props.keys() if 'member' in k.lower() or 'status' in k.lower()}
                        if membership_fields:
                            print(f"    Membership Fields: {membership_fields}")
                    print()
            else:
                print("No ANHD companies found")
        except Exception as e:
            print(f"Error searching for ANHD: {e}")
    
    print("Check complete!")


if __name__ == "__main__":
    asyncio.run(main())










