#!/usr/bin/env python3
"""
BigQuery utilities for data analysis.
Shared across BranchSeeker, BizSight, and LendSight.
"""

import os
from google.cloud import bigquery
from google.oauth2 import service_account
from typing import List, Dict, Any


def get_bigquery_client(project_id: str = None):
    """Get BigQuery client using environment-based credentials."""
    try:
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            # Local: use key file
            credentials = service_account.Credentials.from_service_account_file(
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
            )
            client = bigquery.Client(credentials=credentials, project=project_id)
        else:
            # Cloud: use default service account
            client = bigquery.Client(project=project_id)
        return client
    except Exception as e:
        print(f"Error creating BigQuery client: {e}")
        raise


def execute_query(client: bigquery.Client, sql: str) -> List[Dict[str, Any]]:
    """
    Execute a BigQuery SQL query.
    
    Args:
        client: BigQuery client instance
        sql: SQL query string
        
    Returns:
        List of dictionaries containing query results
    """
    try:
        query_job = client.query(sql)
        results = query_job.result()
        
        # Convert to list of dictionaries
        data = []
        for row in results:
            data.append(dict(row.items()))
        
        return data
        
    except Exception as e:
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

