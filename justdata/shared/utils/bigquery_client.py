#!/usr/bin/env python3
"""
BigQuery utilities for data analysis.
Shared across BranchSight, BizSight, and LendSight.
"""

import os
import json
import tempfile
from google.cloud import bigquery
from google.oauth2 import service_account
from typing import List, Dict, Any


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

def get_bigquery_client(project_id: str = None):
    """Get BigQuery client using environment-based credentials.
    
    VERSION: 2025-12-17-EXTENSIVE-DEBUGGING
    """
    from pathlib import Path
    global _credential_path_cache, _temp_cred_file
    
    # VERSION CHECK - Write to file immediately to verify function is called
    from datetime import datetime
    import sys
    import logging
    
    # Use absolute path and also write to existing debug log
    debug_file_path = Path(__file__).parent.parent.parent / "bigquery_client_debug.log"
    debug_file_path_str = str(debug_file_path)
    
    # Also use the existing logger
    logger = logging.getLogger('bigquery_client')
    
    logger.critical(f"========== get_bigquery_client() CALLED - VERSION 2025-12-17-EXTENSIVE-DEBUGGING ==========")
    logger.critical(f"project_id parameter: {project_id}")
    print(f"[CRITICAL] get_bigquery_client() CALLED - VERSION 2025-12-17", flush=True)
    sys.stdout.flush()
    
    try:
        with open(debug_file_path_str, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"[{datetime.now()}] get_bigquery_client() CALLED - VERSION 2025-12-17-EXTENSIVE-DEBUGGING\n")
            f.write(f"[{datetime.now()}] project_id parameter: {project_id}\n")
            f.write(f"[{datetime.now()}] Working directory: {Path.cwd()}\n")
            f.flush()
    except Exception as e:
        # If file write fails, at least print to stdout and logger
        error_msg = f"[CRITICAL] Failed to write debug file: {e}"
        print(error_msg, flush=True)
        logger.critical(error_msg)
        sys.stdout.flush()
    
    try:
        # Ensure unified_env is loaded so credentials are in os.environ
        try:
            from justdata.shared.utils.unified_env import ensure_unified_env_loaded
            ensure_unified_env_loaded(verbose=False)
        except Exception as e:
            print(f"[WARNING] Failed to load unified_env: {e}", flush=True)
        
        # First, check if credentials are provided as JSON string (for Render/cloud deployments)
        # Check both exact name and common variations
        cred_json_str = None
        found_var_name = None
        
        # Check for JSON-specific env vars first
        # Write to file AND print to ensure we see it
        debug_file_path = "bigquery_client_debug.log"
        import sys
        from datetime import datetime
        
        try:
            with open(debug_file_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"[{datetime.now()}] get_bigquery_client() called with project_id={project_id}\n")
                f.write(f"[{datetime.now()}] Checking for JSON credentials in environment variables...\n")
                f.flush()
        except:
            pass
        
        print(f"[DEBUG] Checking for JSON credentials in environment variables...", flush=True)
        sys.stdout.flush()
        env_var_names = ["GOOGLE_APPLICATION_CREDENTIALS_JSON", "GOOGLE_CREDENTIALS_JSON", "GCP_CREDENTIALS_JSON"]
        for var_name in env_var_names:
            print(f"[DEBUG]   Checking {var_name}...", flush=True)
            sys.stdout.flush()
            try:
                with open(debug_file_path, 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now()}]   Checking {var_name}...\n")
                    f.flush()
            except:
                pass
            if var_name in os.environ:
                cred_json_str = os.environ[var_name]
                found_var_name = var_name
                print(f"[INFO] Found credentials in environment variable: {var_name}", flush=True)
                print(f"[DEBUG]   Value length: {len(cred_json_str)}", flush=True)
                sys.stdout.flush()
                try:
                    with open(debug_file_path, 'a', encoding='utf-8') as f:
                        f.write(f"[{datetime.now()}]   FOUND {var_name} (length: {len(cred_json_str)})\n")
                        f.write(f"[{datetime.now()}]   First 100 chars: {cred_json_str[:100]}\n")
                        f.write(f"[{datetime.now()}]   Last 100 chars: {cred_json_str[-100:]}\n")
                        f.flush()
                except:
                    pass
                break
            else:
                print(f"[DEBUG]   {var_name} not found", flush=True)
                sys.stdout.flush()
                try:
                    with open(debug_file_path, 'a', encoding='utf-8') as f:
                        f.write(f"[{datetime.now()}]   {var_name} NOT FOUND\n")
                        f.flush()
                except:
                    pass
        
        # Also check GOOGLE_APPLICATION_CREDENTIALS - if it looks like JSON (starts with {), use it as JSON
        # Otherwise it will be treated as a file path later
        if not cred_json_str and "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
            cred_value = os.environ["GOOGLE_APPLICATION_CREDENTIALS"].strip()
            # If it starts with {, it's JSON content, not a file path
            if cred_value.startswith('{'):
                cred_json_str = cred_value
                found_var_name = "GOOGLE_APPLICATION_CREDENTIALS"
                print(f"[INFO] Found JSON credentials in GOOGLE_APPLICATION_CREDENTIALS (treating as JSON content)")
        
        if cred_json_str:
            # Strip whitespace in case it was added accidentally
            cred_json_str = cred_json_str.strip()
            if not cred_json_str:
                print("[WARNING] GOOGLE_APPLICATION_CREDENTIALS_JSON is set but empty", flush=True)
                sys.stdout.flush()
            else:
                try:
                    print(f"[DEBUG] Attempting to parse JSON credentials from {found_var_name} (length: {len(cred_json_str)} chars)...", flush=True)
                    sys.stdout.flush()
                    
                    # Write to debug file
                    try:
                        with open(debug_file_path, 'a', encoding='utf-8') as f:
                            f.write(f"[{datetime.now()}] Parsing JSON credentials (length: {len(cred_json_str)})\n")
                            f.write(f"[{datetime.now()}] First 100 chars: {cred_json_str[:100]}\n")
                            f.write(f"[{datetime.now()}] Last 100 chars: {cred_json_str[-100:]}\n")
                            f.flush()
                    except:
                        pass
                    
                    # Try to parse JSON, with fallback for literal newlines in private_key
                    try:
                        cred_dict = json.loads(cred_json_str)
                    except json.JSONDecodeError as parse_error:
                        # If parsing fails, it might be due to literal newlines in the private_key
                        # Try to escape them before parsing
                        import re
                        print(f"[DEBUG] Initial JSON parse failed: {parse_error}, attempting to fix newlines...", flush=True)

                        def escape_newlines_in_key(match):
                            key_content = match.group(1)
                            # Replace literal newlines with escaped newlines
                            key_content = key_content.replace('\r\n', '\\n').replace('\n', '\\n').replace('\r', '\\n')
                            return f'"private_key":"{key_content}"'

                        fixed_json = re.sub(
                            r'"private_key"\s*:\s*"([^"]*(?:\\.[^"]*)*)"',
                            escape_newlines_in_key,
                            cred_json_str,
                            flags=re.DOTALL
                        )
                        cred_dict = json.loads(fixed_json)
                        print(f"[DEBUG] Successfully parsed credentials after fixing newlines", flush=True)

                    print(f"[DEBUG] Successfully parsed credentials JSON. Project: {cred_dict.get('project_id', 'N/A')}, Client email: {cred_dict.get('client_email', 'N/A')[:50]}...", flush=True)
                    sys.stdout.flush()
                    
                    # Write parsed info to debug file
                    try:
                        with open(debug_file_path, 'a', encoding='utf-8') as f:
                            f.write(f"[{datetime.now()}] Successfully parsed JSON\n")
                            f.write(f"[{datetime.now()}] Project ID: {cred_dict.get('project_id', 'N/A')}\n")
                            f.write(f"[{datetime.now()}] Client email: {cred_dict.get('client_email', 'N/A')}\n")
                            f.write(f"[{datetime.now()}] Private key ID: {cred_dict.get('private_key_id', 'N/A')}\n")
                            f.write(f"[{datetime.now()}] Has private_key: {'private_key' in cred_dict}\n")
                            f.flush()
                    except:
                        pass
                    
                    # Validate it has required fields
                    if not isinstance(cred_dict, dict):
                        raise ValueError("Credentials must be a JSON object")
                    if 'type' not in cred_dict:
                        raise ValueError("Missing 'type' field in service account JSON")
                    if 'private_key' not in cred_dict:
                        raise ValueError("Missing 'private_key' field in service account JSON")
                    if 'client_email' not in cred_dict:
                        raise ValueError("Missing 'client_email' field in service account JSON")
                    
                    # Create credentials from dict
                    print("[DEBUG] Creating service account credentials from JSON...", flush=True)
                    sys.stdout.flush()
                    
                    # Write to file for debugging
                    try:
                        with open(debug_file_path, 'a', encoding='utf-8') as f:
                            f.write(f"[{datetime.now()}] Creating service account credentials from JSON...\n")
                            f.write(f"[{datetime.now()}] Project ID: {cred_dict.get('project_id', 'N/A')}\n")
                            f.write(f"[{datetime.now()}] Client email: {cred_dict.get('client_email', 'N/A')}\n")
                            f.write(f"[{datetime.now()}] Private key ID: {cred_dict.get('private_key_id', 'N/A')}\n")
                            private_key = cred_dict.get('private_key', '')
                            escaped_newline = '\\n'
                            f.write(f"[{datetime.now()}] Private key length: {len(private_key)}\n")
                            f.write(f"[{datetime.now()}] Private key starts with: {private_key[:50]}\n")
                            f.write(f"[{datetime.now()}] Private key has actual newlines: {chr(10) in private_key}\n")
                            f.write(f"[{datetime.now()}] Private key has escaped newlines: {escaped_newline in private_key}\n")
                            f.flush()
                    except Exception as e:
                        print(f"[WARNING] Failed to write debug info: {e}", flush=True)
                    
                    # Ensure private_key has actual newlines, not escaped ones
                    # The JSON parser should handle this, but let's be explicit
                    if 'private_key' in cred_dict:
                        private_key = cred_dict['private_key']
                        # If it has escaped newlines (\\n), convert them to actual newlines
                        if '\\n' in private_key and chr(10) not in private_key:
                            cred_dict['private_key'] = private_key.replace('\\n', '\n')
                            print("[DEBUG] Converted escaped newlines to actual newlines in private_key", flush=True)
                            sys.stdout.flush()
                    
                    credentials = service_account.Credentials.from_service_account_info(cred_dict)
                    client = bigquery.Client(credentials=credentials, project=project_id)
                    
                    try:
                        with open(debug_file_path, 'a', encoding='utf-8') as f:
                            f.write(f"[{datetime.now()}] BigQuery client created successfully\n")
                            f.write(f"[{datetime.now()}] Client project: {client.project}\n")
                            f.flush()
                    except:
                        pass
                    
                    print("[INFO] Successfully using credentials from GOOGLE_APPLICATION_CREDENTIALS_JSON", flush=True)
                    sys.stdout.flush()
                    return client
                except json.JSONDecodeError as e:
                    print(f"[ERROR] GOOGLE_APPLICATION_CREDENTIALS_JSON contains invalid JSON: {e}")
                    print(f"[DEBUG] First 200 chars of value: {cred_json_str[:200]}...")
                    print("[ERROR] Please check that the JSON is valid and complete")
                except Exception as e:
                    print(f"[ERROR] Error parsing GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")
                    import traceback
                    print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        else:
            print("[WARNING] GOOGLE_APPLICATION_CREDENTIALS_JSON not found in environment variables", flush=True)
            available_vars = [k for k in os.environ.keys() if 'GOOGLE' in k or 'GCP' in k or 'CREDENTIAL' in k]
            print("[INFO] Available env vars (filtered): " + ", ".join(available_vars), flush=True)
            sys.stdout.flush()
            
            # Write to file
            try:
                with open(debug_file_path, 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now()}] WARNING: GOOGLE_APPLICATION_CREDENTIALS_JSON not found\n")
                    f.write(f"[{datetime.now()}] Available env vars: {', '.join(available_vars)}\n")
                    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                        cred_path_val = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
                        f.write(f"[{datetime.now()}] GOOGLE_APPLICATION_CREDENTIALS value: {cred_path_val[:100]}...\n")
                    f.flush()
            except:
                pass
        
        # Second, check environment variable for file path (only if we didn't already use it as JSON)
        env_cred_path = None
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and found_var_name != "GOOGLE_APPLICATION_CREDENTIALS":
            env_cred_str = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
            # Skip if it looks like JSON (already handled above)
            if env_cred_str.strip().startswith('{'):
                print("[INFO] GOOGLE_APPLICATION_CREDENTIALS contains JSON, skipping file path check", flush=True)
                sys.stdout.flush()
            # Validate that it looks like a file path (not just a hash or invalid value)
            elif os.sep in env_cred_str or '/' in env_cred_str or '\\' in env_cred_str or env_cred_str.endswith('.json'):
                env_cred_path = Path(env_cred_str)
                print(f"[DEBUG] Checking file path: {env_cred_path}", flush=True)
                sys.stdout.flush()
                try:
                    with open(debug_file_path, 'a', encoding='utf-8') as f:
                        f.write(f"[{datetime.now()}] Checking GOOGLE_APPLICATION_CREDENTIALS file path: {env_cred_path}\n")
                        f.write(f"[{datetime.now()}] File exists: {env_cred_path.exists()}\n")
                        f.flush()
                except:
                    pass
                if env_cred_path.exists() and env_cred_path.is_file():
                    # Cache the working path
                    _credential_path_cache = env_cred_path
                    print(f"[INFO] Using credentials from file: {env_cred_path}", flush=True)
                    sys.stdout.flush()
                    try:
                        with open(debug_file_path, 'a', encoding='utf-8') as f:
                            f.write(f"[{datetime.now()}] USING FILE PATH CREDENTIALS: {env_cred_path}\n")
                            f.flush()
                    except:
                        pass
                    credentials = service_account.Credentials.from_service_account_file(str(env_cred_path))
                    client = bigquery.Client(credentials=credentials, project=project_id)
                    return client
                else:
                    # Invalid path in env var - unset so default client and other libs don't try to load it
                    print(f"[WARNING] GOOGLE_APPLICATION_CREDENTIALS points to non-existent file: {env_cred_path}", flush=True)
                    sys.stdout.flush()
                    if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                        del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
            else:
                # Not a valid file path (might be a hash or other invalid value)
                print(f"[WARNING] GOOGLE_APPLICATION_CREDENTIALS contains invalid value (not a file path): {env_cred_str[:50]}...")
                print("[INFO] Ignoring invalid env var - unsetting it to prevent Google Auth from trying to use it...")
                # Unset the invalid env var so Google Auth doesn't try to use it
                if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                    del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
        
        # If we have a cached path, use it (avoids repeated lookups and messages)
        if _credential_path_cache and _credential_path_cache.exists():
            credentials = service_account.Credentials.from_service_account_file(str(_credential_path_cache))
            client = bigquery.Client(credentials=credentials, project=project_id)
            return client
        
        # Try to find credentials file in common locations
        # Check both the main file and any timestamped backups
        possible_paths = [
            Path("C:/Code/Dream/config/credentials/hdma1-242116-74024e2eb88f.json"),
            Path("C:/DREAM/config/credentials/hdma1-242116-74024e2eb88f.json"),
            Path("C:/DREAM/config/credentials/hdma1-242116-74024e2eb88f_20251102_180816.json"),  # Backup file
            Path("C:/Code/Dream/hdma1-242116-74024e2eb88f.json"),
            Path("C:/DREAM/hdma1-242116-74024e2eb88f.json"),
            Path("config/credentials/hdma1-242116-74024e2eb88f.json"),
            Path("hdma1-242116-74024e2eb88f.json"),
            Path(__file__).parent.parent.parent / "config" / "credentials" / "hdma1-242116-74024e2eb88f.json",
            Path(__file__).parent.parent.parent.parent / "config" / "credentials" / "hdma1-242116-74024e2eb88f.json",
        ]
        
        # Also search the credentials directory for any matching JSON files
        cred_dir = Path("C:/Code/Dream/config/credentials")
        if cred_dir.exists():
            for json_file in cred_dir.glob("hdma1-*.json"):
                if json_file not in possible_paths:
                    possible_paths.append(json_file)
        
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
        
        # If we get here, no credentials found - unset bad path so default client doesn't fail
        if env_cred_path and not env_cred_path.exists():
            if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
            print(f"[WARNING] GOOGLE_APPLICATION_CREDENTIALS pointed to missing file; unset. Set GOOGLE_APPLICATION_CREDENTIALS_JSON (JSON string) in .env for BigQuery.")
        
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
                # Only log every 10,000 rows to reduce log verbosity
                if row_count % 10000 == 0:
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

