#!/usr/bin/env python3
"""
Test script to verify branch query works correctly.
This helps debug column name issues before they hit the API.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(REPO_ROOT))

from apps.dataexplorer.config import DataExplorerConfig
from apps.dataexplorer.data_utils import get_bigquery_client, execute_query

def test_branch_query():
    """Test the branch query with a simple example."""
    print("=" * 80)
    print("Testing Branch Query")
    print("=" * 80)
    
    project_id = DataExplorerConfig.GCP_PROJECT_ID
    geoid5_list = "34041"  # One county for testing
    legacy_years = [2021, 2022, 2023, 2024]
    sod25_years = [2025]
    
    # Test query - just check if columns exist
    test_query = f"""
    SELECT 
        year, geoid5, rssd, bank_name, branch_name, deposits_000s, 
        br_lmi, br_minority, geoid
    FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.sod_legacy`
    WHERE LPAD(CAST(geoid5 AS STRING), 5, '0') = '{geoid5_list}'
        AND CAST(year AS STRING) = '2021'
    LIMIT 1
    """
    
    print("\n1. Testing sod_legacy table columns...")
    print(f"   Query: SELECT year, geoid5, rssd, bank_name, branch_name, deposits_000s, br_lmi, br_minority, geoid")
    try:
        result = execute_query(test_query)
        if result:
            print(f"   ✓ Query successful! Got {len(result)} row(s)")
            print(f"   Columns in result: {list(result[0].keys())}")
        else:
            print("   ⚠ Query successful but returned no rows")
    except Exception as e:
        print(f"   ✗ Query failed: {e}")
        return False
    
    # Test sod25 table
    test_query2 = f"""
    SELECT 
        year, geoid5, rssd, bank_name, branch_name, deposits_000s, 
        br_lmi, cr_minority, COALESCE(geoid, census_tract) as census_tract
    FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.{DataExplorerConfig.BRANCHES_TABLE}`
    WHERE LPAD(CAST(geoid5 AS STRING), 5, '0') = '{geoid5_list}'
        AND CAST(year AS STRING) = '2025'
    LIMIT 1
    """
    
    print("\n2. Testing sod25 table columns...")
    print(f"   Query: SELECT year, geoid5, rssd, bank_name, branch_name, deposits_000s, br_lmi, cr_minority, COALESCE(geoid, census_tract)")
    try:
        result = execute_query(test_query2)
        if result:
            print(f"   ✓ Query successful! Got {len(result)} row(s)")
            print(f"   Columns in result: {list(result[0].keys())}")
        else:
            print("   ⚠ Query successful but returned no rows")
    except Exception as e:
        print(f"   ✗ Query failed: {e}")
        return False
    
    # Test full query
    print("\n3. Testing full branch analysis query...")
    full_query = f"""
    WITH branch_data AS (
        SELECT 
            year, geoid5, rssd, bank_name, branch_name, deposits_000s, 
            br_lmi, br_minority as cr_minority, geoid as census_tract
        FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.sod_legacy`
        WHERE LPAD(CAST(geoid5 AS STRING), 5, '0') = '{geoid5_list}'
            AND CAST(year AS STRING) = '2021'
        UNION ALL
        SELECT 
            year, geoid5, rssd, bank_name, branch_name, deposits_000s, 
            br_lmi, br_minority as cr_minority, geoid as census_tract
        FROM `{project_id}.{DataExplorerConfig.BRANCHES_DATASET}.{DataExplorerConfig.BRANCHES_TABLE}`
        WHERE LPAD(CAST(geoid5 AS STRING), 5, '0') = '{geoid5_list}'
            AND CAST(year AS STRING) = '2025'
    )
    SELECT 
        CAST(b.year AS STRING) as year,
        CAST(b.geoid5 AS STRING) as geoid5,
        CAST(b.rssd AS STRING) as rssd,
        b.bank_name,
        b.branch_name,
        CAST(b.deposits_000s AS FLOAT64) * 1000 as deposits,
        COALESCE(CAST(b.br_lmi AS INT64), 
            CASE WHEN c.income_level IN (1, 2) THEN 1 ELSE 0 END, 0) as is_lmi_tract,
        CASE WHEN c.income_level = 1 THEN 1 ELSE 0 END as is_low_income_tract,
        CASE WHEN c.income_level = 2 THEN 1 ELSE 0 END as is_moderate_income_tract,
        CASE WHEN c.income_level = 3 THEN 1 ELSE 0 END as is_middle_income_tract,
        CASE WHEN c.income_level = 4 THEN 1 ELSE 0 END as is_upper_income_tract,
        COALESCE(CAST(b.cr_minority AS INT64),
            CASE WHEN SAFE_DIVIDE(
                COALESCE(c.total_persons, 0) - COALESCE(c.total_white, 0),
                NULLIF(COALESCE(c.total_persons, 0), 0)
            ) * 100 > 50 THEN 1 ELSE 0 END, 0) as is_mmct_tract,
        SAFE_DIVIDE(
            COALESCE(c.total_persons, 0) - COALESCE(c.total_white, 0),
            NULLIF(COALESCE(c.total_persons, 0), 0)
        ) * 100 as tract_minority_population_percent
    FROM branch_data b
    LEFT JOIN `{project_id}.{DataExplorerConfig.GEO_DATASET}.{DataExplorerConfig.GEO_CENSUS_TABLE}` c
        ON LPAD(CAST(b.geoid5 AS STRING), 5, '0') = SUBSTR(LPAD(CAST(c.geoid AS STRING), 11, '0'), 1, 5)
        AND LPAD(CAST(b.census_tract AS STRING), 6, '0') = SUBSTR(LPAD(CAST(c.geoid AS STRING), 11, '0'), 6, 6)
    ORDER BY b.year, b.rssd, b.bank_name
    LIMIT 10
    """
    
    try:
        result = execute_query(full_query)
        if result:
            print(f"   ✓ Full query successful! Got {len(result)} row(s)")
            print(f"   Sample row columns: {list(result[0].keys())}")
            print(f"   Sample data: year={result[0].get('year')}, bank={result[0].get('bank_name')[:30]}...")
        else:
            print("   ⚠ Full query successful but returned no rows")
    except Exception as e:
        print(f"   ✗ Full query failed: {e}")
        import traceback
        print("\nFull traceback:")
        print(traceback.format_exc())
        return False
    
    print("\n" + "=" * 80)
    print("All tests passed!")
    print("=" * 80)
    return True

if __name__ == '__main__':
    success = test_branch_query()
    sys.exit(0 if success else 1)

