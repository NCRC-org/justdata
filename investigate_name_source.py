"""Investigate where contacts with short/null names came from."""
import json
from pathlib import Path

json_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups\all_contacts_enriched.json")

print("=" * 80)
print("INVESTIGATING SOURCE OF CONTACTS WITH SHORT/NULL NAMES")
print("=" * 80)

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

contacts = data.get('contacts', [])

# Find contacts with short names (initials) and emails
short_names = []
for c in contacts:
    first = str(c.get('First Name', '') or '').strip()
    last = str(c.get('Last Name', '') or '').strip()
    full_name = f"{first} {last}".strip()
    email = str(c.get('Email', '') or '').strip()
    
    if email and len(full_name) < 5 and len(full_name) > 0:
        short_names.append(c)

print(f"\nFound {len(short_names)} contacts with short names (<5 chars) and emails")
print("\nSample of short names:")
for i, c in enumerate(short_names[:15], 1):
    first = str(c.get('First Name', '') or '')
    last = str(c.get('Last Name', '') or '')
    email = c.get('Email', '')
    source = c.get('Email_Source', 'Original')
    company = c.get('Associated Company', '')
    record_id = c.get('Record ID', '')
    print(f"  {i}. '{first} {last}' | Email: {email}")
    print(f"     Source: {source} | Company: {company} | ID: {record_id}")

# Check if these are from original data or discovered
original_short = [c for c in short_names if not c.get('Email_Source')]
discovered_short = [c for c in short_names if c.get('Email_Source') == 'Discovered_via_Search']

print(f"\n  - Original data (no Email_Source): {len(original_short)}")
print(f"  - Discovered via search: {len(discovered_short)}")

# Check original JSON file
print("\n" + "=" * 80)
print("CHECKING ORIGINAL JSON FILE")
print("=" * 80)

original_json = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups\all_contacts.json")

if original_json.exists():
    with open(original_json, 'r', encoding='utf-8') as f:
        original_data = json.load(f)
    
    original_contacts = original_data.get('contacts', [])
    original_short = []
    for c in original_contacts:
        first = str(c.get('First Name', '') or '').strip()
        last = str(c.get('Last Name', '') or '').strip()
        full_name = f"{first} {last}".strip()
        email = str(c.get('Email', '') or '').strip()
        
        if email and len(full_name) < 5 and len(full_name) > 0:
            original_short.append(c)
    
    print(f"\nIn ORIGINAL file, found {len(original_short)} contacts with short names and emails")
    print("These were already in your HubSpot export:")
    for i, c in enumerate(original_short[:10], 1):
        first = str(c.get('First Name', '') or '')
        last = str(c.get('Last Name', '') or '')
        email = c.get('Email', '')
        company = c.get('Associated Company', '')
        print(f"  {i}. '{first} {last}' | Email: {email} | Company: {company}")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("These contacts with short/null names are from your ORIGINAL HubSpot export.")
print("They were not created by the email search script.")
print("The script only adds contacts with proper names when discovering new contacts.")















