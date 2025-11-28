#!/usr/bin/env python3
"""Check what columns exist in the 1071_1k_lenders table."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient

bq_client = BigQueryClient()
table_id = f"{bq_client.project_id}.misc.1071_1k_lenders"

# Get a sample row to see columns
sql = f"SELECT * FROM `{table_id}` LIMIT 1"

try:
    result = bq_client.query(sql)
    df = result.to_dataframe()
    
    print("=" * 80)
    print("COLUMNS IN 1071_1k_lenders TABLE")
    print("=" * 80)
    print()
    print(f"Total columns: {len(df.columns)}")
    print()
    print("Column names:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")
    print()
    
    # Check for credit card related columns
    credit_card_cols = [col for col in df.columns if 'credit' in col.lower() or 'lender_type' in col.lower()]
    if credit_card_cols:
        print("Credit card related columns found:")
        for col in credit_card_cols:
            print(f"  - {col}")
    else:
        print("⚠ WARNING: No credit card related columns found!")
        print("  The table needs to be recreated with the updated SQL.")
    print()
    print("=" * 80)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

