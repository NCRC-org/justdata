#!/usr/bin/env python3
"""Check the actual structure of the 1071_1k_lenders table."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'apps'))

from bizsight.utils.bigquery_client import BigQueryClient

bq_client = BigQueryClient()
table_id = f"{bq_client.project_id}.misc.1071_1k_lenders"

# Query to get table schema
sql = f"""
SELECT 
  column_name,
  data_type,
  ordinal_position
FROM `{bq_client.project_id}.misc.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = '1071_1k_lenders'
ORDER BY ordinal_position
"""

print("=" * 80)
print("CHECKING TABLE STRUCTURE")
print("=" * 80)
print(f"Table: {table_id}")
print()

try:
    result = bq_client.query(sql)
    rows = list(result)
    
    if rows:
        print(f"Found {len(rows)} columns:")
        print()
        print(f"{'Position':<10} {'Column Name':<40} {'Data Type':<20}")
        print("-" * 80)
        for row in rows:
            print(f"{row.ordinal_position:<10} {row.column_name:<40} {row.data_type:<20}")
        
        # Check for credit card columns
        print()
        credit_card_cols = [r.column_name for r in rows if 'credit' in r.column_name.lower() or 'lender_type' in r.column_name.lower()]
        if credit_card_cols:
            print("✓ Credit card related columns found:")
            for col in credit_card_cols:
                print(f"  - {col}")
        else:
            print("⚠ WARNING: No credit card related columns found!")
            print("  Columns that might be related:")
            related = [r.column_name for r in rows if 'type' in r.column_name.lower() or 'qualif' in r.column_name.lower()]
            if related:
                for col in related:
                    print(f"  - {col}")
            else:
                print("  None found. Table needs to be recreated with updated SQL.")
    else:
        print("⚠ No columns found. Table might not exist or query failed.")
        
except Exception as e:
    print(f"Error querying table: {e}")
    import traceback
    traceback.print_exc()
    
    # Try alternative: just get a sample row
    print()
    print("Trying alternative: getting a sample row...")
    try:
        sample_sql = f"SELECT * FROM `{table_id}` LIMIT 1"
        result = bq_client.query(sample_sql)
        df = result.to_dataframe()
        if not df.empty:
            print(f"\nColumns from sample row ({len(df.columns)} total):")
            for i, col in enumerate(df.columns, 1):
                print(f"  {i:2d}. {col}")
        else:
            print("Table is empty or doesn't exist.")
    except Exception as e2:
        print(f"Alternative also failed: {e2}")

print()
print("=" * 80)

