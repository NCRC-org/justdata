"""
Enrich member data with ProPublica API data
Uses subprocess workaround and C:\dream path to avoid PowerShell issues
"""
import json
import urllib.request
import urllib.parse
import time
from pathlib import Path
from datetime import datetime
import sys

# Configuration
BASE_URL = "https://projects.propublica.org/nonprofits/api/v2/search.json"
INPUT_FILE = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\enriched_members_cleaned_final.json")
OUTPUT_FILE = Path(r"C:\dream\#JustData_Repo\enriched_members_propublica_enhanced.json")
CHECKPOINT_FILE = Path(r"C:\dream\#JustData_Repo\propublica_enrichment_checkpoint.json")
RATE_LIMIT_DELAY = 1.0  # Seconds between API calls (be respectful)

# Fields to add from ProPublica API
FIELDS_TO_ADD = [
    'guidestar_url',
    'nccs_url', 
    'updated',
    'address',
    'zipcode',
    # Additional EO-BMF fields that might be useful
    'classification',
    'ruling_date',
    'deductibility',
    'foundation',
    'activity',
    'asset_cd',
    'income_cd',
    'filing_req_cd',
    'pf_filing_req_cd',
    'subsection',
    'affiliation',
    'ruling',
    'exempt_cd',
    'foundation_cd',
    'status_cd',
    'tax_period',
    'asset_amt',
    'income_amt',
    'revenue_amt',
    'ntee1',
    'ntee2',
    'ntee3',
]

def load_checkpoint():
    """Load checkpoint to resume from where we left off"""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
            print(f"✓ Loaded checkpoint: {checkpoint.get('processed', 0)} records processed")
            return checkpoint.get('processed', 0), checkpoint.get('failed_eins', [])
        except Exception as e:
            print(f"⚠ Could not load checkpoint: {e}")
            return 0, []
    return 0, []

def save_checkpoint(processed_count, failed_eins):
    """Save checkpoint"""
    checkpoint = {
        'processed': processed_count,
        'failed_eins': failed_eins,
        'timestamp': datetime.now().isoformat()
    }
    try:
        with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, indent=2)
    except Exception as e:
        print(f"⚠ Could not save checkpoint: {e}")

def query_propublica_api(ein):
    """
    Query ProPublica API for an EIN
    Returns organization data or None if not found/error
    """
    # Use strein format if available, otherwise format the ein
    if isinstance(ein, int):
        strein = f"{ein:09d}"
        strein = f"{strein[:2]}-{strein[2:]}"
    else:
        strein = str(ein)
    
    params = {'q': strein}
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.loads(response.read().decode())
        
        if data.get('organizations') and len(data['organizations']) > 0:
            return data['organizations'][0]
        return None
        
    except urllib.error.HTTPError as e:
        if e.code == 429:  # Rate limited
            print(f"  ⚠ Rate limited, waiting 5 seconds...")
            time.sleep(5)
            return query_propublica_api(ein)  # Retry once
        print(f"  ✗ HTTP Error {e.code}: {e.reason}")
        return None
    except Exception as e:
        print(f"  ✗ Error querying API: {type(e).__name__}: {e}")
        return None

def enrich_record(record):
    """
    Enrich a single record with ProPublica API data
    Returns enriched record and success status
    """
    # Extract EIN from the record
    org_data = record.get('form_990', {}).get('organization', {})
    ein = org_data.get('ein') or org_data.get('strein')
    
    if not ein:
        return record, False
    
    # Query API
    api_data = query_propublica_api(ein)
    
    if not api_data:
        return record, False
    
    # Create enrichment section if it doesn't exist
    if 'propublica_enrichment' not in record:
        record['propublica_enrichment'] = {}
    
    # Add new fields
    enrichment = record['propublica_enrichment']
    enrichment['enriched_at'] = datetime.now().isoformat()
    enrichment['api_source'] = 'ProPublica Nonprofit Explorer API v2'
    
    # Add fields that aren't already in the organization data
    for field in FIELDS_TO_ADD:
        if field in api_data and api_data[field] is not None:
            # Only add if not already present or if new value is different/better
            if field not in org_data or org_data[field] is None:
                enrichment[field] = api_data[field]
    
    # Add all other fields from API that might be useful
    for key, value in api_data.items():
        if key not in ['ein', 'strein', 'name'] and value is not None:
            if key not in enrichment and key not in org_data:
                enrichment[key] = value
    
    # Update organization data with any missing fields
    for field in ['address', 'zipcode', 'updated']:
        if field in api_data and api_data[field] and (not org_data.get(field)):
            org_data[field] = api_data[field]
    
    # Add external links
    if 'guidestar_url' in api_data and api_data['guidestar_url']:
        enrichment['guidestar_url'] = api_data['guidestar_url']
    if 'nccs_url' in api_data and api_data['nccs_url']:
        enrichment['nccs_url'] = api_data['nccs_url']
    
    return record, True

def main():
    """Main enrichment process"""
    print("="*80)
    print("PROPUBLICA API ENRICHMENT")
    print("="*80)
    print(f"Input file: {INPUT_FILE}")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Checkpoint file: {CHECKPOINT_FILE}")
    print("="*80)
    print()
    
    # Load data
    print("Loading data file...")
    if not INPUT_FILE.exists():
        print(f"✗ ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"✗ ERROR: Could not load input file: {e}")
        sys.exit(1)
    
    total_records = len(data)
    print(f"✓ Loaded {total_records:,} records")
    print()
    
    # Load checkpoint
    start_index, failed_eins = load_checkpoint()
    if start_index > 0:
        print(f"Resuming from record {start_index:,}")
        print()
    
    # Process records
    enriched_count = 0
    skipped_count = 0
    error_count = 0
    
    print("Starting enrichment process...")
    print(f"Rate limit delay: {RATE_LIMIT_DELAY} seconds between calls")
    print("-" * 80)
    
    for i, record in enumerate(data[start_index:], start=start_index):
        # Progress indicator
        if (i + 1) % 100 == 0:
            progress = ((i + 1) / total_records) * 100
            print(f"\nProgress: {i + 1:,}/{total_records:,} ({progress:.1f}%)")
            print(f"  Enriched: {enriched_count:,} | Skipped: {skipped_count:,} | Errors: {error_count:,}")
            save_checkpoint(i + 1, failed_eins)
        
        # Extract EIN
        org_data = record.get('form_990', {}).get('organization', {})
        ein = org_data.get('ein') or org_data.get('strein')
        company_name = record.get('company_name', 'Unknown')
        
        if not ein:
            skipped_count += 1
            continue
        
        # Enrich record
        try:
            enriched_record, success = enrich_record(record)
            data[i] = enriched_record
            
            if success:
                enriched_count += 1
                if (i + 1) % 10 == 0:
                    print(f"  [{i + 1:,}] ✓ {company_name[:50]} (EIN: {ein})")
            else:
                skipped_count += 1
                failed_eins.append(str(ein))
                if (i + 1) % 10 == 0:
                    print(f"  [{i + 1:,}] - {company_name[:50]} (EIN: {ein}) - No API data")
        except Exception as e:
            error_count += 1
            failed_eins.append(str(ein))
            print(f"  [{i + 1:,}] ✗ Error processing {company_name[:50]}: {e}")
        
        # Rate limiting
        if i < total_records - 1:  # Don't delay after last record
            time.sleep(RATE_LIMIT_DELAY)
    
    # Save results
    print()
    print("="*80)
    print("Saving enriched data...")
    print("="*80)
    
    try:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved enriched data to: {OUTPUT_FILE}")
    except Exception as e:
        print(f"✗ ERROR: Could not save output file: {e}")
        sys.exit(1)
    
    # Final summary
    print()
    print("="*80)
    print("ENRICHMENT COMPLETE")
    print("="*80)
    print(f"Total records processed: {total_records:,}")
    print(f"  ✓ Successfully enriched: {enriched_count:,}")
    print(f"  - Skipped (no EIN/no API data): {skipped_count:,}")
    print(f"  ✗ Errors: {error_count:,}")
    print(f"Success rate: {(enriched_count/total_records*100):.1f}%")
    print()
    print(f"Output file: {OUTPUT_FILE}")
    print("="*80)

if __name__ == "__main__":
    main()
















