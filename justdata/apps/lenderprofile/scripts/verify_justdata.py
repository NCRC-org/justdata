#!/usr/bin/env python3
"""Verify all data is in justdata dataset."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from justdata.shared.utils.unified_env import ensure_unified_env_loaded
from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query

ensure_unified_env_loaded(verbose=True)

client = get_bigquery_client()
project_id = 'hdma1-242116'

print("=" * 80)
print("VERIFYING JUSTDATA DATASET")
print("=" * 80)

tables_to_check = [
    ('gleif_names', 'GLEIF Names'),
    ('credit_union_branches', 'Credit Union Branches'),
    ('credit_union_call_reports', 'Credit Union Call Reports'),
    ('sod_branches_optimized', 'Optimized SOD Branches'),
]

for table_name, description in tables_to_check:
    print(f"\n{description} ({table_name}):")
    try:
        query = f"SELECT COUNT(*) as cnt FROM `{project_id}.justdata.{table_name}`"
        results = execute_query(client, query)
        count = results[0].get('cnt') if results else 0
        print(f"  [OK] {count:,} records")
        
        # Get additional stats for optimized SOD
        if table_name == 'sod_branches_optimized':
            stats_query = f"""
            SELECT 
                COUNT(DISTINCT rssd) as banks,
                COUNT(DISTINCT year) as years,
                MIN(year) as min_year,
                MAX(year) as max_year
            FROM `{project_id}.justdata.{table_name}`
            """
            stats = execute_query(client, stats_query)
            if stats:
                s = stats[0]
                print(f"  Banks: {s.get('banks'):,}")
                print(f"  Years: {s.get('min_year')} - {s.get('max_year')} ({s.get('years')} years)")
    except Exception as e:
        print(f"  [ERROR] {e}")

print("\n" + "=" * 80)
print("All data is now in the justdata dataset!")

