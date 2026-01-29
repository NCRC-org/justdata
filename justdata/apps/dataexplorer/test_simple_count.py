#!/usr/bin/env python3
"""
Simple test query to count loans directly (like Tableau might do).
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
from justdata.shared.utils.unified_env import ensure_unified_env_loaded, get_unified_config

# Load environment
ensure_unified_env_loaded(verbose=True)
config = get_unified_config(verbose=True)

def test_simple_count():
    """Run a simple COUNT(*) query like Tableau might use."""
    
    client = get_bigquery_client()
    if not client:
        print("ERROR: BigQuery client not available")
        return
    
    lei = "WWB2V0FCW3A0EE3ZJN75"
    
    # Simple query - just count loans by year (like Tableau might do)
    query = f"""
    SELECT
        h.activity_year as year,
        COUNT(*) as total_loans
    FROM `justdata-ncrc.shared.de_hmda` h
    WHERE h.lei = '{lei}'
        AND h.activity_year IN ('2022', '2023', '2024')
        AND h.action_taken = '1'  -- Originations
        AND h.occupancy_type = '1'  -- Owner-occupied
        AND h.total_units IN ('1', '2', '3', '4')  -- 1-4 units
        AND h.construction_method = '1'  -- Site-built
        AND h.loan_type IN ('1', '2', '3', '4')  -- Conventional, FHA, VA, USDA
        AND (h.reverse_mortgage IS NULL OR h.reverse_mortgage != '1')  -- Not reverse mortgages
    GROUP BY h.activity_year
    ORDER BY h.activity_year
    """
    
    print("=" * 80)
    print("SIMPLE COUNT QUERY (Like Tableau)")
    print("=" * 80)
    print(query)
    print("=" * 80)
    
    try:
        results = execute_query(client, query)
        
        print(f"\nResults:")
        print("-" * 80)
        total_all_years = 0
        for row in results:
            year = row.get('year')
            count = int(row.get('total_loans', 0))
            total_all_years += count
            print(f"Year {year}: {count:,} loans")
        
        print("-" * 80)
        print(f"Total across all years: {total_all_years:,} loans")
        print("\nExpected (from Tableau):")
        print("  2022: 25,130")
        print("  2023: 16,835")
        print("  2024: 19,791")
        print("  Total: 61,756")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_simple_count()

