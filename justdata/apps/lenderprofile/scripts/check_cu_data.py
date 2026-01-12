#!/usr/bin/env python3
"""Check if credit union call report data was loaded into BigQuery."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from justdata.shared.utils.unified_env import ensure_unified_env_loaded
from justdata.shared.utils.bigquery_client import get_bigquery_client, execute_query

ensure_unified_env_loaded(verbose=True)

client = get_bigquery_client()

# Check branches table
try:
    query = """
    SELECT 
        COUNT(*) as total_branches,
        COUNT(DISTINCT year) as years_available,
        MIN(year) as min_year,
        MAX(year) as max_year,
        COUNT(DISTINCT cu_number) as total_cus
    FROM `hdma1-242116.credit_unions.cu_branches`
    """
    results = execute_query(client, query)
    print("=" * 80)
    print("CREDIT UNION BRANCHES TABLE")
    print("=" * 80)
    for row in results:
        print(f"Total branches: {row.get('total_branches'):,}")
        print(f"Years available: {row.get('years_available')}")
        print(f"Year range: {row.get('min_year')} - {row.get('max_year')}")
        print(f"Total credit unions: {row.get('total_cus'):,}")
    
    # Check by year
    query2 = """
    SELECT 
        year,
        COUNT(*) as branches,
        COUNT(DISTINCT cu_number) as cus
    FROM `hdma1-242116.credit_unions.cu_branches`
    GROUP BY year
    ORDER BY year
    """
    results2 = execute_query(client, query2)
    print("\nBranches by Year:")
    for row in results2:
        print(f"  {row.get('year')}: {row.get('branches'):,} branches, {row.get('cus'):,} credit unions")
        
except Exception as e:
    print(f"ERROR checking branches table: {e}")

# Check call reports table
try:
    query3 = """
    SELECT 
        COUNT(*) as total_records,
        COUNT(DISTINCT year) as years_available,
        MIN(year) as min_year,
        MAX(year) as max_year,
        COUNT(DISTINCT cu_number) as total_cus
    FROM `hdma1-242116.credit_unions.cu_call_reports`
    """
    results3 = execute_query(client, query3)
    print("\n" + "=" * 80)
    print("CREDIT UNION CALL REPORTS TABLE")
    print("=" * 80)
    for row in results3:
        print(f"Total records: {row.get('total_records'):,}")
        print(f"Years available: {row.get('years_available')}")
        print(f"Year range: {row.get('min_year')} - {row.get('max_year')}")
        print(f"Total credit unions: {row.get('total_cus'):,}")
except Exception as e:
    print(f"ERROR checking call reports table: {e}")

