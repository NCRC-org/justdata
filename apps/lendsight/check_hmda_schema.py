#!/usr/bin/env python3
"""
Script to check the schema of the HMDA BigQuery table to see available columns.
"""

import os
import sys

# Add the project root to the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared.utils.bigquery_client import get_bigquery_client
from apps.lendsight.config import PROJECT_ID, DATASET_ID, TABLE_ID

def get_table_schema():
    """Get all column names from the HMDA BigQuery table."""
    try:
        client = get_bigquery_client(PROJECT_ID)
        
        # Query to get column information from INFORMATION_SCHEMA
        query = f"""
        SELECT 
            column_name,
            data_type,
            is_nullable
        FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = '{TABLE_ID}'
        ORDER BY ordinal_position
        """
        
        print(f"\nQuerying schema for table: {DATASET_ID}.{TABLE_ID}")
        print(f"Project: {PROJECT_ID}")
        print("=" * 80)
        
        query_job = client.query(query)
        results = query_job.result()
        
        columns = []
        for row in results:
            columns.append({
                'name': row.column_name,
                'type': row.data_type,
                'nullable': row.is_nullable
            })
            print(f"{row.column_name:40} | {row.data_type:20} | {row.is_nullable}")
        
        print("=" * 80)
        print(f"\nTotal columns: {len(columns)}")
        
        return columns
        
    except Exception as e:
        print(f"Error querying schema: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback: try to get schema by querying the table directly
        print("\nTrying alternative method: querying table directly...")
        try:
            query = f"SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` LIMIT 0"
            query_job = client.query(query)
            schema = query_job.schema
            
            print(f"\nColumns from table schema ({DATASET_ID}.{TABLE_ID}):")
            print("=" * 80)
            for field in schema:
                nullable = "YES" if field.mode == "NULLABLE" else "NO"
                print(f"{field.name:40} | {field.field_type:20} | {nullable}")
            print("=" * 80)
            print(f"\nTotal columns: {len(schema)}")
            
            return [{'name': field.name, 'type': field.field_type, 'nullable': nullable} for field in schema]
        except Exception as e2:
            print(f"Alternative method also failed: {e2}")
            return []

def test_sample_query():
    """Test a sample query to see what data is available."""
    try:
        client = get_bigquery_client(PROJECT_ID)
        
        query = f"""
        SELECT 
            activity_year,
            COUNT(*) as record_count,
            COUNT(DISTINCT lei) as unique_lenders,
            COUNT(DISTINCT county_code) as unique_counties,
            MIN(activity_year) as min_year,
            MAX(activity_year) as max_year
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        GROUP BY activity_year
        ORDER BY activity_year DESC
        LIMIT 10
        """
        
        print("\n" + "=" * 80)
        print("SAMPLE DATA AVAILABILITY:")
        print("=" * 80)
        
        query_job = client.query(query)
        results = query_job.result()
        
        for row in results:
            print(f"Year {row.activity_year}: {row.record_count:,} records, {row.unique_lenders} lenders, {row.unique_counties} counties")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"Error running sample query: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print(f"\n{'='*80}")
    print(f"HMDA TABLE SCHEMA CHECK")
    print(f"{'='*80}")
    
    columns = get_table_schema()
    
    if columns:
        print(f"\nColumn names only (comma-separated):")
        print(", ".join([col['name'] for col in columns]))
        
        # Show key columns used in our SQL template
        print(f"\n{'='*80}")
        print("KEY COLUMNS USED IN CURRENT SQL TEMPLATE:")
        print("=" * 80)
        key_columns = [
            'activity_year', 'lei', 'county_code', 'geoid5', 'respondent_name',
            'action_taken', 'occupancy_type', 'loan_purpose', 'total_units',
            'construction_method', 'reverse_mortgage', 'loan_amount', 'income',
            'applicant_race_1', 'applicant_ethnicity_1',
            'ffiec_msa_md_median_family_income', 'tract_to_msa_income_percentage',
            'tract_minority_population_percent'
        ]
        
        for col_name in key_columns:
            found = [c for c in columns if c['name'].lower() == col_name.lower()]
            if found:
                col = found[0]
                print(f"[OK] {col['name']:40} | {col['type']:20} | {col['nullable']}")
            else:
                print(f"[MISSING] {col_name:40} | NOT FOUND")
        
        print("=" * 80)
    
    # Test sample query
    test_sample_query()

