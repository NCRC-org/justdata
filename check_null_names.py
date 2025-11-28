"""Check for contacts with null names but emails."""
import json
import csv
from pathlib import Path

# Check CSV
csv_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups\contacts_export.csv")
json_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups\all_contacts_enriched.json")

print("=" * 80)
print("CHECKING CSV FILE")
print("=" * 80)

null_names_csv = []
with open(csv_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row.get('Name', '').strip()
        email = row.get('Email Address', '').strip()
        if (not name or name == '') and email:
            null_names_csv.append(row)

print(f"\nFound {len(null_names_csv)} contacts in CSV with null/empty names but emails:")
for i, row in enumerate(null_names_csv[:15], 1):
    print(f"  {i}. Name: '{row.get('Name', '')}' | Email: {row.get('Email Address', '')} | Employer: {row.get('Employer', '')} | ID: {row.get('Record ID', '')}")

print("\n" + "=" * 80)
print("CHECKING JSON FILE")
print("=" * 80)

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

null_names_json = []
for contact in data.get('contacts', []):
    first = str(contact.get('First Name', '') or '').strip()
    last = str(contact.get('Last Name', '') or '').strip()
    email = str(contact.get('Email', '') or '').strip()
    
    if (not first and not last) and email:
        null_names_json.append(contact)

print(f"\nFound {len(null_names_json)} contacts in JSON with null names but emails:")
for i, contact in enumerate(null_names_json[:15], 1):
    print(f"  {i}. First: '{contact.get('First Name', '')}' | Last: '{contact.get('Last Name', '')}' | Email: {contact.get('Email', '')} | Company: {contact.get('Associated Company', '')} | ID: {contact.get('Record ID', '')}")
    print(f"     Source: {contact.get('Email_Source', 'N/A')} | Keys: {list(contact.keys())[:8]}")

# Check if these are discovered contacts
discovered = [c for c in null_names_json if c.get('Email_Source') == 'Discovered_via_Search']
print(f"\n  Of these, {len(discovered)} appear to be discovered contacts (Email_Source: Discovered_via_Search)")















