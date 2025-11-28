#!/usr/bin/env python3
"""Simple schema checker using BigQuery INFORMATION_SCHEMA."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from apps.dataexplorer.config import DataExplorerConfig
from apps.dataexplorer.data_utils import get_bigquery_client, execute_query

def check_table_columns(project_id, dataset, table_name):
    """Get column names for a table using INFORMATION_SCHEMA."""
    query = f"""
    SELECT column_name, data_type, is_nullable
    FROM `{project_id}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
    WHERE table_name = '{table_name}'
    ORDER BY ordinal_position
    """
    
    try:
        results = execute_query(query)
        return results
    except Exception as e:
        print(f"  Error querying schema: {e}")
        return None

def print_table_schema(project_id, dataset, table_name, description):
    """Print schema for a table."""
    print(f"\n{'=' * 80}")
    print(f"{description}")
    print(f"Table: {project_id}.{dataset}.{table_name}")
    print(f"{'=' * 80}")
    
    columns = check_table_columns(project_id, dataset, table_name)
    
    if columns:
        column_names = [row['column_name'] for row in columns]
        
        print(f"\nTotal columns: {len(columns)}")
        print("\nAll columns:")
        for row in columns:
            nullable = "NULLABLE" if row.get('is_nullable') == 'YES' else "REQUIRED"
            print(f"  {row['column_name']:<30} {row['data_type']:<15} {nullable}")
        
        print("\n[CHECK] Key columns we care about:")
        checks = ['br_minority', 'cr_minority', 'geoid', 'census_tract', 'br_lmi']
        for col in checks:
            status = "YES" if col in column_names else "NO"
            print(f"  {col:<20} {status}")
    else:
        print("  [ERROR] Could not retrieve schema")

def main():
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    
    print("=" * 80)
    print("BIGQUERY TABLE SCHEMA CHECKER")
    print("=" * 80)
    
    # Check branch tables
    print_table_schema(project_id, 'branches', 'sod_legacy', 'SOD Legacy Table (Years < 2025)')
    print_table_schema(project_id, 'branches', 'sod25', 'SOD25 Table (Year >= 2025)')
    
    # Check census table
    print_table_schema(project_id, 'geo', 'census', 'Census Tract Table')
    
    print("\n" + "=" * 80)
    print("SCHEMA CHECK COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()

