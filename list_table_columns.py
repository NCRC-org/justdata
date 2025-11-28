#!/usr/bin/env python3
"""List columns in the 1071_1k_lenders table."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient

bq_client = BigQueryClient()
table_id = f"{bq_client.project_id}.misc.1071_1k_lenders"

print("Querying table for column names...")
print(f"Table: {table_id}")
print()

try:
    # Simple query to get one row and see columns
    sql = f"SELECT * FROM `{table_id}` LIMIT 1"
    query_job = bq_client.query(sql)
    result = query_job.result()
    
    # Get the first row to see what columns exist
    rows = list(result)
    if rows:
        row = rows[0]
        columns = list(row.keys())
        
        print("=" * 80)
        print(f"COLUMNS IN TABLE ({len(columns)} total)")
        print("=" * 80)
        print()
        for i, col in enumerate(columns, 1):
            marker = ""
            if 'credit' in col.lower() or 'lender_type' in col.lower():
                marker = " ← Credit card column"
            print(f"{i:2d}. {col}{marker}")
        
        print()
        credit_cols = [c for c in columns if 'credit' in c.lower() or 'lender_type' in c.lower()]
        if credit_cols:
            print(f"✓ Found {len(credit_cols)} credit card related column(s)")
        else:
            print("⚠ No credit card columns found!")
            print("  The table was created with an older version of the SQL.")
            print("  You need to run the updated SQL from 1071_table_sql.txt")
    else:
        print("Table is empty or query returned no results.")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

