"""
Export contacts to CSV with Name, Employer, and Email Address(es).
"""
import json
import csv
from pathlib import Path
from datetime import datetime

# Paths
json_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups\all_contacts_enriched.json")
csv_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups\contacts_export.csv")

print(f"Loading contacts from: {json_file}")

# Try enriched file first, fall back to original
if not json_file.exists():
    json_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups\all_contacts.json")
    print(f"Enriched file not found, using: {json_file}")

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

contacts = data.get('contacts', [])
print(f"Loaded {len(contacts):,} contacts")

# Prepare CSV data
csv_rows = []

for contact in contacts:
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
    
    # Add row
    csv_rows.append({
        'Name': full_name,
        'First Name': first_name,
        'Last Name': last_name,
        'Employer': company,
        'Email Address': emails_str,
        'Primary Email': email,
        'Record ID': str(contact.get('Record ID', '') or '')
    })

# Write CSV
print(f"\nWriting {len(csv_rows):,} contacts to CSV: {csv_file}")

with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
    fieldnames = ['Name', 'First Name', 'Last Name', 'Employer', 'Email Address', 'Primary Email', 'Record ID']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    
    writer.writeheader()
    writer.writerows(csv_rows)

print(f"Successfully exported to: {csv_file}")

# Print summary
contacts_with_emails = sum(1 for row in csv_rows if row['Email Address'])
contacts_with_companies = sum(1 for row in csv_rows if row['Employer'])

print(f"\nSummary:")
print(f"  Total contacts: {len(csv_rows):,}")
print(f"  Contacts with emails: {contacts_with_emails:,}")
print(f"  Contacts with employers: {contacts_with_companies:,}")

