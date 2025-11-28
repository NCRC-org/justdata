#!/usr/bin/env python3
"""
Run the SQL to create/update the 1071_1k_lenders table in BigQuery.
If table creation fails due to permissions, will query existing table instead.
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient


def read_sql_file():
    """Read the SQL from 1071_table_sql.txt"""
    sql_file = os.path.join(os.path.dirname(__file__), '1071_table_sql.txt')
    with open(sql_file, 'r') as f:
        return f.read()


def verify_table(bq_client, table_id):
    """Verify the table structure and show sample data."""
    print("=" * 80)
    print("VERIFYING TABLE STRUCTURE")
    print("=" * 80)
    print(f"Table: {table_id}")
    print()
    
    # Get column information
    try:
        sample_sql = f"SELECT * FROM `{table_id}` LIMIT 5"
        query_job = bq_client.query(sample_sql)
        result = query_job.result()
        df = result.to_dataframe()
        
        print(f"✓ Table exists with {len(df.columns)} columns")
        print()
        print("Columns:")
        for i, col in enumerate(df.columns, 1):
            marker = ""
            if 'credit' in col.lower() or 'lender_type' in col.lower():
                marker = " ← Credit card column"
            print(f"  {i:2d}. {col}{marker}")
        
        print()
        # Check for required columns
        required_cols = ['is_credit_card_lender', 'lender_type', 'qualification_status']
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            print(f"⚠ Missing columns: {', '.join(missing)}")
            print("  Table needs to be recreated with updated SQL.")
        else:
            print("✓ All required columns present!")
        
        print()
        print("Sample row count:")
        count_sql = f"SELECT COUNT(*) as cnt FROM `{table_id}`"
        count_result = bq_client.query(count_sql).result()
        row_count = list(count_result)[0].cnt
        print(f"  Total rows: {row_count:,}")
        
        if row_count > 0:
            print()
            print("Sample data (first 3 rows):")
            print("-" * 80)
            for idx, row in df.head(3).iterrows():
                print(f"\nRow {idx + 1}:")
                print(f"  respondent_id: {row.get('respondent_id', 'N/A')}")
                print(f"  year: {row.get('year', 'N/A')}")
                print(f"  lender_name: {row.get('lender_name', 'N/A')}")
                print(f"  is_credit_card_lender: {row.get('is_credit_card_lender', 'N/A')}")
                print(f"  lender_type: {row.get('lender_type', 'N/A')}")
                print(f"  qualification_status: {row.get('qualification_status', 'N/A')}")
        
    except Exception as e:
        print(f"Error querying table: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("=" * 80)
    print("1071_1K_LENDERS TABLE UPDATE")
    print("=" * 80)
    print()
    
    bq_client = BigQueryClient()
    table_id = f"{bq_client.project_id}.misc.1071_1k_lenders"
    
    # Read SQL
    print("Reading SQL from 1071_table_sql.txt...")
    sql = read_sql_file()
    print("✓ SQL loaded")
    print()
    
    # Try to create/update table
    print("Attempting to create/update table...")
    print(f"Table: {table_id}")
    print("⏳ This may take several minutes...")
    print()
    
    try:
        start_time = time.time()
        query_job = bq_client.query(sql)
        
        # Wait for completion with progress updates
        print("⏳ Waiting for query to complete...")
        while not query_job.done():
            time.sleep(5)
            print("  Still running...")
        
        query_job.result()  # This will raise an exception if the job failed
        
        elapsed = time.time() - start_time
        print(f"✓ Table created/updated successfully in {elapsed:.1f}s")
        print()
        
        # Verify the table
        verify_table(bq_client, table_id)
        
    except Exception as e:
        error_msg = str(e)
        print(f"✗ Error creating table: {error_msg}")
        print()
        
        if "Permission" in error_msg or "Access Denied" in error_msg:
            print("⚠ Permission denied - cannot create table via Python client.")
            print("  Please run the SQL directly in BigQuery console:")
            print(f"  File: 1071_table_sql.txt")
            print()
            print("  After running the SQL in BigQuery, this script can verify the table.")
            print()
            # Try to verify existing table anyway
            try:
                verify_table(bq_client, table_id)
            except:
                print("  Table does not exist or cannot be accessed.")
        else:
            import traceback
            traceback.print_exc()
    
    print()
    print("=" * 80)


if __name__ == '__main__':
    main()

