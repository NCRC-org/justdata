#!/usr/bin/env python3
"""
Check all income_group_total values in the disclosure table.
"""

import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from apps.bizsight.utils.bigquery_client import BigQueryClient

def check_income_groups():
    """Query BigQuery to get all unique income_group_total values."""
    bq_client = BigQueryClient()
    
    # Query to get all unique income_group_total values and their counts
    query = f"""
    SELECT 
        income_group_total,
        COUNT(*) as count,
        SUM(num_under_100k + num_100k_250k + num_250k_1m) as total_loans
    FROM `{bq_client.project_id}.sb.disclosure`
    WHERE year = 2024
      AND income_group_total IS NOT NULL
      AND income_group_total != ''
    GROUP BY income_group_total
    ORDER BY income_group_total
    """
    
    print("=" * 80)
    print("INCOME_GROUP_TOTAL VALUES IN DISCLOSURE TABLE (2024)")
    print("=" * 80)
    print("\nQuerying BigQuery...")
    
    try:
        result = bq_client.client.query(query).to_dataframe()
        
        print(f"\nFound {len(result)} unique income_group_total values:\n")
        print(f"{'Code':<10} {'Count':<15} {'Total Loans':<15}")
        print("-" * 40)
        
        for _, row in result.iterrows():
            code = str(row['income_group_total'])
            count = int(row['count'])
            total_loans = int(row['total_loans'])
            print(f"{code:<10} {count:<15,} {total_loans:<15,}")
        
        print("\n" + "=" * 80)
        print("All income_group_total codes found:")
        codes = sorted([str(c) for c in result['income_group_total'].unique()])
        print(", ".join(codes))
        print("=" * 80)
        
    except Exception as e:
        print(f"Error querying BigQuery: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_income_groups()

