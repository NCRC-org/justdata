#!/usr/bin/env python3
"""Check which datasets contain GLEIF names and credit union data."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.utils.unified_env import ensure_unified_env_loaded
from shared.utils.bigquery_client import get_bigquery_client, execute_query

ensure_unified_env_loaded(verbose=True)

client = get_bigquery_client()

print("=" * 80)
print("DATASET LOCATIONS")
print("=" * 80)

# Check GLEIF names
print("\n1. GLEIF Names:")
try:
    query = "SELECT COUNT(*) as cnt FROM `hdma1-242116.hmda.lender_names_gleif`"
    results = execute_query(client, query)
    count = results[0].get('cnt') if results else 0
    print(f"   Location: hmda.lender_names_gleif")
    print(f"   Records: {count:,}")
except Exception as e:
    print(f"   ERROR: {e}")

# Check credit union branches
print("\n2. Credit Union Branches:")
try:
    query = "SELECT COUNT(*) as cnt FROM `hdma1-242116.credit_unions.cu_branches`"
    results = execute_query(client, query)
    count = results[0].get('cnt') if results else 0
    print(f"   Location: credit_unions.cu_branches")
    print(f"   Records: {count:,}")
except Exception as e:
    print(f"   ERROR: {e}")

# Check credit union call reports
print("\n3. Credit Union Call Reports:")
try:
    query = "SELECT COUNT(*) as cnt FROM `hdma1-242116.credit_unions.cu_call_reports`"
    results = execute_query(client, query)
    count = results[0].get('cnt') if results else 0
    print(f"   Location: credit_unions.cu_call_reports")
    print(f"   Records: {count:,}")
except Exception as e:
    print(f"   ERROR: {e}")

# Check what's in justdata dataset
print("\n4. JustData Dataset:")
try:
    # List tables in justdata
    datasets = list(client.list_datasets())
    justdata_dataset = None
    for d in datasets:
        if d.dataset_id == 'justdata':
            justdata_dataset = d
            break
    
    if justdata_dataset:
        tables = list(client.list_tables(justdata_dataset))
        print(f"   Tables in justdata dataset ({len(tables)}):")
        for table in tables[:20]:  # Show first 20
            print(f"     - {table.table_id}")
        if len(tables) > 20:
            print(f"     ... and {len(tables) - 20} more")
    else:
        print("   Dataset 'justdata' not found")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("GLEIF names: hmda.lender_names_gleif (NOT in justdata)")
print("Credit union branches: credit_unions.cu_branches (NOT in justdata)")
print("Credit union call reports: credit_unions.cu_call_reports (NOT in justdata)")

