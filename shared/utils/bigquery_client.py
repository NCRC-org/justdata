#!/usr/bin/env python3
"""
BigQuery utilities for data analysis.
Shared across BranchSeeker, BizSight, and LendSight.
"""

import os
from google.cloud import bigquery
from google.oauth2 import service_account
from typing import List, Dict, Any


# Cache for credential path to avoid repeated lookups and messages
_credential_path_cache = None

def get_bigquery_client(project_id: str = None):
    """Get BigQuery client using environment-based credentials."""
    from pathlib import Path
    global _credential_path_cache
    
    try:
        # First, check environment variable
        env_cred_path = None
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            env_cred_path = Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
            if env_cred_path.exists():
                # Cache the working path
                _credential_path_cache = env_cred_path
                credentials = service_account.Credentials.from_service_account_file(str(env_cred_path))
                client = bigquery.Client(credentials=credentials, project=project_id)
                return client
        
        # If we have a cached path, use it (avoids repeated lookups and messages)
        if _credential_path_cache and _credential_path_cache.exists():
            credentials = service_account.Credentials.from_service_account_file(str(_credential_path_cache))
            client = bigquery.Client(credentials=credentials, project=project_id)
            return client
        
        # Try to find credentials file in common locations
        # Check both the main file and any timestamped backups
        possible_paths = [
            Path("C:/DREAM/config/credentials/hdma1-242116-74024e2eb88f.json"),
            Path("C:/DREAM/config/credentials/hdma1-242116-74024e2eb88f_20251102_180816.json"),  # Backup file
            Path("C:/DREAM/hdma1-242116-74024e2eb88f.json"),
            Path("config/credentials/hdma1-242116-74024e2eb88f.json"),
            Path("hdma1-242116-74024e2eb88f.json"),
            Path(__file__).parent.parent.parent / "config" / "credentials" / "hdma1-242116-74024e2eb88f.json",
            Path(__file__).parent.parent.parent.parent / "config" / "credentials" / "hdma1-242116-74024e2eb88f.json",
        ]
        
        # Also search the credentials directory for any matching JSON files
        cred_dir = Path("C:/DREAM/config/credentials")
        if cred_dir.exists():
            for json_file in cred_dir.glob("hdma1-*.json"):
                if json_file not in possible_paths:
                    possible_paths.append(json_file)
        
        cred_path = None
        for path in possible_paths:
            if path.exists():
                cred_path = path
                break
        
        if cred_path:
            # Cache the found path
            was_first_time = _credential_path_cache is None
            _credential_path_cache = cred_path
            # Only show message on first discovery (not on subsequent cached uses)
            if was_first_time:
                if env_cred_path and not env_cred_path.exists():
                    # Silent - env var issue already handled, just use the found file
                    pass
                # Don't print anything - credentials found and cached, will be used silently next time
            credentials = service_account.Credentials.from_service_account_file(str(cred_path))
            client = bigquery.Client(credentials=credentials, project=project_id)
            return client
        
        # If we get here, no credentials found - show warning about env var if it was set
        if env_cred_path and not env_cred_path.exists():
            print(f"[WARNING] GOOGLE_APPLICATION_CREDENTIALS points to non-existent file: {env_cred_path}")
            print(f"[WARNING] No credentials file found in common locations either")
        
        # Fallback: try default service account (for cloud deployments)
        print("[INFO] No credentials file found, trying default service account...")
        client = bigquery.Client(project=project_id)
        return client
        
    except Exception as e:
        print(f"Error creating BigQuery client: {e}")
        # Try one more time with default credentials
        try:
            print("[INFO] Attempting to use default application credentials...")
            client = bigquery.Client(project=project_id)
            return client
        except Exception as e2:
            print(f"Error with default credentials: {e2}")
            raise


def execute_query(client: bigquery.Client, sql: str, timeout: int = 120) -> List[Dict[str, Any]]:
    """
    Execute a BigQuery SQL query with timeout.
    
    Args:
        client: BigQuery client instance
        sql: SQL query string
        timeout: Query timeout in seconds (default: 120)
        
    Returns:
        List of dictionaries containing query results
    """
    try:
        from google.cloud.bigquery import QueryJobConfig
        
        # Configure query with timeout
        job_config = QueryJobConfig()
        job_config.use_query_cache = True
        job_config.use_legacy_sql = False
        
        print(f"[DEBUG] Executing BigQuery query (timeout: {timeout}s)...")
        query_job = client.query(sql, job_config=job_config)
        
        # Wait for results with timeout
        print(f"[DEBUG] Waiting for query results...")
        try:
            results = query_job.result(timeout=timeout)
            print(f"[DEBUG] Query completed successfully")
        except Exception as timeout_error:
            # Try to cancel the job if it times out
            try:
                query_job.cancel()
                print(f"[WARNING] Query cancelled due to timeout")
            except:
                pass
            raise Exception(f"Query timed out after {timeout} seconds: {timeout_error}")
        
        # Convert to list of dictionaries
        data = []
        row_count = 0
        for row in results:
            data.append(dict(row.items()))
            row_count += 1
            if row_count % 1000 == 0:
                print(f"[DEBUG] Processed {row_count} rows...")
        
        print(f"[DEBUG] Query returned {len(data)} total rows")
        return data
        
    except Exception as e:
        print(f"[ERROR] BigQuery query error: {e}")
        raise Exception(f"Error executing BigQuery query: {e}")


def test_connection(project_id: str = None) -> bool:
    """Test BigQuery connection and return True if successful."""
    try:
        client = get_bigquery_client(project_id)
        # Run a simple test query
        query = "SELECT 1 as test"
        query_job = client.query(query)
        query_job.result()
        return True
    except Exception as e:
        print(f"BigQuery connection test failed: {e}")
        return False

