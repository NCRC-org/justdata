#!/usr/bin/env python3
"""
Script to query BigQuery job history and find Tableau queries.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from justdata.shared.utils.bigquery_client import get_bigquery_client
from justdata.shared.utils.unified_env import ensure_unified_env_loaded, get_unified_config
from google.cloud import bigquery
from datetime import datetime, timedelta
import json

# Load environment
ensure_unified_env_loaded(verbose=True)
config = get_unified_config(verbose=True)

def find_tableau_queries(lei: str = "WWB2V0FCW3A0EE3ZJN75", lender_name: str = "Manufacturers and Traders Trust", hours_back: int = 168):
    """Find recent Tableau queries for a specific lender.
    
    Tableau queries are typically simpler - they might just do COUNT(*) or SUM() aggregations
    without all the complex demographic breakdowns.
    """
    
    client = get_bigquery_client()
    if not client:
        print("ERROR: BigQuery client not available")
        return
    
    project_id = config.get('GCP_PROJECT_ID', 'hdma1-242116')
    
    print(f"Searching for queries in the last {hours_back} hours...")
    print(f"Looking for LEI: {lei}")
    print(f"Looking for lender: {lender_name}")
    print("-" * 80)
    
    # Query job history from INFORMATION_SCHEMA
    # Look for queries that might be from Tableau (different user or query pattern)
    query = f"""
        SELECT
            job_id,
            creation_time,
            start_time,
            end_time,
            state,
            total_bytes_processed,
            user_email,
            query,
            statement_type,
            error_result
        FROM `{project_id}`.`region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
        WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours_back} HOUR)
            AND job_type = 'QUERY'
            AND state = 'DONE'
            AND (
                UPPER(query) LIKE UPPER('%{lei}%')
                OR UPPER(query) LIKE UPPER('%{lender_name.replace(" ", "%")}%')
            )
        ORDER BY creation_time DESC
        LIMIT 100
        """
    
    try:
        print("Executing query...")
        query_job = client.query(query)
        results = query_job.result()
        
        matching_jobs = []
        for row in results:
            query_text = row.query or ""
            
            # Check if it matches our filter criteria
            has_lei = lei.upper() in query_text.upper()
            has_lender_name = lender_name.upper().replace(" ", "") in query_text.upper().replace(" ", "")
            has_originations = "action_taken = '1'" in query_text or "action_taken='1'" in query_text
            has_owner_occupied = "occupancy_type = '1'" in query_text or "occupancy_type='1'" in query_text
            has_site_built = "construction_method = '1'" in query_text or "construction_method='1'" in query_text
            has_1_4_units = "total_units IN ('1','2','3','4')" in query_text or "'1','2','3','4'" in query_text
            
            # Check if it's a simpler aggregation query (like Tableau might use)
            is_simple_aggregation = (
                "COUNT(*)" in query_text.upper() or 
                "COUNT(1)" in query_text.upper() or
                ("SUM(" in query_text.upper() and "COUNT(" not in query_text.upper())
            )
            
            if has_lei or has_lender_name:
                matching_jobs.append({
                    'job_id': row.job_id,
                    'creation_time': row.creation_time.isoformat() if row.creation_time else None,
                    'start_time': row.start_time.isoformat() if row.start_time else None,
                    'end_time': row.end_time.isoformat() if row.end_time else None,
                    'state': row.state,
                    'total_bytes_processed': row.total_bytes_processed,
                    'user_email': row.user_email,
                    'query': query_text,
                    'statement_type': row.statement_type,
                    'error': str(row.error_result) if row.error_result else None,
                    'matches': {
                        'has_lei': has_lei,
                        'has_lender_name': has_lender_name,
                        'has_originations': has_originations,
                        'has_owner_occupied': has_owner_occupied,
                        'has_site_built': has_site_built,
                        'has_1_4_units': has_1_4_units,
                        'is_simple_aggregation': is_simple_aggregation
                    }
                })
        
        print(f"\nFound {len(matching_jobs)} matching queries\n")
        
        # Sort by creation time (most recent first) and prioritize simple aggregations (likely Tableau)
        matching_jobs.sort(key=lambda x: (
            not x['matches'].get('is_simple_aggregation', False),  # Simple aggregations first
            x['creation_time'] or ''  # Then by time
        ), reverse=True)
        
        # Show the most recent/most relevant ones first
        for i, job in enumerate(matching_jobs[:10], 1):  # Show top 10
            print(f"\n{'='*80}")
            print(f"QUERY #{i}")
            print(f"{'='*80}")
            print(f"Job ID: {job['job_id']}")
            print(f"Creation Time: {job['creation_time']}")
            print(f"User: {job['user_email']}")
            bytes_processed = job['total_bytes_processed'] or 0
            print(f"Bytes Processed: {bytes_processed:,}")
            print(f"\nMatch Criteria:")
            for key, value in job['matches'].items():
                print(f"  {key}: {value}")
            print(f"\n{'='*80}")
            print("FULL SQL QUERY:")
            print(f"{'='*80}")
            print(job['query'])
            print(f"{'='*80}\n")
        
        # Save the most recent query to a file
        if matching_jobs:
            most_recent = matching_jobs[0]
            output_file = Path(__file__).parent / "tableau_query_reference.sql"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"-- Tableau Query for {lender_name}\n")
                f.write(f"-- Job ID: {most_recent['job_id']}\n")
                f.write(f"-- Creation Time: {most_recent['creation_time']}\n")
                f.write(f"-- User: {most_recent['user_email']}\n")
                f.write(f"\n{most_recent['query']}\n")
            print(f"\nSaved most recent query to: {output_file}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    find_tableau_queries()

