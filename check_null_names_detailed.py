"""Detailed check for contacts with problematic names."""
import json
import csv
from pathlib import Path

csv_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups\contacts_export.csv")
json_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups\all_contacts_enriched.json")

print("=" * 80)
print("DETAILED CHECK - CSV FILE")
print("=" * 80)

# Check CSV for various name issues
issues = {
    'empty_name': [],
    'whitespace_only': [],
    'null_string': [],
    'nan_string': [],
    'very_short': []
}

with open(csv_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row.get('Name', '')
        first = row.get('First Name', '')
        last = row.get('Last Name', '')
        email = row.get('Email Address', '').strip()
        
        if not email:
            continue
        
        # Check various problematic patterns
        if not name or name.strip() == '':
            issues['empty_name'].append(row)
        elif name.strip().lower() in ['null', 'none', 'nan', 'n/a', 'na']:
            issues['null_string'].append(row)
        elif name.strip() == ' ' or len(name.strip()) < 2:
            issues['whitespace_only'].append(row)
        elif len(name.strip()) < 5:
            issues['very_short'].append(row)

print(f"\nEmpty/Null names with emails: {len(issues['empty_name'])}")
print(f"Null/None/Nan string names: {len(issues['null_string'])}")
print(f"Whitespace-only names: {len(issues['whitespace_only'])}")
print(f"Very short names (<5 chars): {len(issues['very_short'])}")

# Show examples
all_issues = issues['empty_name'] + issues['null_string'] + issues['whitespace_only']
if all_issues:
    print(f"\nExamples of problematic entries:")
    for i, row in enumerate(all_issues[:20], 1):
        print(f"  {i}. Name: '{row.get('Name', '')}' | First: '{row.get('First Name', '')}' | Last: '{row.get('Last Name', '')}' | Email: {row.get('Email Address', '')} | Employer: {row.get('Employer', '')}")

print("\n" + "=" * 80)
print("CHECKING JSON SOURCE")
print("=" * 80)

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Check JSON for similar issues
json_issues = []
for contact in data.get('contacts', []):
    first = str(contact.get('First Name', '') or '').strip()
    last = str(contact.get('Last Name', '') or '').strip()
    email = str(contact.get('Email', '') or '').strip()
    
    if not email:
        continue
    
    full_name = f"{first} {last}".strip()
    
    # Check if name is problematic
    if (not first and not last) or \
       full_name.lower() in ['null', 'none', 'nan', 'n/a', 'na', ''] or \
       len(full_name) < 2:
        json_issues.append({
            'first': first,
            'last': last,
            'email': email,
            'company': contact.get('Associated Company', ''),
            'id': contact.get('Record ID', ''),
            'source': contact.get('Email_Source', 'N/A'),
            'all_keys': list(contact.keys())
        })

print(f"\nFound {len(json_issues)} contacts in JSON with problematic names:")
for i, issue in enumerate(json_issues[:20], 1):
    print(f"  {i}. First: '{issue['first']}' | Last: '{issue['last']}' | Email: {issue['email']}")
    print(f"     Company: {issue['company']} | ID: {issue['id']} | Source: {issue['source']}")















