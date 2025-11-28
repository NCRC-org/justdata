"""Check contacts with very short names."""
import csv
from pathlib import Path

csv_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups\contacts_export.csv")

print("Checking contacts with very short names (<5 characters):")
print("=" * 80)

short_names = []
with open(csv_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row.get('Name', '').strip()
        email = row.get('Email Address', '').strip()
        
        if email and len(name) < 5 and len(name) > 0:
            short_names.append(row)

print(f"\nFound {len(short_names)} contacts with short names (<5 chars) and emails:")
for i, row in enumerate(short_names[:30], 1):
    print(f"  {i}. Name: '{row.get('Name', '')}' ({len(row.get('Name', '').strip())} chars) | First: '{row.get('First Name', '')}' | Last: '{row.get('Last Name', '')}' | Email: {row.get('Email Address', '')} | Employer: {row.get('Employer', '')}")

# Also check for actual null/empty in raw CSV
print("\n" + "=" * 80)
print("Checking for actual null/empty values in raw CSV:")
print("=" * 80)

null_count = 0
with open(csv_file, 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()
    for i, line in enumerate(lines[1:11], 2):  # Skip header, check first 10
        if ',,,' in line or line.startswith(','):
            null_count += 1
            print(f"  Line {i}: {line[:100]}")

print(f"\nAlso checking original JSON for contacts where name fields might be NaN/None:")
import json
json_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups\all_contacts_enriched.json")
with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)
    
    # Check for contacts where name is actually None or NaN in JSON
    problematic = []
    for contact in data.get('contacts', []):
        first = contact.get('First Name')
        last = contact.get('Last Name')
        email = contact.get('Email')
        
        # Check if first/last are actually None (not just empty string)
        if email and (first is None or last is None or 
                     (isinstance(first, float) and str(first) == 'nan') or
                     (isinstance(last, float) and str(last) == 'nan')):
            problematic.append(contact)
    
    print(f"\nFound {len(problematic)} contacts where First/Last Name is None or NaN in JSON:")
    for i, c in enumerate(problematic[:15], 1):
        print(f"  {i}. First: {repr(c.get('First Name'))} | Last: {repr(c.get('Last Name'))} | Email: {c.get('Email')} | ID: {c.get('Record ID')}")















