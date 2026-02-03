#!/usr/bin/env python3
"""
BigQuery utilities for data analysis.
Shared across BranchSight, BizSight, LendSight, and other JustData apps.

Supports per-app service account credentials for cost attribution.
Each app can have its own credentials via {APP_NAME}_CREDENTIALS_JSON env var.
"""

import os
import json
import tempfile
import logging
from google.cloud import bigquery
from google.oauth2 import service_account
from typing import List, Dict, Any, Optional

logger = logging.getLogger('bigquery_client')


# Valid app names for per-app credentials
VALID_APP_NAMES = [
    'LENDSIGHT',
    'BIZSIGHT', 
    'BRANCHSIGHT',
    'BRANCHMAPPER',
    'MERGERMETER',
    'DATAEXPLORER',
    'LENDERPROFILE',
    'ANALYTICS',
    'ELECTWATCH',
]


def escape_sql_string(value: str) -> str:
    """
    Escape a string value for safe use in BigQuery SQL queries.
    BigQuery uses backslash escaping for special characters in single-quoted strings.

    Args:
        value: String value to escape

    Returns:
        Escaped string safe for BigQuery SQL interpolation
    """
    if value is None:
        return ''
    # BigQuery uses backslash escaping (not SQL-standard double apostrophe)
    # Escape backslashes first, then apostrophes
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


# Cache for credential path to avoid repeated lookups and messages
_credential_path_cache = None
_temp_cred_file = None
# Cache for per-app clients to avoid recreating them
_app_client_cache: Dict[str, bigquery.Client] = {}


def _parse_credentials_json(cred_json_str: str) -> dict:
    """Parse credentials JSON string, handling newline escaping issues.
    
    Args:
        cred_json_str: JSON string containing service account credentials
        
    Returns:
        Parsed credentials dictionary
        
    Raises:
        json.JSONDecodeError: If JSON is invalid
        ValueError: If required fields are missing
    """
    import re
    
    cred_json_str = cred_json_str.strip()
    
    # Try to parse JSON, with fallback for literal newlines in private_key
    try:
        cred_dict = json.loads(cred_json_str)
    except json.JSONDecodeError as parse_error:
        # If parsing fails, it might be due to literal newlines in the private_key
        def escape_newlines_in_key(match):
            key_content = match.group(1)
            key_content = key_content.replace('\r\n', '\\n').replace('\n', '\\n').replace('\r', '\\n')
            return f'"private_key":"{key_content}"'

        fixed_json = re.sub(
            r'"private_key"\s*:\s*"([^"]*(?:\\.[^"]*)*)"',
            escape_newlines_in_key,
            cred_json_str,
            flags=re.DOTALL
        )
        cred_dict = json.loads(fixed_json)
    
    # Validate required fields
    if not isinstance(cred_dict, dict):
        raise ValueError("Credentials must be a JSON object")
    if 'type' not in cred_dict:
        raise ValueError("Missing 'type' field in service account JSON")
    if 'private_key' not in cred_dict:
        raise ValueError("Missing 'private_key' field in service account JSON")
    if 'client_email' not in cred_dict:
        raise ValueError("Missing 'client_email' field in service account JSON")
    
    # Ensure private_key has actual newlines, not escaped ones
    if 'private_key' in cred_dict:
        private_key = cred_dict['private_key']
        if '\\n' in private_key and chr(10) not in private_key:
            cred_dict['private_key'] = private_key.replace('\\n', '\n')
    
    return cred_dict


def _get_credentials_from_env(app_name: Optional[str] = None) -> Optional[tuple]:
    """Get credentials from environment variables.
    
    Checks for app-specific credentials first, then falls back to shared credentials.
    
    Args:
        app_name: Optional app name (e.g., 'LENDSIGHT', 'BIZSIGHT') for per-app credentials
        
    Returns:
        Tuple of (credentials, found_var_name) or None if not found
    """
    env_var_names = []
    
    # If app_name is provided, check for app-specific credentials first
    if app_name:
        app_name_upper = app_name.upper()
        if app_name_upper in VALID_APP_NAMES:
            env_var_names.append(f"{app_name_upper}_CREDENTIALS_JSON")
    
    # Then check shared/fallback credentials
    env_var_names.extend([
        "GOOGLE_APPLICATION_CREDENTIALS_JSON",
        "GOOGLE_CREDENTIALS_JSON", 
        "GCP_CREDENTIALS_JSON"
    ])
    
    for var_name in env_var_names:
        if var_name in os.environ and os.environ[var_name].strip():
            cred_json_str = os.environ[var_name]
            try:
                cred_dict = _parse_credentials_json(cred_json_str)
                credentials = service_account.Credentials.from_service_account_info(cred_dict)
                client_email = cred_dict.get('client_email', 'unknown')
                logger.info(f"Using credentials from {var_name} (service account: {client_email})")
                return (credentials, var_name)
            except Exception as e:
                logger.warning(f"Failed to parse credentials from {var_name}: {e}")
                continue
    
    # Also check GOOGLE_APPLICATION_CREDENTIALS if it contains JSON
    if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
        cred_value = os.environ["GOOGLE_APPLICATION_CREDENTIALS"].strip()
        if cred_value.startswith('{'):
            try:
                cred_dict = _parse_credentials_json(cred_value)
                credentials = service_account.Credentials.from_service_account_info(cred_dict)
                logger.info(f"Using JSON credentials from GOOGLE_APPLICATION_CREDENTIALS")
                return (credentials, "GOOGLE_APPLICATION_CREDENTIALS")
            except Exception as e:
                logger.warning(f"Failed to parse JSON from GOOGLE_APPLICATION_CREDENTIALS: {e}")
    
    return None


def get_bigquery_client(project_id: str = None, app_name: str = None):
    """Get BigQuery client using environment-based credentials.
    
    Supports per-app service account credentials for cost attribution.
    Checks for {APP_NAME}_CREDENTIALS_JSON first, then falls back to
    GOOGLE_APPLICATION_CREDENTIALS_JSON.
    
    Args:
        project_id: GCP project ID (defaults to GCP_PROJECT_ID env var or 'justdata-ncrc')
        app_name: App name for per-app credentials (e.g., 'lendsight', 'bizsight')
                  If provided, will check for {APP_NAME}_CREDENTIALS_JSON first
    
    Returns:
        BigQuery client instance
        
    Example:
        # Use app-specific credentials
        client = get_bigquery_client(project_id='justdata-ncrc', app_name='lendsight')
        
        # Use shared/default credentials  
        client = get_bigquery_client(project_id='justdata-ncrc')
    """
    from pathlib import Path
    global _credential_path_cache, _temp_cred_file, _app_client_cache
    
    # Normalize app_name
    app_name_key = app_name.upper() if app_name else None
    
    # Check cache first (per-app caching)
    cache_key = f"{project_id}:{app_name_key or 'default'}"
    if cache_key in _app_client_cache:
        return _app_client_cache[cache_key]
    
    try:
        # Ensure unified_env is loaded so credentials are in os.environ
        try:
            from justdata.shared.utils.unified_env import ensure_unified_env_loaded
            ensure_unified_env_loaded(verbose=False)
        except Exception as e:
            logger.debug(f"Failed to load unified_env: {e}")
        
        # Get project ID from env if not provided
        if not project_id:
            project_id = os.getenv('GCP_PROJECT_ID', 'justdata-ncrc')
        
        # Try to get credentials from environment variables
        cred_result = _get_credentials_from_env(app_name_key)
        if cred_result:
            credentials, found_var_name = cred_result
            client = bigquery.Client(credentials=credentials, project=project_id)
            _app_client_cache[cache_key] = client
            return client
        
        # Check for file-based credentials
        env_cred_path = None
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            env_cred_str = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
            # Skip if it looks like JSON (already handled above)
            if not env_cred_str.strip().startswith('{'):
                if os.sep in env_cred_str or '/' in env_cred_str or '\\' in env_cred_str or env_cred_str.endswith('.json'):
                    env_cred_path = Path(env_cred_str)
                    if env_cred_path.exists() and env_cred_path.is_file():
                        _credential_path_cache = env_cred_path
                        logger.info(f"Using credentials from file: {env_cred_path}")
                        credentials = service_account.Credentials.from_service_account_file(str(env_cred_path))
                        client = bigquery.Client(credentials=credentials, project=project_id)
                        _app_client_cache[cache_key] = client
                        return client
        
        # If we have a cached path, use it (avoids repeated lookups and messages)
        if _credential_path_cache and _credential_path_cache.exists():
            credentials = service_account.Credentials.from_service_account_file(str(_credential_path_cache))
            client = bigquery.Client(credentials=credentials, project=project_id)
            _app_client_cache[cache_key] = client
            return client
        
        # Try to find credentials file in common locations (fallback - prefer environment variables)
        possible_paths = [
            Path("config/credentials/bigquery_service_account.json"),
            Path(__file__).parent.parent.parent / "config" / "credentials" / "bigquery_service_account.json",
            Path(__file__).parent.parent.parent / "credentials" / "bigquery_service_account.json",
        ]
        
        cred_path = None
        for path in possible_paths:
            if path.exists():
                cred_path = path
                break
        
        if cred_path:
            _credential_path_cache = cred_path
            logger.info(f"Using credentials from file: {cred_path}")
            credentials = service_account.Credentials.from_service_account_file(str(cred_path))
            client = bigquery.Client(credentials=credentials, project=project_id)
            _app_client_cache[cache_key] = client
            return client
        
        # Fallback: try default service account (for cloud deployments)
        logger.info("No credentials found, using default service account...")
        client = bigquery.Client(project=project_id)
        _app_client_cache[cache_key] = client
        return client
        
    except Exception as e:
        logger.error(f"Error creating BigQuery client: {e}")
        # Try one more time with default credentials
        try:
            logger.info("Attempting to use default application credentials...")
            client = bigquery.Client(project=project_id)
            _app_client_cache[cache_key] = client
            return client
        except Exception as e2:
            logger.error(f"Error with default credentials: {e2}")
            raise


def clear_client_cache():
    """Clear the cached BigQuery clients. Useful for testing or credential rotation."""
    global _app_client_cache, _credential_path_cache
    _app_client_cache = {}
    _credential_path_cache = None


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
        
        query_job = client.query(sql, job_config=job_config)
        
        # Wait for results with timeout
        try:
            results = query_job.result(timeout=timeout)
        except Exception as timeout_error:
            # Try to cancel the job if it times out
            try:
                query_job.cancel()
                logger.warning("Query cancelled due to timeout")
            except:
                pass
            raise Exception(f"Query timed out after {timeout} seconds: {timeout_error}")
        
        # Convert to list of dictionaries
        data = [dict(row.items()) for row in results]
        logger.debug(f"Query returned {len(data)} rows")
        return data
        
    except Exception as e:
        logger.error(f"BigQuery query error: {e}")
        raise Exception(f"Error executing BigQuery query: {e}")


def test_connection(project_id: str = None, app_name: str = None) -> bool:
    """Test BigQuery connection and return True if successful.
    
    Args:
        project_id: GCP project ID
        app_name: App name for per-app credentials testing
        
    Returns:
        True if connection is successful
    """
    try:
        client = get_bigquery_client(project_id, app_name=app_name)
        # Run a simple test query
        query = "SELECT 1 as test"
        query_job = client.query(query)
        query_job.result()
        return True
    except Exception as e:
        logger.error(f"BigQuery connection test failed: {e}")
        return False

