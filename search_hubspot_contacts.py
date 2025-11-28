#!/usr/bin/env python3
"""
Search HubSpot contacts and companies for specific people and organizations.
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
from apps.hubspot.lists import HubSpotListsClient


# List of people and organizations to search for
SEARCH_TARGETS = [
    # Organizations
    {"type": "organization", "name": "Committee on Housing"},
    
    # People with organizations
    {"type": "person", "first_name": "Nicholas", "last_name": "Bloom", "organization": "City University of New York (CUNY)"},
    {"type": "person", "first_name": "Dedrick", "last_name": "Blue", "organization": "Church of Seventh Day Adventists"},
    {"type": "person", "first_name": "Rafael", "last_name": "Cestero", "organization": "Community Preservation Corporation"},
    {"type": "person", "first_name": "Bea", "last_name": "De la Torre", "organization": "Trinity Foundation"},
    {"type": "person", "first_name": "Charlie", "last_name": "Dulik", "organization": "Housing Conservation Coordinators"},
    {"type": "person", "first_name": "Emily", "last_name": "Eisner", "organization": "Fiscal Policy Institute"},
    {"type": "person", "first_name": "Carolee", "last_name": "Fink", "organization": "COO M Squared"},
    {"type": "person", "first_name": "Moses", "last_name": "Gates", "organization": "Regional Plan Association"},
    {"type": "person", "first_name": "Lisa", "last_name": "Gomez"},
    {"type": "person", "first_name": "Annemarie", "last_name": "Gray", "organization": "Open New York"},
    {"type": "person", "first_name": "David", "last_name": "Greenberg", "organization": "Local Initiatives Support Corporation (LISC)"},
    {"type": "person", "first_name": "Adriene", "last_name": "Holder", "organization": "Legal Aid Society"},
    {"type": "person", "first_name": "Olivia", "last_name": "Leirer", "organization": "New York Communities for Change"},
    {"type": "person", "first_name": "Allison", "last_name": "Nickerson", "organization": "LiveOn NY"},
    {"type": "person", "first_name": "Manny", "last_name": "Pastreich", "organization": "32BJ SEIU"},
    {"type": "person", "first_name": "Carlina", "last_name": "Rivera", "organization": "New York State Association for Affordable Housing"},
    {"type": "person", "first_name": "Brian", "last_name": "Scott", "organization": "Pastor"},
    {"type": "person", "first_name": "Alina", "last_name": "Shen", "organization": "CAAAV"},
    {"type": "person", "first_name": "Iziah", "last_name": "Thompson", "organization": "Community Service Society"},
    {"type": "person", "first_name": "Jed", "last_name": "Walentas", "organization": "REBNY"},
    {"type": "person", "first_name": "Matt", "last_name": "Wambua", "organization": "Merchants Capital"},
    {"type": "person", "first_name": "Cea", "last_name": "Weaver", "organization": "Tenant Bloc"},
    {"type": "person", "first_name": "Barika", "last_name": "Williams", "organization": "Association for Neighborhood & Housing Development"},
    {"type": "person", "first_name": "Paul", "last_name": "Williams", "organization": "Center for Public Enterprise"},
]


async def search_contact_by_name(
    client: HubSpotClient,
    first_name: str,
    last_name: str,
    organization: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search for a contact by name."""
    results = []
    
    # Search by first name and last name
    filters = [
        {
            "propertyName": "firstname",
            "operator": "CONTAINS_TOKEN",
            "value": first_name
        },
        {
            "propertyName": "lastname",
            "operator": "CONTAINS_TOKEN",
            "value": last_name
        }
    ]
    
    try:
        contacts = await client.search_contacts(filters, limit=100)
        for contact in contacts:
            contact["match_type"] = "name"
            contact["search_organization"] = organization
            results.append(contact)
    except Exception as e:
        print(f"  Error searching for {first_name} {last_name}: {e}")
    
    # Also try searching by last name only (in case first name is different)
    if not results:
        filters_lastname = [
            {
                "propertyName": "lastname",
                "operator": "EQ",
                "value": last_name
            }
        ]
        try:
            contacts = await client.search_contacts(filters_lastname, limit=100)
            for contact in contacts:
                # Check if first name is similar
                props = contact.get("properties", {})
                contact_first = props.get("firstname", "").lower()
                if first_name.lower() in contact_first or contact_first in first_name.lower():
                    contact["match_type"] = "name_partial"
                    contact["search_organization"] = organization
                    results.append(contact)
        except Exception as e:
            print(f"  Error searching by last name for {last_name}: {e}")
    
    # If organization provided, also search by company
    if organization and not results:
        filters_company = [
            {
                "propertyName": "company",
                "operator": "CONTAINS_TOKEN",
                "value": organization
            },
            {
                "propertyName": "lastname",
                "operator": "CONTAINS_TOKEN",
                "value": last_name
            }
        ]
        try:
            contacts = await client.search_contacts(filters_company, limit=100)
            for contact in contacts:
                contact["match_type"] = "company_and_name"
                contact["search_organization"] = organization
                results.append(contact)
        except Exception as e:
            print(f"  Error searching by company for {organization}: {e}")
    
    return results


async def search_company_by_name(
    client: HubSpotClient,
    company_name: str
) -> List[Dict[str, Any]]:
    """Search for a company by name."""
    results = []
    
    # Try exact match first
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
            results.append(company)
    except Exception as e:
        print(f"  Error searching for company {company_name}: {e}")
    
    # Also try partial match using CONTAINS_TOKEN
    if not results:
        filters_partial = [
            {
                "propertyName": "name",
                "operator": "CONTAINS_TOKEN",
                "value": company_name
            }
        ]
        try:
            companies = await client.search_companies(filters_partial, limit=100)
            for company in companies:
                company["match_type"] = "company_name_partial"
                results.append(company)
        except Exception as e:
            print(f"  Error searching for company {company_name} (partial): {e}")
    
    return results


async def search_in_member_lists(
    lists_client: HubSpotListsClient,
    search_target: Dict[str, Any],
    cached_lists: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """Search for contacts in member lists."""
    results = []
    
    try:
        # Get all lists (use cached if provided)
        if cached_lists is None:
            all_lists = await lists_client.get_all_lists()
        else:
            all_lists = cached_lists
        
        # Skip if no lists
        if not all_lists:
            return results
        
        for lst in all_lists:
            list_name = lst.get("name", "")
            list_id = lst.get("listId")
            
            try:
                # Get contacts from this list
                contacts_data = await lists_client.get_list_contacts(list_id, limit=500)
                contacts = contacts_data.get("contacts", [])
                
                # Check each contact
                for contact in contacts:
                    props = contact.get("properties", {})
                    
                    if search_target["type"] == "person":
                        first_name = search_target.get("first_name", "").lower()
                        last_name = search_target.get("last_name", "").lower()
                        contact_first = props.get("firstname", "").lower()
                        contact_last = props.get("lastname", "").lower()
                        
                        if (first_name in contact_first or contact_first in first_name) and \
                           (last_name in contact_last or contact_last in last_name):
                            contact["match_type"] = "member_list"
                            contact["list_name"] = list_name
                            contact["search_organization"] = search_target.get("organization")
                            results.append(contact)
                    
                    elif search_target["type"] == "organization":
                        org_name = search_target.get("name", "").lower()
                        company = props.get("company", "").lower()
                        if org_name in company or company in org_name:
                            contact["match_type"] = "member_list_company"
                            contact["list_name"] = list_name
                            results.append(contact)
            
            except Exception as e:
                # Skip lists that fail
                continue
    
    except Exception as e:
        print(f"  Error searching member lists: {e}")
    
    return results


async def main():
    """Main search function."""
    print("=" * 80)
    print("HUBSPOT CONTACT AND MEMBER DATA SEARCH")
    print("=" * 80)
    print()
    
    # Initialize clients
    access_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
    if not access_token:
        print("ERROR: HUBSPOT_ACCESS_TOKEN environment variable not set")
        print("Please set it before running this script.")
        return
    
    client = HubSpotClient(access_token=access_token)
    lists_client = HubSpotListsClient(access_token=access_token)
    
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
    print(f"Searching for {len(SEARCH_TARGETS)} targets...")
    print()
    
    # Cache member lists (only fetch once)
    print("Fetching member lists...")
    try:
        cached_lists = await lists_client.get_all_lists()
        print(f"Found {len(cached_lists)} member list(s)")
    except Exception as e:
        print(f"Warning: Could not fetch member lists: {e}")
        cached_lists = []
    print()
    
    all_results = {
        "contacts": [],
        "companies": [],
        "member_list_matches": [],
        "summary": {
            "total_searched": len(SEARCH_TARGETS),
            "contacts_found": 0,
            "companies_found": 0,
            "member_list_matches": 0,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    # Search for each target
    for i, target in enumerate(SEARCH_TARGETS, 1):
        print(f"[{i}/{len(SEARCH_TARGETS)}] Searching for: ", end="")
        
        if target["type"] == "person":
            name_str = f"{target.get('first_name', '')} {target.get('last_name', '')}"
            org_str = f" ({target.get('organization', '')})" if target.get('organization') else ""
            print(f"{name_str}{org_str}")
            
            # Search contacts
            contacts = await search_contact_by_name(
                client,
                target.get("first_name", ""),
                target.get("last_name", ""),
                target.get("organization")
            )
            
            if contacts:
                print(f"  ✓ Found {len(contacts)} contact(s)")
                all_results["contacts"].extend(contacts)
                all_results["summary"]["contacts_found"] += len(contacts)
            else:
                print(f"  ✗ No contacts found")
            
            # Search in member lists (use cached lists)
            member_matches = await search_in_member_lists(lists_client, target, cached_lists)
            if member_matches:
                print(f"  ✓ Found {len(member_matches)} member list match(es)")
                all_results["member_list_matches"].extend(member_matches)
                all_results["summary"]["member_list_matches"] += len(member_matches)
        
        elif target["type"] == "organization":
            print(f"{target.get('name', '')}")
            
            # Search companies
            companies = await search_company_by_name(client, target.get("name", ""))
            
            if companies:
                print(f"  ✓ Found {len(companies)} company/companies")
                all_results["companies"].extend(companies)
                all_results["summary"]["companies_found"] += len(companies)
            else:
                print(f"  ✗ No companies found")
            
            # Also search for contacts with this company
            filters = [
                {
                    "propertyName": "company",
                    "operator": "CONTAINS_TOKEN",
                    "value": target.get("name", "")
                }
            ]
            try:
                contacts = await client.search_contacts(filters, limit=100)
                if contacts:
                    print(f"  ✓ Found {len(contacts)} contact(s) at this organization")
                    for contact in contacts:
                        contact["match_type"] = "company_contact"
                        contact["search_organization"] = target.get("name")
                    all_results["contacts"].extend(contacts)
                    all_results["summary"]["contacts_found"] += len(contacts)
            except Exception as e:
                print(f"  Error searching contacts for organization: {e}")
            
            # Search in member lists (use cached lists)
            member_matches = await search_in_member_lists(lists_client, target, cached_lists)
            if member_matches:
                print(f"  ✓ Found {len(member_matches)} member list match(es)")
                all_results["member_list_matches"].extend(member_matches)
                all_results["summary"]["member_list_matches"] += len(member_matches)
        
        print()
    
    # Print summary
    print("=" * 80)
    print("SEARCH SUMMARY")
    print("=" * 80)
    print(f"Total targets searched: {all_results['summary']['total_searched']}")
    print(f"Contacts found: {all_results['summary']['contacts_found']}")
    print(f"Companies found: {all_results['summary']['companies_found']}")
    print(f"Member list matches: {all_results['summary']['member_list_matches']}")
    print()
    
    # Save results
    output_dir = Path(__file__).parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON output (convert datetime objects to strings)
    def json_serializer(obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    json_file = output_dir / f"hubspot_search_results_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=json_serializer)
    print(f"Results saved to: {json_file}")
    
    # Human-readable report
    report_file = output_dir / f"hubspot_search_report_{timestamp}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("HUBSPOT CONTACT AND MEMBER DATA SEARCH RESULTS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Search Date: {all_results['summary']['timestamp']}\n")
        f.write(f"Total Targets Searched: {all_results['summary']['total_searched']}\n")
        f.write(f"Contacts Found: {all_results['summary']['contacts_found']}\n")
        f.write(f"Companies Found: {all_results['summary']['companies_found']}\n")
        f.write(f"Member List Matches: {all_results['summary']['member_list_matches']}\n")
        f.write("\n" + "=" * 80 + "\n\n")
        
        # Contacts section
        if all_results["contacts"]:
            f.write("CONTACTS FOUND\n")
            f.write("-" * 80 + "\n\n")
            for contact in all_results["contacts"]:
                props = contact.get("properties", {})
                f.write(f"Name: {props.get('firstname', '')} {props.get('lastname', '')}\n")
                f.write(f"Email: {props.get('email', 'N/A')}\n")
                f.write(f"Company: {props.get('company', 'N/A')}\n")
                f.write(f"Match Type: {contact.get('match_type', 'N/A')}\n")
                if contact.get('search_organization'):
                    f.write(f"Searched Organization: {contact.get('search_organization')}\n")
                f.write(f"HubSpot ID: {contact.get('id', 'N/A')}\n")
                f.write(f"HubSpot URL: https://app.hubspot.com/contacts/{contact.get('portalId', 'N/A')}/contact/{contact.get('id', 'N/A')}\n")
                f.write("\n")
        
        # Companies section
        if all_results["companies"]:
            f.write("COMPANIES FOUND\n")
            f.write("-" * 80 + "\n\n")
            for company in all_results["companies"]:
                props = company.get("properties", {})
                f.write(f"Name: {props.get('name', 'N/A')}\n")
                f.write(f"Domain: {props.get('domain', 'N/A')}\n")
                f.write(f"Match Type: {company.get('match_type', 'N/A')}\n")
                f.write(f"HubSpot ID: {company.get('id', 'N/A')}\n")
                f.write(f"HubSpot URL: https://app.hubspot.com/contacts/{company.get('portalId', 'N/A')}/company/{company.get('id', 'N/A')}\n")
                f.write("\n")
        
        # Member list matches section
        if all_results["member_list_matches"]:
            f.write("MEMBER LIST MATCHES\n")
            f.write("-" * 80 + "\n\n")
            for contact in all_results["member_list_matches"]:
                props = contact.get("properties", {})
                f.write(f"Name: {props.get('firstname', '')} {props.get('lastname', '')}\n")
                f.write(f"Email: {props.get('email', 'N/A')}\n")
                f.write(f"Company: {props.get('company', 'N/A')}\n")
                f.write(f"List: {contact.get('list_name', 'N/A')}\n")
                f.write(f"Match Type: {contact.get('match_type', 'N/A')}\n")
                if contact.get('search_organization'):
                    f.write(f"Searched Organization: {contact.get('search_organization')}\n")
                f.write(f"HubSpot ID: {contact.get('id', 'N/A')}\n")
                f.write("\n")
    
    print(f"Report saved to: {report_file}")
    print()
    print("Search complete!")


if __name__ == "__main__":
    asyncio.run(main())

