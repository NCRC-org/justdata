#!/usr/bin/env python3
"""
Static Report Caching System for JustData.

Serves pre-generated static report files to users, eliminating redundant API and AI calls.
Reports are generated once (on first request or admin regeneration) and served as static files.

File Storage:
    Location: {REPO_ROOT}/cache/reports/{app}/{state}/{county}.json

    Naming Convention:
    - Lowercase
    - Spaces → underscores
    - Apostrophes → removed
    - Example: "St. Mary's County, Maryland" → "st_marys_county.json"
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Cache root directory (at repo root level)
REPO_ROOT = Path(__file__).parent.parent.parent.parent.absolute()
CACHE_ROOT = REPO_ROOT / 'cache' / 'reports'


def sanitize_filename(name: str) -> str:
    """
    Convert county/state name to safe filename.

    Args:
        name: Original name (e.g., "St. Mary's County" or "Maryland")

    Returns:
        Sanitized filename (e.g., "st_marys_county" or "maryland")
    """
    if not name:
        return "unknown"

    name = name.lower()
    name = name.replace("'", "")       # Remove apostrophes (O'Brien → obrien)
    name = name.replace(".", "")       # Remove periods (St. Mary's → st marys)
    name = name.replace(" ", "_")      # Spaces to underscores
    name = re.sub(r'[^a-z0-9_]', '', name)  # Remove other special chars
    name = re.sub(r'_+', '_', name)    # Collapse multiple underscores
    name = name.strip('_')             # Remove leading/trailing underscores
    return name


def get_cache_path(app: str, state: str, county: str) -> Path:
    """
    Return full path to cached report file.

    Args:
        app: App name (lendsight, bizsight, branchsight)
        state: State name (e.g., "Maryland")
        county: County name (e.g., "St. Mary's County")

    Returns:
        Path object to the cache file
    """
    state_clean = sanitize_filename(state)
    county_clean = sanitize_filename(county)
    return CACHE_ROOT / app / state_clean / f"{county_clean}.json"


def cache_exists(app: str, state: str, county: str) -> bool:
    """
    Check if cached report exists.

    Args:
        app: App name
        state: State name
        county: County name

    Returns:
        True if cache file exists, False otherwise
    """
    path = get_cache_path(app, state, county)
    exists = path.exists()
    if exists:
        logger.info(f"[CACHE] Cache hit: {path}")
    else:
        logger.info(f"[CACHE] Cache miss: {path}")
    return exists


def load_from_cache(app: str, state: str, county: str) -> Optional[Dict[str, Any]]:
    """
    Load cached report from file.

    Args:
        app: App name
        state: State name
        county: County name

    Returns:
        Report data dictionary, or None if file doesn't exist or is invalid
    """
    path = get_cache_path(app, state, county)

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"[CACHE] Loaded report from cache: {path}")
            return data
    except FileNotFoundError:
        logger.warning(f"[CACHE] Cache file not found: {path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"[CACHE] Invalid JSON in cache file {path}: {e}")
        return None
    except Exception as e:
        logger.error(f"[CACHE] Error loading cache file {path}: {e}")
        return None


def save_to_cache(app: str, state: str, county: str, report_data: Dict[str, Any]) -> bool:
    """
    Save report to cache file.

    Args:
        app: App name
        state: State name
        county: County name
        report_data: Complete report data dictionary

    Returns:
        True if successfully saved, False otherwise
    """
    path = get_cache_path(app, state, county)

    try:
        # Create directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Add cache metadata
        report_data['_cache_metadata'] = {
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'app': app,
            'state': state,
            'county': county,
            'cache_path': str(path.relative_to(REPO_ROOT))
        }

        # Write to file
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)

        logger.info(f"[CACHE] Saved report to cache: {path}")
        return True

    except Exception as e:
        logger.error(f"[CACHE] Error saving cache file {path}: {e}")
        return False


def delete_cache(app: str, state: str, county: str) -> bool:
    """
    Delete cached report file.

    Args:
        app: App name
        state: State name
        county: County name

    Returns:
        True if successfully deleted or didn't exist, False on error
    """
    path = get_cache_path(app, state, county)

    try:
        if path.exists():
            path.unlink()
            logger.info(f"[CACHE] Deleted cache file: {path}")
        return True
    except Exception as e:
        logger.error(f"[CACHE] Error deleting cache file {path}: {e}")
        return False


def get_cache_info(app: str, state: str, county: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata about a cached report without loading full content.

    Args:
        app: App name
        state: State name
        county: County name

    Returns:
        Dictionary with cache info (exists, path, generated_at) or None
    """
    path = get_cache_path(app, state, county)

    if not path.exists():
        return None

    try:
        # Read just the metadata
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            metadata = data.get('_cache_metadata', {})

            return {
                'exists': True,
                'path': str(path),
                'generated_at': metadata.get('generated_at'),
                'file_size_kb': path.stat().st_size / 1024
            }
    except Exception as e:
        logger.error(f"[CACHE] Error reading cache info for {path}: {e}")
        return {'exists': True, 'path': str(path), 'error': str(e)}


def is_staff_user(user_type: str) -> bool:
    """
    Check if user type has staff/admin privileges (can regenerate reports).

    Args:
        user_type: User type string from session

    Returns:
        True if user is staff or admin, False otherwise
    """
    return user_type in ('staff', 'admin')


def extract_state_county_from_data(county_data: dict) -> tuple:
    """
    Extract state and county names from county_data object.

    Args:
        county_data: County data dictionary from frontend

    Returns:
        Tuple of (state_name, county_name)
    """
    # Try different field names
    county_name = (
        county_data.get('county_name') or
        county_data.get('name', '').split(',')[0].strip() or
        'unknown'
    )

    state_name = (
        county_data.get('state_name') or
        county_data.get('state') or
        (county_data.get('name', '').split(',')[1].strip() if ',' in county_data.get('name', '') else '') or
        'unknown'
    )

    return state_name, county_name
