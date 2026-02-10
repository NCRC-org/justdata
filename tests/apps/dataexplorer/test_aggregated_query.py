#!/usr/bin/env python3
"""
Test our aggregated query to see if it matches the simple count.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
from justdata.shared.utils.unified_env import ensure_unified_env_loaded, get_unified_config
from justdata.apps.lendsight.core import load_sql_template
from justdata.apps.dataexplorer.lender_analysis_core import apply_filters_to_sql_template, escape_sql_string

# Load environment
ensure_unified_env_loaded(verbose=True)
config = get_unified_config(verbose=True)

def test_aggregated_query():
    """Test our aggregated query structure."""
    
    client = get_bigquery_client()
    if not client:
        print("ERROR: BigQuery client not available")
        return
    
    lei = "WWB2V0FCW3A0EE3ZJN75"
    years = ['2022', '2023', '2024']
    years_str = "', '".join(years)
    
    # Load the SQL template
    sql_template = load_sql_template()
    
    # Apply the same modifications we do in lender_analysis_core.py
    sql = sql_template.replace("WHERE c.county_state = @county", f"WHERE h.lei = '{escape_sql_string(lei)}'")
    sql = sql.replace('@county', "'all'")
    sql = sql.replace("AND h.activity_year = @year", f"AND h.activity_year IN ('{years_str}')")
    if '@year' in sql:
        sql = sql.replace('@year', f"'{years_str}'")
    sql = sql.replace('@loan_purpose', "'all'")
    
    # Apply default filters (same as our default)
    query_filters = {
        'action_taken': ['1'],
        'occupancy': ['1'],
        'total_units': ['1', '2', '3', '4'],
        'construction': ['1'],
        'loan_type': ['1', '2', '3', '4'],
        'exclude_reverse_mortgages': True
    }
    sql = apply_filters_to_sql_template(sql, query_filters)
    
    # Remove any county_state requirements
    sql = sql.replace("AND c.county_state IS NOT NULL", "")
    sql = sql.replace("WHERE c.county_state IS NOT NULL AND", "WHERE")
    sql = sql.replace("WHERE c.county_state IS NOT NULL", "WHERE 1=1")
    
    print("=" * 80)
    print("OUR AGGREGATED QUERY (First 2000 chars)")
    print("=" * 80)
    print(sql[:2000])
    print("...")
    print("=" * 80)
    
    try:
        results = execute_query(client, sql)
        
        print(f"\nQuery returned {len(results)} aggregated rows")
        
        # Sum up total_originations by year
        year_totals = {}
        total_all = 0
        for row in results:
            year = row.get('year')
            loans = int(row.get('total_originations', 0))
            if year:
                year_totals[year] = year_totals.get(year, 0) + loans
                total_all += loans
        
        print("\nResults (sum of total_originations from all grouped rows):")
        print("-" * 80)
        for year in sorted(year_totals.keys()):
            print(f"Year {year}: {year_totals[year]:,} loans")
        print("-" * 80)
        print(f"Total across all years: {total_all:,} loans")
        
        print("\nExpected (from simple COUNT query):")
        print("  2022: 25,130")
        print("  2023: 16,835")
        print("  2024: 19,791")
        print("  Total: 61,756")
        
        if total_all == 61756:
            print("\n✓ MATCH! Our aggregated query produces the correct total.")
        else:
            print(f"\n✗ MISMATCH! Our query produces {total_all:,} but should be 61,756")
            print(f"  Difference: {61756 - total_all:,} loans")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_aggregated_query()

