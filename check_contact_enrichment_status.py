"""Check the status of contact enrichment files"""
import json
import csv
from pathlib import Path

backup_dir = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups")
all_contacts_file = backup_dir / "all_contacts.json"
enriched_contacts_file = backup_dir / "all_contacts_enriched.json"
csv_export_file = backup_dir / "contacts_export.csv"

print("="*80)
print("CONTACT ENRICHMENT STATUS CHECK")
print("="*80)
print()

# Check original file
print("1. ORIGINAL CONTACTS FILE")
print("-" * 80)
if all_contacts_file.exists():
    with open(all_contacts_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict) and 'contacts' in data:
        contacts = data['contacts']
        total = data.get('total_contacts', len(contacts))
    else:
        contacts = data if isinstance(data, list) else []
        total = len(contacts)
    
    print(f"   File: {all_contacts_file.name}")
    print(f"   Exists: YES")
    print(f"   Total contacts: {total:,}")
    
    if contacts:
        # Count contacts with/without emails
        with_email = 0
        without_email = 0
        for contact in contacts[:1000]:  # Sample first 1000
            email = contact.get('Email', '') or contact.get('email', '')
            if email and str(email).strip() and str(email).lower() not in ['nan', 'none', 'null', '']:
                with_email += 1
            else:
                without_email += 1
        
        # Extrapolate if we sampled
        if len(contacts) > 1000:
            ratio = len(contacts) / 1000
            with_email = int(with_email * ratio)
            without_email = int(without_email * ratio)
        else:
            with_email = sum(1 for c in contacts if c.get('Email') or c.get('email'))
            without_email = total - with_email
        
        print(f"   Contacts with email: {with_email:,} ({with_email/total*100:.1f}%)")
        print(f"   Contacts without email: {without_email:,} ({without_email/total*100:.1f}%)")
        
        # Show sample fields
        if contacts:
            keys = list(contacts[0].keys())
            print(f"   Fields per contact: {len(keys)}")
            print(f"   Sample fields: {', '.join(keys[:8])}")
else:
    print(f"   File: {all_contacts_file.name}")
    print(f"   Exists: NO")
print()

# Check enriched file
print("2. ENRICHED CONTACTS FILE")
print("-" * 80)
if enriched_contacts_file.exists():
    with open(enriched_contacts_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict) and 'contacts' in data:
        contacts = data['contacts']
        total = data.get('total_contacts', len(contacts))
    else:
        contacts = data if isinstance(data, list) else []
        total = len(contacts)
    
    print(f"   File: {enriched_contacts_file.name}")
    print(f"   Exists: YES")
    print(f"   Total contacts: {total:,}")
    
    if contacts:
        # Count enrichment status
        with_email = 0
        without_email = 0
        enriched_count = 0
        search_statuses = {}
        
        for contact in contacts[:1000]:  # Sample
            email = contact.get('Email', '') or contact.get('email', '')
            if email and str(email).strip() and str(email).lower() not in ['nan', 'none', 'null', '']:
                with_email += 1
            else:
                without_email += 1
            
            # Check for enrichment indicators
            if 'Email_Search_Status' in contact:
                enriched_count += 1
                status = contact.get('Email_Search_Status', 'Unknown')
                search_statuses[status] = search_statuses.get(status, 0) + 1
        
        # Extrapolate
        if len(contacts) > 1000:
            ratio = len(contacts) / 1000
            with_email = int(with_email * ratio)
            without_email = int(without_email * ratio)
            enriched_count = int(enriched_count * ratio)
        else:
            with_email = sum(1 for c in contacts if c.get('Email') or c.get('email'))
            without_email = total - with_email
            enriched_count = sum(1 for c in contacts if 'Email_Search_Status' in c)
        
        print(f"   Contacts with email: {with_email:,} ({with_email/total*100:.1f}%)")
        print(f"   Contacts without email: {without_email:,} ({without_email/total*100:.1f}%)")
        print(f"   Contacts processed for enrichment: {enriched_count:,}")
        
        if search_statuses:
            print(f"\n   Enrichment Status Breakdown:")
            for status, count in sorted(search_statuses.items()):
                print(f"     {status}: {count:,}")
        
        # Compare with original
        if all_contacts_file.exists():
            print(f"\n   Comparison with original:")
            print(f"     Original total: {total:,}")
            print(f"     Enriched total: {total:,}")
            if contacts:
                orig_keys = set(contacts[0].keys()) if contacts else set()
                # Try to get original keys
                try:
                    with open(all_contacts_file, 'r', encoding='utf-8') as f:
                        orig_data = json.load(f)
                    if isinstance(orig_data, dict) and 'contacts' in orig_data:
                        orig_contacts = orig_data['contacts']
                    else:
                        orig_contacts = orig_data if isinstance(orig_data, list) else []
                    if orig_contacts:
                        orig_keys = set(orig_contacts[0].keys())
                        enr_keys = set(contacts[0].keys())
                        new_keys = enr_keys - orig_keys
                        print(f"     New fields added: {len(new_keys)}")
                        if new_keys:
                            print(f"       Sample: {', '.join(list(new_keys)[:5])}")
                except:
                    pass
else:
    print(f"   File: {enriched_contacts_file.name}")
    print(f"   Exists: NO")
    print(f"   Status: Enrichment has NOT been run yet")
print()

# Check CSV export
print("3. CSV EXPORT FILE")
print("-" * 80)
if csv_export_file.exists():
    with open(csv_export_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)
    
    print(f"   File: {csv_export_file.name}")
    print(f"   Exists: YES")
    print(f"   Total rows: {len(csv_rows):,}")
    
    if csv_rows:
        with_email = sum(1 for row in csv_rows if row.get('Email Address', '').strip())
        with_employer = sum(1 for row in csv_rows if row.get('Employer', '').strip())
        
        print(f"   Rows with email: {with_email:,} ({with_email/len(csv_rows)*100:.1f}%)")
        print(f"   Rows with employer: {with_employer:,} ({with_employer/len(csv_rows)*100:.1f}%)")
        print(f"   Columns: {', '.join(csv_rows[0].keys())}")
else:
    print(f"   File: {csv_export_file.name}")
    print(f"   Exists: NO")
    print(f"   Status: CSV export has NOT been run yet")
print()

# Summary
print("="*80)
print("SUMMARY")
print("="*80)

if all_contacts_file.exists() and enriched_contacts_file.exists():
    print("[OK] Contact enrichment files exist")
    print("     - Original contacts: Available")
    print("     - Enriched contacts: Available")
    if csv_export_file.exists():
        print("     - CSV export: Available")
    else:
        print("     - CSV export: Missing (run export_contacts_to_csv.py)")
elif all_contacts_file.exists():
    print("[ACTION NEEDED] Original contacts exist but enrichment not run")
    print("     - Run: python find_missing_emails.py")
else:
    print("[ERROR] Original contacts file not found")
    print("     - Need to export contacts from HubSpot first")

print("="*80)

