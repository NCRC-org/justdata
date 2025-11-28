#!/usr/bin/env python3
"""
Search HubSpot Companies for NCRC member organizations.
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


# List of organizations to search for
ORGANIZATIONS = [
    "Committee on Housing",
    "City University of New York (CUNY)",
    "Church of Seventh Day Adventists",
    "Community Preservation Corporation",
    "Trinity Foundation",
    "Housing Conservation Coordinators",
    "Fiscal Policy Institute",
    "COO M Squared",
    "M Squared",
    "Regional Plan Association",
    "Open New York",
    "Local Initiatives Support Corporation",
    "LISC",
    "Legal Aid Society",
    "New York Communities for Change",
    "LiveOn NY",
    "32BJ SEIU",
    "New York State Association for Affordable Housing",
    "CAAAV",
    "Community Service Society",
    "REBNY",
    "Merchants Capital",
    "Tenant Bloc",
    "Association for Neighborhood & Housing Development",
    "ANHD",
    "Center for Public Enterprise",
]


async def search_company_by_name(
    client: HubSpotClient,
    company_name: str
) -> List[Dict[str, Any]]:
    """Search for a company by name."""
    results = []
    
    # Try exact match with CONTAINS_TOKEN
    filters = [
        {
            "propertyName": "name",
            "operator": "CONTAINS_TOKEN",
            "value": company_name
        }
    ]
    
    try:
        companies = await client.search_companies(filters, limit=100)
        for company in companies:
            company["match_type"] = "company_name"
            company["search_term"] = company_name
            results.append(company)
    except Exception as e:
        print(f"  Error searching for company {company_name}: {e}")
    
    return results


async def main():
    """Main search function."""
    print("=" * 80)
    print("HUBSPOT COMPANIES SEARCH - NCRC MEMBERS")
    print("=" * 80)
    print()
    
    # Initialize client
    access_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
    if not access_token:
        print("ERROR: HUBSPOT_ACCESS_TOKEN environment variable not set")
        return
    
    client = HubSpotClient(access_token=access_token)
    
    # Test connection
    print("Testing HubSpot connection...")
    try:
        is_connected = await client.test_connection()
        if not is_connected:
            print("ERROR: Failed to connect to HubSpot")
            return
        print("✓ Connected to HubSpot")
    except Exception as e:
        print(f"ERROR: Failed to connect to HubSpot: {e}")
        return
    
    print()
    print(f"Searching for {len(ORGANIZATIONS)} organizations in HubSpot Companies...")
    print()
    
    all_results = {
        "companies": [],
        "summary": {
            "total_searched": len(ORGANIZATIONS),
            "companies_found": 0,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    found_companies = {}  # Track by company ID to avoid duplicates
    
    # Search for each organization
    for i, org_name in enumerate(ORGANIZATIONS, 1):
        print(f"[{i}/{len(ORGANIZATIONS)}] Searching for: {org_name}")
        
        companies = await search_company_by_name(client, org_name)
        
        if companies:
            print(f"  ✓ Found {len(companies)} company/companies")
            for company in companies:
                company_id = company.get("id")
                if company_id not in found_companies:
                    found_companies[company_id] = company
                    all_results["companies"].append(company)
                    all_results["summary"]["companies_found"] += 1
        else:
            print(f"  ✗ No companies found")
        
        print()
    
    # Print summary
    print("=" * 80)
    print("SEARCH SUMMARY")
    print("=" * 80)
    print(f"Total organizations searched: {all_results['summary']['total_searched']}")
    print(f"Unique NCRC member companies found: {all_results['summary']['companies_found']}")
    print()
    
    # Save results
    output_dir = Path(__file__).parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON output
    def json_serializer(obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    json_file = output_dir / f"hubspot_companies_search_results_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=json_serializer)
    print(f"Results saved to: {json_file}")
    
    # Human-readable report
    report_file = output_dir / f"hubspot_companies_search_report_{timestamp}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("HUBSPOT COMPANIES SEARCH RESULTS - NCRC MEMBERS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Search Date: {all_results['summary']['timestamp']}\n")
        f.write(f"Total Organizations Searched: {all_results['summary']['total_searched']}\n")
        f.write(f"Unique NCRC Member Companies Found: {all_results['summary']['companies_found']}\n")
        f.write("\n" + "=" * 80 + "\n\n")
        
        # Companies section
        if all_results["companies"]:
            f.write("NCRC MEMBER COMPANIES FOUND\n")
            f.write("-" * 80 + "\n\n")
            for company in all_results["companies"]:
                props = company.get("properties", {})
                f.write(f"Company Name: {props.get('name', 'N/A')}\n")
                f.write(f"Domain: {props.get('domain', 'N/A')}\n")
                f.write(f"Industry: {props.get('industry', 'N/A')}\n")
                f.write(f"City: {props.get('city', 'N/A')}\n")
                f.write(f"State: {props.get('state', 'N/A')}\n")
                f.write(f"Match Type: {company.get('match_type', 'N/A')}\n")
                f.write(f"Searched Term: {company.get('search_term', 'N/A')}\n")
                f.write(f"HubSpot ID: {company.get('id', 'N/A')}\n")
                f.write(f"HubSpot URL: https://app.hubspot.com/contacts/{company.get('portalId', 'N/A')}/company/{company.get('id', 'N/A')}\n")
                f.write("\n")
        else:
            f.write("No NCRC member companies found.\n")
    
    print(f"Report saved to: {report_file}")
    print()
    
    # Print found companies
    if all_results["companies"]:
        print("NCRC MEMBER COMPANIES FOUND:")
        print("-" * 80)
        for company in all_results["companies"]:
            props = company.get("properties", {})
            print(f"  • {props.get('name', 'N/A')}")
            if props.get('domain'):
                print(f"    Domain: {props.get('domain')}")
            print(f"    HubSpot ID: {company.get('id')}")
            print()
    
    print("Search complete!")


if __name__ == "__main__":
    asyncio.run(main())










