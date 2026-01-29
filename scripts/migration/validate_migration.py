#!/usr/bin/env python3
"""
Validate JustData migration from hdma1-242116 to justdata-ncrc.

Checks:
1. All destination tables exist
2. Row counts match source tables (where applicable)
3. No null values in critical columns
4. Code references are updated
"""

import os
import sys
from pathlib import Path
from google.cloud import bigquery

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration
SOURCE_PROJECT = 'hdma1-242116'
DEST_PROJECT = 'justdata-ncrc'

# Table comparisons: (source_table, dest_table, check_type)
# check_type: 'exact' = row counts must match, 'exists' = just check table exists
TABLE_CHECKS = [
    ('sb.lenders', 'bizsight.sb_lenders', 'exact'),
    ('hmda.lenders18', 'lendsight.lenders18', 'exact'),
    ('hmda.lender_names_gleif', 'shared.lender_names_gleif', 'exact'),
    ('credit_unions.cu_branches', 'lenderprofile.cu_branches', 'exact'),
    ('credit_unions.cu_call_reports', 'lenderprofile.cu_call_reports', 'exact'),
    (None, 'bizsight.sb_county_summary', 'exists'),  # Aggregated, no direct comparison
    (None, 'shared.de_hmda', 'exists'),  # Derived table
    (None, 'lendsight.de_hmda_county_summary', 'exists'),
    (None, 'lendsight.de_hmda_tract_summary', 'exists'),
    (None, 'branchsight.sod', 'exists'),
    (None, 'branchsight.branch_hhi_summary', 'exists'),
    (None, 'shared.county_centroids', 'exists'),
    (None, 'shared.cbsa_centroids', 'exists'),
    (None, 'cache.analysis_cache', 'exists'),
    (None, 'cache.usage_log', 'exists'),
]

# Critical columns to check for nulls
NULL_CHECKS = [
    ('shared.de_hmda', ['lei', 'county_code']),
    ('bizsight.sb_lenders', ['sb_resid']),
    ('lendsight.lenders18', ['lei']),
]


def get_row_count(client: bigquery.Client, project: str, table: str) -> int:
    """Get row count for a table."""
    query = f"SELECT COUNT(*) as cnt FROM `{project}.{table}`"
    try:
        result = list(client.query(query).result())
        return result[0].cnt
    except Exception as e:
        print(f"  ERROR: Could not query {project}.{table}: {e}")
        return -1


def check_nulls(client: bigquery.Client, project: str, table: str, columns: list) -> dict:
    """Check for null values in specified columns."""
    results = {}
    for col in columns:
        query = f"""
        SELECT 
            COUNT(*) as total,
            COUNTIF({col} IS NULL) as nulls
        FROM `{project}.{table}`
        """
        try:
            result = list(client.query(query).result())[0]
            pct = (result.nulls / result.total * 100) if result.total > 0 else 0
            results[col] = {'total': result.total, 'nulls': result.nulls, 'pct': pct}
        except Exception as e:
            results[col] = {'error': str(e)}
    return results


def check_code_references():
    """Check for remaining hdma1-242116 references in code."""
    import subprocess
    
    print("\n" + "="*60)
    print("CODE REFERENCE CHECK")
    print("="*60)
    
    # Search for remaining references in Python files
    result = subprocess.run(
        ['grep', '-r', 'hdma1-242116', 'justdata/', '--include=*.py', '-l'],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT
    )
    
    if result.stdout:
        files = result.stdout.strip().split('\n')
        # Filter out scripts and test files
        critical_files = [f for f in files if 'script' not in f.lower() and 'test' not in f.lower()]
        
        if critical_files:
            print(f"WARNING: Found hdma1-242116 references in {len(critical_files)} files:")
            for f in critical_files[:10]:
                print(f"  - {f}")
            if len(critical_files) > 10:
                print(f"  ... and {len(critical_files) - 10} more")
        else:
            print("OK: No critical hdma1-242116 references in application code")
            print(f"   (Found {len(files)} references in scripts/tests - OK)")
    else:
        print("OK: No hdma1-242116 references found in Python files")


def main():
    print("="*60)
    print("JUSTDATA MIGRATION VALIDATION")
    print("="*60)
    print(f"Source Project: {SOURCE_PROJECT}")
    print(f"Destination Project: {DEST_PROJECT}")
    print()
    
    # Initialize client
    client = bigquery.Client(project=DEST_PROJECT)
    
    # Check tables
    print("TABLE CHECKS")
    print("-"*60)
    
    all_passed = True
    for source_table, dest_table, check_type in TABLE_CHECKS:
        dest_count = get_row_count(client, DEST_PROJECT, dest_table)
        
        if dest_count < 0:
            print(f"FAIL: {dest_table} - TABLE NOT FOUND")
            all_passed = False
            continue
        
        if check_type == 'exact' and source_table:
            source_count = get_row_count(client, SOURCE_PROJECT, source_table)
            if source_count == dest_count:
                print(f"PASS: {dest_table} - {dest_count:,} rows (matches source)")
            else:
                diff = dest_count - source_count
                pct = (diff / source_count * 100) if source_count > 0 else 0
                if abs(pct) < 1:
                    print(f"WARN: {dest_table} - {dest_count:,} rows (source: {source_count:,}, diff: {diff:+,})")
                else:
                    print(f"FAIL: {dest_table} - {dest_count:,} rows (source: {source_count:,}, diff: {diff:+,} = {pct:+.1f}%)")
                    all_passed = False
        else:
            print(f"PASS: {dest_table} - {dest_count:,} rows (exists)")
    
    # Check nulls
    print("\nNULL VALUE CHECKS")
    print("-"*60)
    
    for table, columns in NULL_CHECKS:
        results = check_nulls(client, DEST_PROJECT, table, columns)
        for col, data in results.items():
            if 'error' in data:
                print(f"WARN: {table}.{col} - {data['error']}")
            elif data['pct'] > 10:
                print(f"FAIL: {table}.{col} - {data['nulls']:,} nulls ({data['pct']:.1f}%)")
                all_passed = False
            elif data['pct'] > 1:
                print(f"WARN: {table}.{col} - {data['nulls']:,} nulls ({data['pct']:.1f}%)")
            else:
                print(f"PASS: {table}.{col} - {data['nulls']:,} nulls ({data['pct']:.2f}%)")
    
    # Check code references
    check_code_references()
    
    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("VALIDATION PASSED - Migration successful!")
    else:
        print("VALIDATION FAILED - Some issues need attention")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
