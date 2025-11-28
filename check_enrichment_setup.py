"""Quick script to verify enrichment setup"""
from pathlib import Path
import json

# Check input file
input_file = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\enriched_members_cleaned_final.json")
output_file = Path(r"C:\dream\#JustData_Repo\enriched_members_propublica_enhanced.json")
checkpoint_file = Path(r"C:\dream\#JustData_Repo\propublica_enrichment_checkpoint.json")

print("="*80)
print("ENRICHMENT SETUP VERIFICATION")
print("="*80)
print()

# Check input file
print(f"Input file: {input_file}")
print(f"  Exists: {input_file.exists()}")
if input_file.exists():
    size_mb = input_file.stat().st_size / (1024*1024)
    print(f"  Size: {size_mb:.2f} MB")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"  Records: {len(data):,}")
        # Check a sample record for EIN
        if len(data) > 0:
            sample = data[0]
            org_data = sample.get('form_990', {}).get('organization', {})
            ein = org_data.get('ein') or org_data.get('strein')
            print(f"  Sample EIN: {ein if ein else 'NOT FOUND'}")
    except Exception as e:
        print(f"  ERROR reading file: {e}")
else:
    print("  ⚠️  INPUT FILE NOT FOUND - Enrichment cannot proceed!")
print()

# Check output directory
print(f"Output file: {output_file}")
print(f"  Directory exists: {output_file.parent.exists()}")
if output_file.exists():
    size_mb = output_file.stat().st_size / (1024*1024)
    print(f"  Output file exists: YES ({size_mb:.2f} MB)")
else:
    print(f"  Output file exists: NO (will be created)")
print()

# Check checkpoint
print(f"Checkpoint file: {checkpoint_file}")
if checkpoint_file.exists():
    try:
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)
        processed = checkpoint.get('processed', 0)
        print(f"  Exists: YES")
        print(f"  Processed records: {processed:,}")
        print(f"  Can resume from: Record {processed}")
    except Exception as e:
        print(f"  ERROR reading checkpoint: {e}")
else:
    print(f"  Exists: NO (will start from beginning)")
print()

print("="*80)
if input_file.exists():
    print("[OK] Setup looks good! Ready to run enrichment.")
else:
    print("[ERROR] Setup incomplete - Input file not found!")
print("="*80)

