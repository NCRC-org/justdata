"""
Count how many new email addresses were identified that were NOT already in HubSpot.
"""
import json
from pathlib import Path

# Paths
json_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups\all_contacts_enriched.json")

print("="*80)
print("NEW EMAIL ADDRESSES ANALYSIS")
print("="*80)
print()

if not json_file.exists():
    print(f"ERROR: File not found: {json_file}")
    exit(1)

print(f"Loading: {json_file}")
with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

contacts = data.get('contacts', [])
discovered_contacts = data.get('discovered_contacts', [])
enrichment_history = data.get('enrichment_history', [])

print(f"Total contacts in file: {len(contacts):,}")
print(f"Discovered contacts (separate section): {len(discovered_contacts):,}")
print()

# Count emails found via enrichment
emails_found_via_search = 0
emails_found_contacts = []  # Track which contacts got new emails

# Check main contacts list
for contact in contacts:
    email = contact.get('Email', '') or contact.get('email', '')
    email_source = contact.get('Email_Source', '')
    email_found_date = contact.get('Email_Found_Date', '')
    email_search_status = contact.get('Email_Search_Status', '')
    
    # If it has Email_Source = 'DuckDuckGo_Search' or Email_Found_Date, it was found
    if email and (email_source == 'DuckDuckGo_Search' or email_found_date):
        emails_found_via_search += 1
        emails_found_contacts.append({
            'name': f"{contact.get('First Name', '')} {contact.get('Last Name', '')}".strip(),
            'email': email,
            'company': contact.get('Associated Company', ''),
            'source_url': contact.get('Source_URL') or contact.get('Email_Source_URL', ''),
            'found_date': email_found_date
        })

# Count discovered contacts (these are all new)
discovered_with_emails = 0
for contact in discovered_contacts:
    email = contact.get('Email', '') or contact.get('email', '')
    if email:
        discovered_with_emails += 1
        emails_found_contacts.append({
            'name': f"{contact.get('First Name', '')} {contact.get('Last Name', '')}".strip(),
            'email': email,
            'company': contact.get('Associated Company', ''),
            'source_url': contact.get('Source_URL', ''),
            'found_date': contact.get('Discovered_Date', ''),
            'discovered': True
        })

total_new_emails = emails_found_via_search + discovered_with_emails

print("="*80)
print("RESULTS")
print("="*80)
print(f"Emails found for existing contacts: {emails_found_via_search:,}")
print(f"  (Contacts that had Email_Source='DuckDuckGo_Search' or Email_Found_Date)")
print()
print(f"New contacts discovered with emails: {discovered_with_emails:,}")
print(f"  (Contacts from discovered_contacts section)")
print()
print(f"TOTAL NEW EMAIL ADDRESSES IDENTIFIED: {total_new_emails:,}")
print()

# Check enrichment history for statistics
if enrichment_history:
    print("="*80)
    print("ENRICHMENT HISTORY")
    print("="*80)
    total_searched = 0
    total_found = 0
    total_discovered = 0
    
    for entry in enrichment_history:
        date = entry.get('date', 'Unknown')
        searched = entry.get('contacts_searched', 0)
        found = entry.get('emails_found', 0)
        discovered = entry.get('new_contacts_discovered', 0)
        
        total_searched += searched
        total_found += found
        total_discovered += discovered
        
        print(f"  {date[:10]}: Searched {searched:,}, Found {found:,} emails, Discovered {discovered:,} new contacts")
    
    print()
    print(f"Total across all enrichment runs:")
    print(f"  Contacts searched: {total_searched:,}")
    print(f"  Emails found: {total_found:,}")
    print(f"  New contacts discovered: {total_discovered:,}")
    print()

# Show breakdown by source
print("="*80)
print("BREAKDOWN BY SOURCE")
print("="*80)
with_source_url = sum(1 for c in emails_found_contacts if c.get('source_url') and 'http' in str(c.get('source_url')).lower())
without_source_url = total_new_emails - with_source_url

print(f"Emails with source URL: {with_source_url:,}")
print(f"Emails without source URL (found but URL not stored): {without_source_url:,}")
print()

# Show sample of found emails
if emails_found_contacts:
    print("="*80)
    print("SAMPLE OF NEW EMAILS FOUND (first 10)")
    print("="*80)
    for i, contact in enumerate(emails_found_contacts[:10], 1):
        source_info = contact.get('source_url', '') or 'URL not stored'
        discovered = " (NEW CONTACT)" if contact.get('discovered') else ""
        print(f"{i}. {contact['name']} - {contact['email']}")
        print(f"   Company: {contact.get('company', 'N/A')}")
        print(f"   Source: {source_info[:80]}{discovered}")
        print()

print("="*80)
print(f"SUMMARY: {total_new_emails:,} new email addresses identified")
print("        (Not originally in HubSpot)")
print("="*80)

