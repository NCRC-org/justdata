#!/usr/bin/env python3
"""
Script to check for the lenders table in BigQuery.
"""

import os
import sys

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared.utils.bigquery_client import get_bigquery_client
from apps.lendsight.config import PROJECT_ID

def find_lenders_table():
    """Find the lenders table in the database."""
    try:
        client = get_bigquery_client(PROJECT_ID)
        
        # Try to find tables with "lender" in the name
        query = f"""
        SELECT 
            table_schema,
            table_name
        FROM `{PROJECT_ID}.INFORMATION_SCHEMA.TABLES`
        WHERE LOWER(table_name) LIKE '%lender%'
        ORDER BY table_schema, table_name
        """
        
        print(f"\nSearching for lender tables in project: {PROJECT_ID}")
        print("=" * 80)
        
        query_job = client.query(query)
        results = query_job.result()
        
        tables = []
        for row in results:
            tables.append(f"{row.table_schema}.{row.table_name}")
            print(f"Found: {row.table_schema}.{row.table_name}")
        
        if not tables:
            print("No tables with 'lender' in name found.")
            print("\nTrying common variations...")
            # Try specific names
            variations = ['lenders18', 'lenders_18', 'lenders', 'lender18', 'lender_18']
            for var in variations:
                for dataset in ['hmda', 'geo', 'justdata']:
                    try:
                        test_query = f"SELECT * FROM `{PROJECT_ID}.{dataset}.{var}` LIMIT 1"
                        test_job = client.query(test_query)
                        test_job.result()
                        print(f"✓ Found: {dataset}.{var}")
                        tables.append(f"{dataset}.{var}")
                    except:
                        pass
        
        if tables:
            # Get schema for the first found table
            table_name = tables[0]
            print(f"\n{'='*80}")
            print(f"Getting schema for: {table_name}")
            print("=" * 80)
            
            parts = table_name.split('.')
            dataset = parts[0]
            table = parts[1]
            
            schema_query = f"""
            SELECT 
                column_name,
                data_type,
                is_nullable
            FROM `{PROJECT_ID}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
            WHERE table_name = '{table}'
            ORDER BY ordinal_position
            """
            
            schema_job = client.query(schema_query)
            schema_results = schema_job.result()
            
            for row in schema_results:
                print(f"{row.column_name:40} | {row.data_type:20} | {row.is_nullable}")
            
            print("=" * 80)
        
        return tables
        
    except Exception as e:
        print(f"Error searching for lenders table: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == '__main__':
    find_lenders_table()

