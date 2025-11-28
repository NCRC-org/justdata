#!/usr/bin/env python3
"""
Test HMDA query with expanded county codes to see if data is returned.
"""

import sys
sys.path.insert(0, '.')

from apps.dataexplorer.data_utils import expand_geoids, execute_query
from apps.dataexplorer.demographic_queries import build_hmda_demographic_query

print("=" * 80)
print("HMDA QUERY TEST WITH METRO EXPANSION")
print("=" * 80)
print()

# Step 1: Expand metro code
metro_code = "12060"  # Atlanta
print(f"Step 1: Expanding metro code {metro_code}...")
expanded = expand_geoids([metro_code])
print(f"✓ Expanded to {len(expanded)} counties")
print(f"  First 5 counties: {expanded[:5]}")
print()

# Step 2: Build HMDA query
print("Step 2: Building HMDA query...")
years = [2020, 2021, 2022, 2023, 2024]
query = build_hmda_demographic_query(
    geoids=expanded,
    years=years,
    loan_purpose=["1"],
    action_taken=["1", "2", "3", "4", "5"],
    occupancy_type=["1"],
    total_units=["1", "2", "3", "4"],
    construction_method=["1"],
    exclude_reverse_mortgages=True,
    metric_type='count'
)

print(f"✓ Query built")
print(f"  Counties: {len(expanded)}")
print(f"  Years: {years}")
print()

# Step 3: Check query format
print("Step 3: Checking query format...")
# Check if geoids are properly formatted in the query
geoid5_list_in_query = "', '".join([str(g).zfill(5) for g in expanded[:5]])
print(f"  Sample geoid format in query: '{geoid5_list_in_query}'")
print(f"  Query contains {len(expanded)} counties")
print()

# Step 4: Execute query
print("Step 4: Executing query (this may take a moment)...")
try:
    raw_data = execute_query(query)
    print(f"✓ Query executed")
    print(f"  Rows returned: {len(raw_data) if raw_data else 0}")
    
    if raw_data:
        print(f"  ✓ DATA FOUND!")
        print(f"  Sample row keys: {list(raw_data[0].keys()) if raw_data else 'N/A'}")
        print(f"  First row sample:")
        if raw_data:
            first_row = raw_data[0]
            for key in list(first_row.keys())[:10]:
                print(f"    {key}: {first_row.get(key)}")
    else:
        print(f"  ⚠ NO DATA RETURNED")
        print()
        print("  This could mean:")
        print("    - No HMDA data for these counties/years")
        print("    - Filters are too restrictive")
        print("    - Query format issue")
        print()
        print("  Let's check a simpler query...")
        # Try with just one county and one year
        simple_query = build_hmda_demographic_query(
            geoids=[expanded[0]],  # Just first county
            years=[2024],  # Just latest year
            loan_purpose=None,  # No filters
            action_taken=None,
            occupancy_type=None,
            total_units=None,
            construction_method=None,
            exclude_reverse_mortgages=False,
            metric_type='count'
        )
        print(f"  Testing simple query (1 county, 1 year, no filters)...")
        simple_data = execute_query(simple_query)
        print(f"  Simple query returned: {len(simple_data) if simple_data else 0} rows")
        
except Exception as e:
    print(f"❌ Error executing query: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)


