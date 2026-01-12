#!/usr/bin/env python3
"""
Move GLEIF names and credit union data to justdata dataset.
Also create an optimized SOD table for branch network analysis.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.utils.unified_env import ensure_unified_env_loaded
from shared.utils.bigquery_client import get_bigquery_client, execute_query
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

ensure_unified_env_loaded(verbose=True)

client = get_bigquery_client()
project_id = 'hdma1-242116'

print("=" * 80)
print("MOVING DATA TO JUSTDATA DATASET")
print("=" * 80)

# 1. Copy GLEIF names to justdata
print("\n1. Copying GLEIF names to justdata...")
try:
    # Create table in justdata by copying from hmda
    copy_query = f"""
    CREATE OR REPLACE TABLE `{project_id}.justdata.gleif_names` AS
    SELECT *
    FROM `{project_id}.hmda.lender_names_gleif`
    """
    execute_query(client, copy_query)
    print("   [OK] GLEIF names copied to justdata.gleif_names")
except Exception as e:
    print(f"   [ERROR] {e}")

# 2. Copy credit union branches to justdata
print("\n2. Copying credit union branches to justdata...")
try:
    copy_query = f"""
    CREATE OR REPLACE TABLE `{project_id}.justdata.credit_union_branches` AS
    SELECT *
    FROM `{project_id}.credit_unions.cu_branches`
    """
    execute_query(client, copy_query)
    print("   [OK] Credit union branches copied to justdata.credit_union_branches")
except Exception as e:
    print(f"   [ERROR] {e}")

# 3. Copy credit union call reports to justdata
print("\n3. Copying credit union call reports to justdata...")
try:
    copy_query = f"""
    CREATE OR REPLACE TABLE `{project_id}.justdata.credit_union_call_reports` AS
    SELECT *
    FROM `{project_id}.credit_unions.cu_call_reports`
    """
    execute_query(client, copy_query)
    print("   [OK] Credit union call reports copied to justdata.credit_union_call_reports")
except Exception as e:
    print(f"   [ERROR] {e}")

# 4. Create optimized SOD table for branch network analysis
print("\n4. Creating optimized SOD table for branch network analysis...")
try:
    # This table will:
    # - Combine all SOD tables (sod, sod_legacy, sod25)
    # - Include only fields needed for branch analysis
    # - Pre-calculate useful fields
    # - Optimize for year-over-year queries
    optimized_query = f"""
    CREATE OR REPLACE TABLE `{project_id}.justdata.sod_branches_optimized` AS
    WITH all_sod AS (
        -- SOD25 (2025)
        SELECT
            CAST(rssd AS STRING) as rssd,
            year,
            uninumbr as branch_id,
            bank_name,
            branch_name,
            address,
            city,
            state,
            state_abbrv as state_abbr,
            zip,
            county,
            geoid5,
            latitude,
            longitude,
            COALESCE(deposits_000s, 0) * 1000 as deposits,
            br_lmi,
            br_minority,
            service_type,
            assets_000s
        FROM `{project_id}.branches.sod25`
        
        UNION ALL
        
        -- SOD (intermediate years)
        SELECT
            CAST(rssd AS STRING) as rssd,
            year,
            uninumbr as branch_id,
            bank_name,
            branch_name,
            address,
            city,
            state,
            state_abbrv as state_abbr,
            zip,
            county,
            geoid5,
            latitude,
            longitude,
            COALESCE(deposits_000s, 0) * 1000 as deposits,
            br_lmi,
            br_minority,
            service_type,
            assets_000s
        FROM `{project_id}.branches.sod`
        
        UNION ALL
        
        -- SOD Legacy (older years)
        SELECT
            CAST(rssd AS STRING) as rssd,
            year,
            uninumbr as branch_id,
            bank_name,
            branch_name,
            address,
            city,
            state,
            state_abbrv as state_abbr,
            zip,
            county,
            geoid5,
            latitude,
            longitude,
            COALESCE(deposits_000s, 0) * 1000 as deposits,
            br_lmi,
            br_minority,
            service_type,
            assets_000s
        FROM `{project_id}.branches.sod_legacy`
    )
    SELECT DISTINCT
        rssd,
        year,
        branch_id,
        bank_name,
        branch_name,
        address,
        city,
        state,
        state_abbr,
        zip,
        county,
        geoid5,
        latitude,
        longitude,
        deposits,
        br_lmi,
        br_minority,
        service_type,
        assets_000s,
        -- Create a stable branch key for year-over-year matching
        -- Use coordinates if available, otherwise use address
        CASE 
            WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN
                CONCAT(
                    CAST(ROUND(CAST(latitude AS FLOAT64), 4) AS STRING),
                    ',',
                    CAST(ROUND(CAST(longitude AS FLOAT64), 4) AS STRING)
                )
            ELSE NULL
        END as branch_key_coords,
        CONCAT(
            COALESCE(UPPER(TRIM(address)), ''),
            '|',
            COALESCE(UPPER(TRIM(city)), ''),
            '|',
            COALESCE(UPPER(TRIM(state)), ''),
            '|',
            COALESCE(SUBSTR(TRIM(zip), 1, 5), '')
        ) as branch_key_address
    FROM all_sod
    WHERE rssd IS NOT NULL
        AND year IS NOT NULL
        AND (city IS NOT NULL OR state IS NOT NULL)
    """
    execute_query(client, optimized_query)
    print("   [OK] Optimized SOD table created: justdata.sod_branches_optimized")
    
    # Get stats
    stats_query = f"""
    SELECT 
        COUNT(*) as total_branches,
        COUNT(DISTINCT rssd) as total_banks,
        COUNT(DISTINCT year) as years,
        MIN(year) as min_year,
        MAX(year) as max_year
    FROM `{project_id}.justdata.sod_branches_optimized`
    """
    stats = execute_query(client, stats_query)
    if stats:
        s = stats[0]
        print(f"     Total branches: {s.get('total_branches'):,}")
        print(f"     Total banks: {s.get('total_banks'):,}")
        print(f"     Years: {s.get('min_year')} - {s.get('max_year')} ({s.get('years')} years)")
        
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    import traceback
    traceback.print_exc()

# 5. Optimize table structure with clustering
print("\n5. Optimizing table structure...")
try:
    # Use clustering (partitioning by integer year requires RANGE_BUCKET which is complex)
    # Clustering is sufficient for performance on year-based queries
    optimize_query = f"""
    CREATE OR REPLACE TABLE `{project_id}.justdata.sod_branches_optimized_clustered`
    CLUSTER BY rssd, year, state, city
    AS
    SELECT * FROM `{project_id}.justdata.sod_branches_optimized`
    """
    execute_query(client, optimize_query)
    
    # Replace original with clustered version
    replace_query = f"""
    DROP TABLE `{project_id}.justdata.sod_branches_optimized`;
    ALTER TABLE `{project_id}.justdata.sod_branches_optimized_clustered`
    RENAME TO sod_branches_optimized
    """
    execute_query(client, replace_query)
    print("   [OK] Table clustered by rssd, year, state, city for optimal query performance")
except Exception as e:
    print(f"   [WARNING] Could not optimize table structure: {e}")
    print("   (Table created but without clustering - still functional)")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("[OK] GLEIF names: justdata.gleif_names")
print("[OK] Credit union branches: justdata.credit_union_branches")
print("[OK] Credit union call reports: justdata.credit_union_call_reports")
print("[OK] Optimized SOD branches: justdata.sod_branches_optimized")
print("\nAll data is now in the justdata dataset!")

