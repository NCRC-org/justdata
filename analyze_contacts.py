import json
import csv
from pathlib import Path

backup_dir = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups")
all_contacts_file = backup_dir / "all_contacts.json"
enriched_contacts_file = backup_dir / "all_contacts_enriched.json"
csv_export_file = backup_dir / "contacts_export.csv"

print("="*80)
print("CONTACTS DATA ENRICHMENT REVIEW")
print("="*80)
print()

# 1. Original contacts
print("1. ORIGINAL CONTACTS (all_contacts.json)")
print("-" * 80)
if all_contacts_file.exists():
    with open(all_contacts_file, 'r', encoding='utf-8') as f:
        all_contacts = json.load(f)
    print(f"   Records: {len(all_contacts):,}")
    if all_contacts:
        keys = list(all_contacts[0].keys())
        print(f"   Fields: {len(keys)}")
        print(f"   Sample fields: {', '.join(keys[:10])}")
        if len(keys) > 10:
            print(f"   ... and {len(keys)-10} more")
else:
    print("   [NOT FOUND]")
print()

# 2. Enriched contacts
print("2. ENRICHED CONTACTS (all_contacts_enriched.json)")
print("-" * 80)
if enriched_contacts_file.exists():
    with open(enriched_contacts_file, 'r', encoding='utf-8') as f:
        enriched_contacts = json.load(f)
    print(f"   Records: {len(enriched_contacts):,}")
    if enriched_contacts:
        keys = list(enriched_contacts[0].keys())
        print(f"   Fields: {len(keys)}")
        print(f"   Sample fields: {', '.join(keys[:15])}")
        if len(keys) > 15:
            print(f"   ... and {len(keys)-15} more")
        
        # Find enrichment fields
        if all_contacts_file.exists() and all_contacts:
            orig_keys = set(all_contacts[0].keys())
            enr_keys = set(enriched_contacts[0].keys())
            new_keys = sorted(enr_keys - orig_keys)
            print(f"\n   NEW FIELDS ADDED: {len(new_keys)}")
            for key in new_keys[:20]:
                print(f"     - {key}")
            if len(new_keys) > 20:
                print(f"     ... and {len(new_keys)-20} more")
        
        # Check enrichment data presence
        sample = enriched_contacts[0]
        enrichment_fields = {
            'propublica': 'propublica' in str(sample.keys()).lower(),
            'website': 'website' in sample,
            'staff': 'staff' in sample,
            'form_990': 'form_990' in sample,
            'ein': 'ein' in sample,
            'guidestar': 'guidestar' in str(sample.keys()).lower(),
        }
        print(f"\n   ENRICHMENT DATA PRESENT:")
        for field, present in enrichment_fields.items():
            if present:
                val = sample.get(field, 'N/A')
                if isinstance(val, dict):
                    print(f"     {field}: dict with {len(val)} keys")
                elif isinstance(val, list):
                    print(f"     {field}: list with {len(val)} items")
                else:
                    print(f"     {field}: {str(val)[:50]}")
else:
    print("   [NOT FOUND]")
print()

# 3. CSV Export
print("3. CSV EXPORT (contacts_export.csv)")
print("-" * 80)
if csv_export_file.exists():
    with open(csv_export_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)
    print(f"   Records: {len(csv_rows):,}")
    if csv_rows:
        cols = list(csv_rows[0].keys())
        print(f"   Columns: {len(cols)}")
        print(f"   Sample columns: {', '.join(cols[:10])}")
        if len(cols) > 10:
            print(f"   ... and {len(cols)-10} more")
else:
    print("   [NOT FOUND]")
print()

print("="*80)

