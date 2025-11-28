"""
Export contacts to CSV with Name, Employer, Email Address(es), and Source Website URL in the LAST column.
Includes all URLs where email information was confirmed/found.
"""
import json
import csv
from pathlib import Path
from datetime import datetime

# Paths
json_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups\all_contacts_enriched.json")
csv_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups\contacts_export_with_source.csv")

print(f"Loading contacts from: {json_file}")

# Try enriched file first, fall back to original
if not json_file.exists():
    json_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups\all_contacts.json")
    print(f"Enriched file not found, using: {json_file}")
    print("WARNING: Original file may not have source URL information")

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

contacts = data.get('contacts', [])
discovered_contacts = data.get('discovered_contacts', [])
print(f"Loaded {len(contacts):,} total contacts")
print(f"Found {len(discovered_contacts):,} discovered contacts in separate section")

# Filter to only enriched contacts (those with source URLs or enrichment metadata)
enriched_contacts = []
for contact in contacts:
    # Check if contact was enriched - has source URL, email source, or found date
    has_source_url = bool(contact.get('Source_URL') or contact.get('Email_Source_URL') or contact.get('Email_Found_URL'))
    has_email_source = bool(contact.get('Email_Source'))
    has_found_date = bool(contact.get('Email_Found_Date') or contact.get('Discovered_Date'))
    has_search_status = bool(contact.get('Email_Search_Status'))
    
    # Include if it has any enrichment indicators
    if has_source_url or has_email_source or has_found_date or has_search_status:
        enriched_contacts.append(contact)

# Also add discovered contacts (they should all have source URLs)
if discovered_contacts:
    print(f"Adding {len(discovered_contacts):,} discovered contacts...")
    enriched_contacts.extend(discovered_contacts)

print(f"\nTotal enriched contacts to export: {len(enriched_contacts):,}")
print(f"(Filtered from {len(contacts):,} total contacts)\n")

# Prepare CSV data
csv_rows = []

for contact in enriched_contacts:
    # Get name components
    first_name = str(contact.get('First Name', '') or '').strip()
    last_name = str(contact.get('Last Name', '') or '').strip()
    full_name = f"{first_name} {last_name}".strip()
    
    # Get employer/company
    company = str(contact.get('Associated Company', '') or '').strip()
    if not company or company.lower() in ['nan', 'none', 'null', '']:
        company = ''
    
    # Get email(s)
    email = str(contact.get('Email', '') or '').strip()
    if not email or email.lower() in ['nan', 'none', 'null', '']:
        email = ''
    
    # Check for additional email fields (if any)
    additional_emails = []
    for key in contact.keys():
        if 'email' in key.lower() and key != 'Email':
            value = str(contact.get(key, '') or '').strip()
            if value and value.lower() not in ['nan', 'none', 'null', '']:
                additional_emails.append(value)
    
    # Combine all emails
    all_emails = [email] if email else []
    all_emails.extend(additional_emails)
    emails_str = '; '.join([e for e in all_emails if e])
    
    # Get source website/URL where email was confirmed
    source_url = ''
    
    # Check multiple possible fields for source URL
    # 1. Source_URL (for discovered contacts)
    if contact.get('Source_URL'):
        source_url = str(contact.get('Source_URL', '')).strip()
    
    # 2. Email_Source_URL (if exists)
    elif contact.get('Email_Source_URL'):
        source_url = str(contact.get('Email_Source_URL', '')).strip()
    
    # 3. Email_Found_URL (if exists)
    elif contact.get('Email_Found_URL'):
        source_url = str(contact.get('Email_Found_URL', '')).strip()
    
    # 4. Check Email_Source field to provide context
    email_source = contact.get('Email_Source', '')
    if email_source and not source_url:
        # If we have Email_Source but no URL, indicate the source method
        if email_source == 'DuckDuckGo_Search':
            source_url = 'Found via DuckDuckGo Search (URL not stored)'
        elif email_source == 'Discovered_via_Search':
            source_url = 'Discovered via Search (URL not stored)'
        elif email_source:
            source_url = f'Source: {email_source}'
    
    # 5. Check if email was in original data (no source means it was original)
    if not email_source and not source_url and email:
        source_url = 'Original Data (HubSpot)'
    
    # 6. If still no source and no email, leave blank
    if not source_url and not email:
        source_url = ''
    
    # 7. If email exists but no source info, mark as unknown
    if email and not source_url:
        source_url = 'Source Unknown'
    
    # Get additional metadata
    email_found_date = contact.get('Email_Found_Date', '') or contact.get('Discovered_Date', '')
    email_search_status = contact.get('Email_Search_Status', '')
    
    # Add row - URL is in the LAST column
    csv_rows.append({
        'Name': full_name,
        'First Name': first_name,
        'Last Name': last_name,
        'Employer': company,
        'Email Address': emails_str,
        'Primary Email': email,
        'Email Found Date': email_found_date if email_found_date else '',
        'Email Search Status': email_search_status if email_search_status else '',
        'Record ID': str(contact.get('Record ID', '') or ''),
        'Source URL': source_url  # LAST COLUMN - URL where email was located
    })

# Write CSV
print(f"\nWriting {len(csv_rows):,} contacts to CSV: {csv_file}")

with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
    # Fieldnames with Source URL as the LAST column
    fieldnames = [
        'Name', 
        'First Name', 
        'Last Name', 
        'Employer', 
        'Email Address', 
        'Primary Email',
        'Email Found Date',
        'Email Search Status',
        'Record ID',
        'Source URL'  # LAST COLUMN - URL where email was located
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    
    writer.writeheader()
    writer.writerows(csv_rows)

print(f"Successfully exported to: {csv_file}")

# Print summary
contacts_with_emails = sum(1 for row in csv_rows if row['Email Address'])
contacts_with_companies = sum(1 for row in csv_rows if row['Employer'])
contacts_with_urls = sum(1 for row in csv_rows if row['Source URL'] and 
                        ('http' in row['Source URL'].lower() or 'www.' in row['Source URL'].lower()))

# Count source types
source_types = {}
for row in csv_rows:
    source = row['Source URL']
    if source:
        # Categorize sources
        if 'http' in source.lower() or 'www.' in source.lower():
            source_type = 'Website URL'
        elif 'DuckDuckGo' in source:
            source_type = 'DuckDuckGo Search'
        elif 'Original Data' in source or 'HubSpot' in source:
            source_type = 'Original/HubSpot'
        elif 'Discovered' in source:
            source_type = 'Discovered via Search'
        elif 'Source Unknown' in source:
            source_type = 'Unknown'
        else:
            source_type = 'Other'
        
        source_types[source_type] = source_types.get(source_type, 0) + 1

print(f"\nSummary:")
print(f"  Total enriched contacts exported: {len(csv_rows):,}")
print(f"  Contacts with emails: {contacts_with_emails:,}")
print(f"  Contacts with employers: {contacts_with_companies:,}")
print(f"  Contacts with actual URLs: {contacts_with_urls:,}")
print(f"\n  Source Type Breakdown:")
for source_type, count in sorted(source_types.items(), key=lambda x: x[1], reverse=True):
    print(f"    {source_type}: {count:,}")

print(f"\n[OK] Export complete! File saved to: {csv_file}")
print(f"     Source URL is in the LAST column (rightmost column)")

