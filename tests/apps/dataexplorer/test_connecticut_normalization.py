#!/usr/bin/env python3
"""
Test Connecticut county code normalization in SQL template.
Verifies that 2024 planning region codes are mapped to legacy county codes.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query
from justdata.shared.utils.unified_env import get_unified_config
from justdata.apps.lendsight.core import load_sql_template

config = get_unified_config(load_env=False, verbose=False)
PROJECT_ID = config.get('GCP_PROJECT_ID')
client = get_bigquery_client(PROJECT_ID)

print("=" * 80)
print("TESTING CONNECTICUT COUNTY CODE NORMALIZATION")
print("=" * 80)
print()

# Load SQL template
sql_template = load_sql_template()

# Replace parameters for a simple test query
sql = sql_template.replace("WHERE c.county_state = @county", "WHERE h.activity_year = '2024'")
sql = sql.replace('@county', "'all'")
sql = sql.replace("AND h.activity_year = @year", "AND h.activity_year = '2024'")
sql = sql.replace('@year', "'2024'")
sql = sql.replace('@loan_purpose', "'all'")

# Apply default filters
sql = sql.replace(
    "AND h.action_taken = '1'",
    "AND CAST(h.action_taken AS FLOAT64) = 1"
)
sql = sql.replace(
    "AND h.occupancy_type = '1'",
    "AND h.occupancy_type = '1'"
)
sql = sql.replace(
    "AND h.total_units IN ('1','2','3','4')",
    "AND h.total_units IN ('1','2','3','4')"
)
sql = sql.replace(
    "AND h.construction_method = '1'",
    "AND h.construction_method = '1'"
)

# Limit to Connecticut only
sql = sql.replace(
    "WHERE h.activity_year = '2024'",
    "WHERE h.activity_year = '2024' AND CAST(h.county_code AS STRING) LIKE '09%'"
)

# Add aggregation to see normalized geoid5 values
sql = sql.replace(
    "ORDER BY lender_name, county_state, year, tract_code, h.loan_purpose",
    """
    GROUP BY 
        h.lei,
        year,
        h.county_code,
        c.county_state,
        geoid5
    ORDER BY geoid5, year
    LIMIT 100
    """
)

# Modify SELECT to include both original and normalized codes
sql = sql.replace(
    "SELECT\n    h.lei,\n    h.activity_year as year,\n    h.county_code,",
    """SELECT
    h.lei,
    h.activity_year as year,
    h.county_code as original_county_code,
    COUNT(*) as loan_count,"""
)

print("Testing normalization query...")
print("-" * 80)
print("Query (first 500 chars):")
print(sql[:500])
print("...")
print()

try:
    results = execute_query(client, sql)
    
    if results:
        print(f"Found {len(results)} results")
        print()
        print("Sample results (showing normalization):")
        print("-" * 80)
        
        # Group by original and normalized codes
        normalization_map = {}
        for row in results:
            original = str(row.get('original_county_code', 'Unknown')).zfill(5)
            normalized = str(row.get('geoid5', 'Unknown')).zfill(5)
            county_state = row.get('county_state', 'N/A')
            count = int(row.get('loan_count', 0))
            
            if original not in normalization_map:
                normalization_map[original] = {
                    'normalized': normalized,
                    'county_state': county_state,
                    'total_loans': 0
                }
            normalization_map[original]['total_loans'] += count
        
        print("Original Code → Normalized Code | County State | Total Loans")
        print("-" * 80)
        for original in sorted(normalization_map.keys()):
            info = normalization_map[original]
            if original != info['normalized']:
                print(f"  {original} → {info['normalized']} | {info['county_state']} | {info['total_loans']:,} loans")
            else:
                print(f"  {original} → {info['normalized']} (unchanged) | {info['county_state']} | {info['total_loans']:,} loans")
        
        print()
        print("Verification:")
        print("-" * 80)
        
        # Check if planning regions are normalized
        planning_regions_normalized = 0
        planning_regions_found = 0
        
        for original in normalization_map.keys():
            if original.startswith('091'):  # Planning region code
                planning_regions_found += 1
                if normalization_map[original]['normalized'].startswith('090'):  # Legacy county code
                    planning_regions_normalized += 1
        
        if planning_regions_found > 0:
            print(f"Planning regions found: {planning_regions_found}")
            print(f"Planning regions normalized: {planning_regions_normalized}")
            if planning_regions_normalized == planning_regions_found:
                print("✓ All planning regions successfully normalized to legacy county codes!")
            else:
                print("✗ Some planning regions were not normalized correctly")
        else:
            print("No planning region codes found in results")
    else:
        print("No results returned")
        
except Exception as e:
    print(f"Error executing query: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)

