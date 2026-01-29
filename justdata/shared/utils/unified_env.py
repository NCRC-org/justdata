#!/usr/bin/env python3
"""
Unified environment configuration for all JustData apps.
This module ensures all apps use the same environment variables,
whether running locally (from .env file) or on Render (from environment variables).

Usage:
    from justdata.shared.utils.unified_env import get_unified_config
    config = get_unified_config()
    claude_key = config.get('CLAUDE_API_KEY')
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, Any
try:
    from justdata.shared.utils.env_utils import (
        is_local_development,
        get_env_file_path,
        load_env_file,
        get_api_key
    )
except ImportError:
    # Fallback for when running from different directory structure
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from justdata.shared.utils.env_utils import (
        is_local_development,
        get_env_file_path,
        load_env_file,
        get_api_key
    )


# Shared environment file path (used by all apps)
SHARED_ENV_FILE = None


def find_shared_env_file() -> Optional[Path]:
    """
    Find the shared .env file in the repository root.
    This is the single source of truth for all JustData apps.
    """
    global SHARED_ENV_FILE
    
    if SHARED_ENV_FILE and SHARED_ENV_FILE.exists():
        return SHARED_ENV_FILE
    
    # Try to find ncrc-test-apps directory
    current = Path(__file__).resolve()
    for parent in current.parents:
        if parent.name == 'ncrc-test-apps':
            env_path = parent / '.env'
            if env_path.exists():
                SHARED_ENV_FILE = env_path
                return env_path
    
    # Fallback: check current directory and common locations
    possible_paths = [
        Path.cwd() / '.env',
        Path.cwd().parent / '.env',
        Path(__file__).parent.parent.parent / '.env',
    ]
    
    for path in possible_paths:
        if path.exists():
            SHARED_ENV_FILE = path
            return path
    
    return None


def load_shared_env(verbose: bool = False) -> bool:
    """
    Load the shared .env file if we're in local development.
    On Render, this will be skipped and environment variables will be used directly.
    
    Args:
        verbose: If True, print debug messages
        
    Returns:
        True if .env file was loaded, False otherwise
    """
    # On Render, don't load .env file - use environment variables directly
    if not is_local_development():
        if verbose:
            print("[UNIFIED_ENV] Running on Render - using environment variables directly")
        return False
    
    # Load shared .env file for local development
    env_path = find_shared_env_file()
    if env_path and env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path, override=False)  # Don't override existing env vars
            if verbose:
                print(f"[UNIFIED_ENV] Loaded shared .env file from: {env_path}")
            return True
        except ImportError:
            if verbose:
                print("[UNIFIED_ENV] python-dotenv not installed, skipping .env file load")
            return False
    else:
        if verbose:
            print(f"[UNIFIED_ENV] Shared .env file not found (checked: {env_path})")
        return False


def get_bigquery_credentials_json() -> Optional[str]:
    """
    Get BigQuery credentials as JSON string.
    Works both locally (from .env or file path) and on Render (from GOOGLE_APPLICATION_CREDENTIALS_JSON).
    
    Returns:
        JSON string of credentials, or None if not found
    """
    # First, check for JSON string in environment (Render or local)
    cred_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    if cred_json:
        # Clean it up
        cred_json = cred_json.strip()
        # Remove quotes if present
        if (cred_json.startswith('"') and cred_json.endswith('"')) or \
           (cred_json.startswith("'") and cred_json.endswith("'")):
            cred_json = cred_json[1:-1].strip()
        return cred_json
    
    # On Render, we should have GOOGLE_APPLICATION_CREDENTIALS_JSON
    # If not, return None
    if not is_local_development():
        return None
    
    # For local development, try to read from file path
    cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if cred_path:
        try:
            cred_file = Path(cred_path)
            if cred_file.exists():
                with open(cred_file, 'r') as f:
                    cred_dict = json.load(f)
                    # Convert back to JSON string (single line)
                    return json.dumps(cred_dict, separators=(',', ':'))
        except Exception as e:
            print(f"[UNIFIED_ENV] Error reading credentials file: {e}")
    
    return None


def get_unified_config(load_env: bool = True, verbose: bool = False) -> Dict[str, Any]:
    """
    Get unified configuration for all JustData apps.
    This ensures all apps use the same environment variables.
    
    Args:
        load_env: If True, load .env file (for local development)
        verbose: If True, print debug messages
        
    Returns:
        Dictionary with all configuration values
    """
    # Load shared .env file if in local development
    if load_env:
        load_shared_env(verbose=verbose)
    
    # Get BigQuery credentials
    bq_creds_json = get_bigquery_credentials_json()
    
    # Build unified config
    config = {
        # BigQuery / GCP
        'GCP_PROJECT_ID': os.getenv('GCP_PROJECT_ID', 'justdata-ncrc'),
        'GOOGLE_APPLICATION_CREDENTIALS_JSON': bq_creds_json,

        # Google Cloud Storage
        'GCS_BUCKET_NAME': os.getenv('GCS_BUCKET_NAME', 'justdata-mergermeter-output'),

        # API Keys
        'CLAUDE_API_KEY': get_api_key('CLAUDE_API_KEY', 'ANTHROPIC_API_KEY', verbose=verbose),
        'CENSUS_API_KEY': get_api_key('CENSUS_API_KEY', verbose=verbose),
        'OPENAI_API_KEY': get_api_key('OPENAI_API_KEY', verbose=verbose),

        # AI Provider
        'AI_PROVIDER': os.getenv('AI_PROVIDER', 'claude'),

        # App Settings
        'DEBUG': os.getenv('DEBUG', 'False').lower() == 'true',
        'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
        'SECRET_KEY': os.getenv('SECRET_KEY', 'change-this-secret'),
        'FLASK_DEBUG': os.getenv('FLASK_DEBUG', 'false').lower() == 'true',

        # Environment info
        'IS_LOCAL': is_local_development(),
        'IS_RENDER': not is_local_development(),
        'SHARED_ENV_FILE': str(find_shared_env_file()) if find_shared_env_file() else None,
    }
    
    if verbose:
        print(f"[UNIFIED_ENV] Configuration loaded:")
        print(f"  - GCP_PROJECT_ID: {config['GCP_PROJECT_ID']}")
        print(f"  - BigQuery credentials: {'Set' if config['GOOGLE_APPLICATION_CREDENTIALS_JSON'] else 'Not set'}")
        print(f"  - CLAUDE_API_KEY: {'Set' if config['CLAUDE_API_KEY'] else 'Not set'}")
        print(f"  - CENSUS_API_KEY: {'Set' if config['CENSUS_API_KEY'] else 'Not set'}")
        print(f"  - Environment: {'Local' if config['IS_LOCAL'] else 'Render'}")
    
    return config


def ensure_unified_env_loaded(verbose: bool = False) -> bool:
    """
    Ensure the unified environment is loaded.
    Call this at the start of each app to ensure shared configuration is available.
    
    Args:
        verbose: If True, print debug messages
        
    Returns:
        True if environment was loaded successfully
    """
    return load_shared_env(verbose=verbose)


# Auto-load on import (for convenience)
# This ensures all apps that import this module get the shared config
if is_local_development():
    load_shared_env(verbose=False)
