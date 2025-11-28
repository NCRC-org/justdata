#!/usr/bin/env python3
"""
Script to check the schema of BigQuery tables to see available columns.
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.utils.bigquery_client import get_bigquery_client
from apps.branchseeker.config import PROJECT_ID

def get_table_schema(table_name):
    """Get all column names from a BigQuery table."""
    try:
        client = get_bigquery_client(PROJECT_ID)
        
        # Query to get column information from INFORMATION_SCHEMA
        query = f"""
        SELECT 
            column_name,
            data_type,
            is_nullable
        FROM `{PROJECT_ID}.branches.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position
        """
        
        print(f"\nQuerying schema for table: branches.{table_name}")
        print("=" * 60)
        
        query_job = client.query(query)
        results = query_job.result()
        
        columns = []
        for row in results:
            columns.append({
                'name': row.column_name,
                'type': row.data_type,
                'nullable': row.is_nullable
            })
            print(f"{row.column_name:30} | {row.data_type:15} | {row.is_nullable}")
        
        print("=" * 60)
        print(f"\nTotal columns: {len(columns)}")
        
        return columns
        
    except Exception as e:
        print(f"Error querying schema: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback: try to get schema by querying the table directly
        print("\nTrying alternative method: querying table directly...")
        try:
            query = f"SELECT * FROM `{PROJECT_ID}.branches.{table_name}` LIMIT 0"
            query_job = client.query(query)
            schema = query_job.schema
            
            print(f"\nColumns from table schema (branches.{table_name}):")
            print("=" * 60)
            for field in schema:
                print(f"{field.name:30} | {field.field_type}")
            print("=" * 60)
            print(f"\nTotal columns: {len(schema)}")
            
            return [{'name': field.name, 'type': field.field_type} for field in schema]
        except Exception as e2:
            print(f"Alternative method also failed: {e2}")
            return []

if __name__ == '__main__':
    # Check all three tables
    tables = ['sod', 'sod_legacy', 'sod25']
    
    for table in tables:
        print(f"\n{'='*60}")
        print(f"TABLE: branches.{table}")
        print('='*60)
        columns = get_table_schema(table)
        
        if columns:
            print(f"\nColumn names only:")
            print(", ".join([col['name'] for col in columns]))

