#!/usr/bin/env python3
"""
Environment utilities for detecting local vs production environments
and handling environment-specific configurations.
"""

import os
from pathlib import Path
from typing import Optional, Tuple


def is_local_development() -> bool:
    """
    Detect if running in local development environment.
    
    Checks for:
    - RENDER environment variable (not set locally, set on Render)
    - Local .env file existence
    - Development-specific environment variables
    
    Returns:
        True if running locally, False if on Render/production
    """
    # Render sets RENDER environment variable
    if os.environ.get('RENDER'):
        return False
    
    # Check for common production indicators
    if os.environ.get('DYNO'):  # Heroku
        return False
    if os.environ.get('RAILWAY_ENVIRONMENT'):  # Railway
        return False
    
    # If we're here, likely local development
    return True


def is_render() -> bool:
    """Check if running on Render."""
    return bool(os.environ.get('RENDER'))


def get_env_file_path(repo_root: Optional[Path] = None) -> Optional[Path]:
    """
    Find the .env file path.
    
    Args:
        repo_root: Optional repository root path. If None, tries to detect it.
    
    Returns:
        Path to .env file if found, None otherwise
    """
    if repo_root is None:
        # Try to find repo root by looking for common markers
        current = Path(__file__).resolve()
        # Look for ncrc-test-apps directory
        for parent in current.parents:
            if parent.name == 'ncrc-test-apps':
                repo_root = parent
                break
        
        # Fallback: assume .env is in current directory
        if repo_root is None:
            repo_root = Path.cwd()
    
    env_path = repo_root / '.env'
    if env_path.exists():
        return env_path
    
    # Fallback: check current directory
    env_path = Path.cwd() / '.env'
    if env_path.exists():
        return env_path
    
    return None


def load_env_file(repo_root: Optional[Path] = None, verbose: bool = False) -> bool:
    """
    [DEPRECATED/BACKUP] Load .env file if it exists and we're in local development.
    
    NOTE: This function is now a backup/fallback. New code should use:
    from justdata.shared.utils.unified_env import ensure_unified_env_loaded
    ensure_unified_env_loaded(verbose=True)
    
    This function delegates to the unified environment system for consistency.
    
    Args:
        repo_root: Optional repository root path (deprecated, kept for compatibility)
        verbose: If True, print debug messages
    
    Returns:
        True if .env file was loaded, False otherwise
    """
    # Delegate to unified environment system (primary method)
    try:
        from justdata.shared.utils.unified_env import ensure_unified_env_loaded
        return ensure_unified_env_loaded(verbose=verbose)
    except ImportError:
        # Fallback to old method if unified_env not available
        if verbose:
            print("[ENV] Unified env system not available, using legacy method")
        
        # Only load .env in local development
        if not is_local_development():
            if verbose:
                print("[ENV] Running on production (Render), skipping .env file load")
            return False
        
        try:
            from dotenv import load_dotenv
        except ImportError:
            if verbose:
                print("[ENV] python-dotenv not installed, skipping .env file load")
            return False
        
        env_path = get_env_file_path(repo_root)
        if env_path and env_path.exists():
            load_dotenv(env_path, override=False)  # Don't override existing env vars
            if verbose:
                print(f"[ENV] Loaded .env file from: {env_path}")
            return True
        else:
            if verbose:
                print(f"[ENV] No .env file found (checked: {env_path})")
            return False


def get_api_key(key_name: str, fallback_name: Optional[str] = None, 
                clean: bool = True, verbose: bool = False) -> Optional[str]:
    """
    Get API key from environment, with proper handling for local vs production.
    
    Args:
        key_name: Primary environment variable name (e.g., 'CLAUDE_API_KEY')
        fallback_name: Optional fallback name (e.g., 'ANTHROPIC_API_KEY')
        clean: If True, strip whitespace and quotes
        verbose: If True, print debug messages
    
    Returns:
        API key value, or None if not found
    """
    # Try primary key
    api_key = os.getenv(key_name)
    
    # Try fallback if primary not found
    if not api_key and fallback_name:
        api_key = os.getenv(fallback_name)
    
    if not api_key:
        if verbose:
            print(f"[ENV] {key_name} not found in environment")
        return None
    
    if clean:
        # Remove whitespace
        api_key = api_key.strip()
        
        # Remove quotes if present (common .env file issue)
        if (api_key.startswith('"') and api_key.endswith('"')) or \
           (api_key.startswith("'") and api_key.endswith("'")):
            api_key = api_key[1:-1].strip()
            if verbose:
                print(f"[ENV] Removed quotes from {key_name}")
        
        # Check for whitespace issues
        if ' ' in api_key or '\n' in api_key or '\t' in api_key:
            if verbose:
                print(f"[WARNING] {key_name} contains whitespace - this may cause authentication issues")
    
    if verbose and api_key:
        # Show preview without exposing full key
        preview = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
        print(f"[ENV] {key_name} found (length: {len(api_key)}, preview: {preview})")
    
    return api_key


def get_config_summary() -> dict:
    """
    [DEPRECATED/BACKUP] Get a summary of current environment configuration.
    
    NOTE: This function is now a backup/fallback. New code should use:
    from justdata.shared.utils.unified_env import get_unified_config
    config = get_unified_config(verbose=True)
    
    This function delegates to the unified environment system for consistency.
    
    Returns:
        Dictionary with environment information
    """
    # Try to use unified config first (primary method)
    try:
        from justdata.shared.utils.unified_env import get_unified_config, find_shared_env_file
        config = get_unified_config(load_env=False, verbose=False)
        env_path = find_shared_env_file()
        return {
            'is_local': config.get('IS_LOCAL', is_local_development()),
            'is_render': config.get('IS_RENDER', is_render()),
            'env_file_exists': env_path is not None and env_path.exists(),
            'env_file_path': str(env_path) if env_path else None,
            'has_claude_key': bool(config.get('CLAUDE_API_KEY')),
            'has_census_key': bool(config.get('CENSUS_API_KEY')),
            'has_google_creds': bool(config.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')),
        }
    except ImportError:
        # Fallback to old method if unified_env not available
        return {
            'is_local': is_local_development(),
            'is_render': is_render(),
            'env_file_exists': get_env_file_path() is not None,
            'env_file_path': str(get_env_file_path()) if get_env_file_path() else None,
            'has_claude_key': bool(get_api_key('CLAUDE_API_KEY', 'ANTHROPIC_API_KEY', verbose=False)),
            'has_census_key': bool(get_api_key('CENSUS_API_KEY', verbose=False)),
            'has_google_creds': bool(os.getenv('GOOGLE_APPLICATION_CREDENTIALS')),
        }



