"""Review the enrichment files to understand what has been done"""
import json
import csv
from pathlib import Path
from collections import Counter

# File paths
backup_dir = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\#Cursor Agent Backups")
all_contacts_file = backup_dir / "all_contacts.json"
enriched_contacts_file = backup_dir / "all_contacts_enriched.json"
csv_export_file = backup_dir / "contacts_export.csv"

print("="*80)
print("ENRICHMENT FILES REVIEW")
print("="*80)
print()

# 1. Review all_contacts.json
print("1. ORIGINAL CONTACTS FILE (all_contacts.json)")
print("-" * 80)
if all_contacts_file.exists():
    with open(all_contacts_file, 'r', encoding='utf-8') as f:
        all_contacts = json.load(f)
    
    print(f"   Total records: {len(all_contacts):,}")
    if all_contacts:
        print(f"   Sample record keys ({len(all_contacts[0].keys())} total):")
        for i, key in enumerate(list(all_contacts[0].keys())[:20], 1):
            print(f"     {i}. {key}")
        if len(all_contacts[0].keys()) > 20:
            print(f"     ... and {len(all_contacts[0].keys()) - 20} more")
        
        # Show sample record structure
        print(f"\n   Sample record (first contact):")
        sample = all_contacts[0]
        for key in list(sample.keys())[:10]:
            value = sample[key]
            if isinstance(value, (dict, list)):
                print(f"     {key}: {type(value).__name__} ({len(value) if isinstance(value, (dict, list)) else 'N/A'})")
            else:
                val_str = str(value)[:60] if value else "None"
                print(f"     {key}: {val_str}")
else:
    print("   [FILE NOT FOUND]")
print()

# 2. Review all_contacts_enriched.json
print("2. ENRICHED CONTACTS FILE (all_contacts_enriched.json)")
print("-" * 80)
if enriched_contacts_file.exists():
    with open(enriched_contacts_file, 'r', encoding='utf-8') as f:
        enriched_contacts = json.load(f)
    
    print(f"   Total records: {len(enriched_contacts):,}")
    if enriched_contacts:
        print(f"   Sample record keys ({len(enriched_contacts[0].keys())} total):")
        for i, key in enumerate(list(enriched_contacts[0].keys())[:25], 1):
            print(f"     {i}. {key}")
        if len(enriched_contacts[0].keys()) > 25:
            print(f"     ... and {len(enriched_contacts[0].keys()) - 25} more")
        
        # Compare with original
        if all_contacts_file.exists() and all_contacts:
            original_keys = set(all_contacts[0].keys())
            enriched_keys = set(enriched_contacts[0].keys())
            new_keys = enriched_keys - original_keys
            print(f"\n   NEW KEYS ADDED BY ENRICHMENT ({len(new_keys)} total):")
            for i, key in enumerate(sorted(new_keys)[:30], 1):
                print(f"     {i}. {key}")
            if len(new_keys) > 30:
                print(f"     ... and {len(new_keys) - 30} more")
        
        # Check for enrichment-specific fields
        sample_enriched = enriched_contacts[0]
        enrichment_indicators = [
            'propublica', 'guidestar', 'nccs', 'website', 'staff', 
            'enrichment', 'form_990', 'ein', 'ntee', 'mission'
        ]
        found_enrichment = []
        for key in sample_enriched.keys():
            key_lower = key.lower()
            if any(indicator in key_lower for indicator in enrichment_indicators):
                found_enrichment.append(key)
        
        if found_enrichment:
            print(f"\n   ENRICHMENT-RELATED FIELDS FOUND:")
            for key in found_enrichment[:20]:
                value = sample_enriched[key]
                if isinstance(value, (dict, list)):
                    print(f"     {key}: {type(value).__name__} ({len(value) if isinstance(value, (dict, list)) else 'N/A'})")
                else:
                    val_str = str(value)[:60] if value else "None"
                    print(f"     {key}: {val_str}")
else:
    print("   [FILE NOT FOUND]")
print()

# 3. Review CSV export
print("3. CSV EXPORT FILE (contacts_export.csv)")
print("-" * 80)
if csv_export_file.exists():
    with open(csv_export_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)
    
    print(f"   Total records: {len(csv_rows):,}")
    if csv_rows:
        print(f"   Columns ({len(csv_rows[0].keys())} total):")
        for i, col in enumerate(list(csv_rows[0].keys())[:25], 1):
            print(f"     {i}. {col}")
        if len(csv_rows[0].keys()) > 25:
            print(f"     ... and {len(csv_rows[0].keys()) - 25} more")
        
        # Check for non-empty values in sample
        print(f"\n   Sample record (first contact) - non-empty fields:")
        sample_csv = csv_rows[0]
        non_empty = {k: v for k, v in sample_csv.items() if v and v.strip()}
        print(f"     {len(non_empty)} out of {len(sample_csv)} fields have data")
        for i, (key, value) in enumerate(list(non_empty.items())[:15], 1):
            val_str = str(value)[:60]
            print(f"     {i}. {key}: {val_str}")
else:
    print("   [FILE NOT FOUND]")
print()

# 4. Comparison Summary
print("4. COMPARISON SUMMARY")
print("-" * 80)
if all_contacts_file.exists() and enriched_contacts_file.exists():
    print(f"   Original records: {len(all_contacts):,}")
    print(f"   Enriched records: {len(enriched_contacts):,}")
    print(f"   Difference: {len(enriched_contacts) - len(all_contacts):,}")
    
    if all_contacts and enriched_contacts:
        original_keys = set(all_contacts[0].keys())
        enriched_keys = set(enriched_contacts[0].keys())
        new_keys = enriched_keys - original_keys
        removed_keys = original_keys - enriched_keys
        
        print(f"\n   Field comparison:")
        print(f"     Original fields: {len(original_keys)}")
        print(f"     Enriched fields: {len(enriched_keys)}")
        print(f"     New fields added: {len(new_keys)}")
        if removed_keys:
            print(f"     Fields removed: {len(removed_keys)}")
        
        # Count records with enrichment data
        enrichment_fields = ['propublica_enrichment', 'website', 'staff', 'form_990']
        enrichment_counts = {}
        for field in enrichment_fields:
            count = sum(1 for record in enriched_contacts if field in record and record[field])
            if count > 0:
                enrichment_counts[field] = count
        
        if enrichment_counts:
            print(f"\n   Records with enrichment data:")
            for field, count in enrichment_counts.items():
                pct = (count / len(enriched_contacts)) * 100
                print(f"     {field}: {count:,} ({pct:.1f}%)")
print()

print("="*80)
print("REVIEW COMPLETE")
print("="*80)

