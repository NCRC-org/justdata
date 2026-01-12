#!/usr/bin/env python3
"""
Run multiracial combination analysis query and display results.
"""

import sys
import os
from pathlib import Path

# Add project root to path to import shared utilities
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.utils.bigquery_client import get_bigquery_client, execute_query

PROJECT_ID = "hdma1-242116"

def main():
    """Run the multiracial analysis query."""
    print("=" * 80)
    print("Multi-Racial Borrower Race Combination Analysis")
    print("=" * 80)
    print()
    
    # Read the SQL query
    sql_file = Path(__file__).parent / "analyze_multiracial_combinations.sql"
    with open(sql_file, 'r') as f:
        sql = f.read()
    
    print("Executing query...")
    print()
    
    try:
        client = get_bigquery_client(PROJECT_ID)
        results = execute_query(client, sql, timeout=300)  # 5 minute timeout for large query
        
        if not results:
            print("No results returned.")
            return
        
        print(f"Found {len(results)} race combinations")
        print()
        print("=" * 80)
        print("RACE COMBINATION BREAKDOWN")
        print("=" * 80)
        print()
        
        total_loans = sum(row['loan_count'] for row in results)
        
        print(f"{'Race Combination':<50} {'Loan Count':>15} {'Percentage':>15}")
        print("-" * 80)
        
        for row in results:
            combination = row['race_combination']
            count = row['loan_count']
            pct = row['percentage']
            
            print(f"{combination:<50} {count:>15,} {pct:>14.2f}%")
        
        print("-" * 80)
        print(f"{'TOTAL':<50} {total_loans:>15,} {'100.00':>15}%")
        print()
        print("=" * 80)
        print("ALL RACE COMBINATIONS (Complete List)")
        print("=" * 80)
        print()
        
        for i, row in enumerate(results, 1):
            combination = row['race_combination']
            count = row['loan_count']
            pct = row['percentage']
            combo_code = row.get('race_combo_code', 'N/A')
            
            print(f"{i:2d}. {combination:<45} Code: {combo_code:<15} Count: {count:>10,} ({pct:>5.2f}%)")
        
        print()
        print("=" * 80)
        print("HMDA FILTERS APPLIED")
        print("=" * 80)
        print()
        print("The query analyzed ALL HMDA loan applications (not just originations) with:")
        print("  - Years: 2018-2024 (all available years)")
        print("  - Multi-racial criteria:")
        print("    * Non-Hispanic (all 5 ethnicity fields checked)")
        print("    * 2 or more DISTINCT main race categories")
        print("    * Main categories: 1=Native American, 2=Asian, 3=Black, 4=HoPI, 5=White")
        print("  - No other filters applied (includes all loan types, purposes, actions, etc.)")
        print()
        print("Note: This is ALL applications, not filtered to originations only.")
        print("      The analysis includes all loan applications regardless of action taken.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

