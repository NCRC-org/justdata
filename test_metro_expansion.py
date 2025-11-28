#!/usr/bin/env python3
"""
Test metro code expansion to verify it's working correctly.
"""

import sys
sys.path.insert(0, '.')

from apps.dataexplorer.data_utils import expand_geoids, get_available_metros

print("=" * 80)
print("METRO CODE EXPANSION TEST")
print("=" * 80)
print()

# Step 1: Get a metro area
print("Step 1: Getting metro areas...")
metros = get_available_metros()
if not metros:
    print("❌ No metros found")
    sys.exit(1)

# Select Atlanta metro (code 12060)
atlanta_metro = None
for metro in metros:
    if '12060' in str(metro.get('code', '')):
        atlanta_metro = metro
        break

if not atlanta_metro:
    atlanta_metro = metros[0]  # Use first metro if Atlanta not found

metro_code = str(atlanta_metro.get('code', ''))
metro_name = atlanta_metro.get('name', 'Unknown')

print(f"Selected Metro: {metro_name}")
print(f"Metro Code: {metro_code}")
print(f"Code Type: {type(metro_code)}, Length: {len(metro_code)}")
print()

# Step 2: Expand metro code to counties
print("Step 2: Expanding metro code to county codes...")
try:
    expanded = expand_geoids([metro_code])
    print(f"✓ Expansion successful!")
    print(f"  Metro Code: {metro_code}")
    print(f"  Expanded to {len(expanded)} counties")
    if expanded:
        print(f"  First 10 counties: {expanded[:10]}")
        print(f"  Sample county format: {expanded[0]} (type: {type(expanded[0])}, length: {len(expanded[0])})")
    else:
        print("  ⚠ WARNING: No counties found! This is the problem.")
        print()
        print("  Checking if metro code exists in database...")
        # Let's check what the actual metro code format is in the database
        from apps.dataexplorer.data_utils import get_bigquery_client
        from apps.dataexplorer.config import DataExplorerConfig
        
        client = get_bigquery_client()
        project_id = DataExplorerConfig.GCP_PROJECT_ID
        
        check_query = f"""
        SELECT DISTINCT 
            CAST(cbsa_code AS STRING) as cbsa_code_str,
            cbsa_code as cbsa_code_raw,
            COUNT(DISTINCT geoid5) as county_count
        FROM `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}`
        WHERE CAST(cbsa_code AS STRING) = '{metro_code}'
           OR cbsa_code = {metro_code}
        GROUP BY cbsa_code_str, cbsa_code_raw
        LIMIT 5
        """
        
        query_job = client.query(check_query)
        results = list(query_job.result())
        
        if results:
            print(f"  ✓ Found metro in database:")
            for row in results:
                print(f"    - cbsa_code_str: {row.cbsa_code_str} (type: {type(row.cbsa_code_str)})")
                print(f"    - cbsa_code_raw: {row.cbsa_code_raw} (type: {type(row.cbsa_code_raw)})")
                print(f"    - county_count: {row.county_count}")
        else:
            print(f"  ❌ Metro code {metro_code} NOT found in database!")
            print()
            print("  Checking similar codes...")
            similar_query = f"""
            SELECT DISTINCT 
                CAST(cbsa_code AS STRING) as cbsa_code_str,
                COUNT(DISTINCT geoid5) as county_count
            FROM `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CBSA_TABLE}`
            WHERE CAST(cbsa_code AS STRING) LIKE '%{metro_code[-3:]}%'
            GROUP BY cbsa_code_str
            LIMIT 10
            """
            query_job = client.query(similar_query)
            results = list(query_job.result())
            if results:
                print(f"  Found similar codes:")
                for row in results:
                    print(f"    - {row.cbsa_code_str}: {row.county_count} counties")
    
except Exception as e:
    print(f"❌ Error during expansion: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 80)


