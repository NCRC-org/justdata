#!/usr/bin/env python3
"""
Delete a cached analysis result from BigQuery by job_id.
This will remove the result from all cache tables.
"""

import os
import sys
from pathlib import Path

# Load environment variables from .env file if it exists
env_file = Path(__file__).parent.parent / '.env'
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

from google.cloud import bigquery
from justdata.shared.utils.bigquery_client import get_bigquery_client

PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'hdma1-242116')
DATASET_ID = 'justdata'
RESULTS_TABLE = f'{PROJECT_ID}.{DATASET_ID}.analysis_results'
SECTIONS_TABLE = f'{PROJECT_ID}.{DATASET_ID}.analysis_result_sections'
CACHE_TABLE = f'{PROJECT_ID}.{DATASET_ID}.analysis_cache'

def delete_cached_result(job_id: str):
    """Delete a cached result from all BigQuery tables"""
    client = get_bigquery_client(PROJECT_ID)
    
    print(f"Deleting cached result for job_id: {job_id}\n")
    
    # Delete from sections table
    print("1. Deleting from analysis_result_sections...")
    delete_sections = f"""
    DELETE FROM `{SECTIONS_TABLE}`
    WHERE job_id = @job_id
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("job_id", "STRING", job_id)
        ]
    )
    
    try:
        query_job = client.query(delete_sections, job_config=job_config)
        query_job.result()
        print(f"   ✅ Deleted sections for job_id: {job_id}")
    except Exception as e:
        print(f"   ❌ Error deleting sections: {e}")
        return False
    
    # Delete from results table
    print("2. Deleting from analysis_results...")
    delete_results = f"""
    DELETE FROM `{RESULTS_TABLE}`
    WHERE job_id = @job_id
    """
    
    try:
        query_job = client.query(delete_results, job_config=job_config)
        query_job.result()
        print(f"   ✅ Deleted result for job_id: {job_id}")
    except Exception as e:
        print(f"   ❌ Error deleting result: {e}")
        return False
    
    # Delete from cache table
    print("3. Deleting from analysis_cache...")
    delete_cache = f"""
    DELETE FROM `{CACHE_TABLE}`
    WHERE job_id = @job_id
    """
    
    try:
        query_job = client.query(delete_cache, job_config=job_config)
        query_job.result()
        print(f"   ✅ Deleted cache entry for job_id: {job_id}")
    except Exception as e:
        print(f"   ❌ Error deleting cache entry: {e}")
        return False
    
    print(f"\n✅ Successfully deleted all records for job_id: {job_id}")
    print("   You can now run a new analysis and it will create a fresh result.")
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python delete_cached_result.py <job_id>")
        print("\nExample:")
        print("  python delete_cached_result.py 197ec561-f4fb-4998-8fb0-8a93fa9f1a65")
        sys.exit(1)
    
    job_id = sys.argv[1]
    success = delete_cached_result(job_id)
    sys.exit(0 if success else 1)

