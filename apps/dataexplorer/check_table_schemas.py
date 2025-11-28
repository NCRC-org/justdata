#!/usr/bin/env python3
"""
Check the actual schema of branch and census tables in BigQuery.
This will help us verify the correct column names.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from apps.dataexplorer.config import DataExplorerConfig
from apps.dataexplorer.data_utils import get_bigquery_client

def check_table_schema(project_id, dataset, table_name):
    """Get the schema for a BigQuery table."""
    client = get_bigquery_client()
    table_ref = client.dataset(dataset).table(table_name)
    
    try:
        table = client.get_table(table_ref)
        return table.schema
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None

def print_schema_info(project_id, dataset, table_name, description):
    """Print schema information for a table."""
    print(f"\n{'=' * 80}")
    print(f"{description}")
    print(f"Table: `{project_id}.{dataset}.{table_name}`")
    print(f"{'=' * 80}")
    
    schema = check_table_schema(project_id, dataset, table_name)
    
    if schema:
        print(f"\nColumns ({len(schema)} total):")
        print("-" * 80)
        
        # Group columns by category for easier reading
        key_columns = []
        data_columns = []
        other_columns = []
        
        for field in schema:
            col_info = {
                'name': field.name,
                'type': field.field_type,
                'mode': field.mode
            }
            
            # Categorize columns
            if field.name in ['year', 'geoid5', 'rssd', 'bank_name', 'branch_name', 'geoid', 'census_tract']:
                key_columns.append(col_info)
            elif field.name in ['br_lmi', 'br_minority', 'cr_minority', 'deposits_000s', 'income_level', 'total_persons', 'total_white']:
                data_columns.append(col_info)
            else:
                other_columns.append(col_info)
        
        if key_columns:
            print("\n[KEY] Key Columns:")
            for col in key_columns:
                mode_str = f" ({col['mode']})" if col['mode'] != 'NULLABLE' else ""
                print(f"  - {col['name']:<30} {col['type']:<15}{mode_str}")
        
        if data_columns:
            print("\n[DATA] Data Columns:")
            for col in data_columns:
                mode_str = f" ({col['mode']})" if col['mode'] != 'NULLABLE' else ""
                print(f"  - {col['name']:<30} {col['type']:<15}{mode_str}")
        
        if other_columns:
            print(f"\n[OTHER] Other Columns ({len(other_columns)}):")
            for col in other_columns[:10]:  # Show first 10
                mode_str = f" ({col['mode']})" if col['mode'] != 'NULLABLE' else ""
                print(f"  - {col['name']:<30} {col['type']:<15}{mode_str}")
            if len(other_columns) > 10:
                print(f"  ... and {len(other_columns) - 10} more")
        
        # Check for specific columns we care about
        column_names = [f.name for f in schema]
        print(f"\n[CHECK] Column Checks:")
        print(f"  br_minority: {'YES' if 'br_minority' in column_names else 'NO'}")
        print(f"  cr_minority: {'YES' if 'cr_minority' in column_names else 'NO'}")
        print(f"  geoid: {'YES' if 'geoid' in column_names else 'NO'}")
        print(f"  census_tract: {'YES' if 'census_tract' in column_names else 'NO'}")
        print(f"  br_lmi: {'YES' if 'br_lmi' in column_names else 'NO'}")
    else:
        print("  [ERROR] Could not retrieve schema")

def main():
    """Check schemas for all relevant tables."""
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    branches_dataset = DataExplorerConfig.BRANCHES_DATASET
    geo_dataset = DataExplorerConfig.GEO_DATASET
    
    print("=" * 80)
    print("BIGQUERY TABLE SCHEMA CHECKER")
    print("=" * 80)
    print(f"\nProject: {project_id}")
    print(f"Branches Dataset: {branches_dataset}")
    print(f"Geo Dataset: {geo_dataset}")
    
    # Check branch tables
    print_schema_info(project_id, branches_dataset, 'sod_legacy', 'SOD Legacy Table (Years < 2025)')
    print_schema_info(project_id, branches_dataset, DataExplorerConfig.BRANCHES_TABLE, 'SOD25 Table (Year >= 2025)')
    
    # Check census table
    print_schema_info(project_id, geo_dataset, DataExplorerConfig.GEO_CENSUS_TABLE, 'Census Tract Table')
    
    print("\n" + "=" * 80)
    print("SCHEMA CHECK COMPLETE")
    print("=" * 80)
    print("\nRecommendations:")
    print("1. Update BRANCH_TABLE_SCHEMA.md with the actual column names")
    print("2. Update all queries to use the correct column names")
    print("3. Use this script to verify before making schema assumptions")

if __name__ == '__main__':
    main()

