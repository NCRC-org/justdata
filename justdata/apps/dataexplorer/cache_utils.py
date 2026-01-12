#!/usr/bin/env python3
"""
Cache utilities for DataExplorer Area Analysis
Stores query results locally to avoid repeated BigQuery calls during development.
"""

import json
import pickle
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Cache directory
# On Render, use /tmp for writable directory (ephemeral but works)
# Locally, use data/cache/dataexplorer
import os

# Detect Render environment - Render sets RENDER_EXTERNAL_URL or we're in /opt/render
is_render = (
    os.getenv('RENDER') is not None or 
    os.getenv('RENDER_EXTERNAL_URL') is not None or
    Path('/opt/render').exists()
)

if is_render:
    # Render environment - use /tmp (writable, but ephemeral)
    CACHE_DIR = Path('/tmp') / 'dataexplorer_cache'
    logger.info("Detected Render environment - using /tmp for cache")
else:
    # Local environment - use project data directory
    CACHE_DIR = Path(__file__).parent.parent.parent / 'data' / 'cache' / 'dataexplorer'
    logger.info("Detected local environment - using project data directory for cache")

try:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    is_writable = os.access(CACHE_DIR, os.W_OK)
    logger.info(f"Cache directory: {CACHE_DIR} (writable: {is_writable})")
    if not is_writable:
        logger.error(f"[CRITICAL] Cache directory {CACHE_DIR} is not writable!")
        # Fallback to /tmp if project directory fails
        CACHE_DIR = Path('/tmp') / 'dataexplorer_cache'
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using fallback cache directory: {CACHE_DIR}")
except Exception as e:
    logger.error(f"[CRITICAL] Cannot create cache directory {CACHE_DIR}: {e}")
    # Fallback to /tmp if project directory fails
    CACHE_DIR = Path('/tmp') / 'dataexplorer_cache'
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using fallback cache directory: {CACHE_DIR}")
    except Exception as e2:
        logger.error(f"[CRITICAL] Cannot create fallback cache directory {CACHE_DIR}: {e2}")
        raise

# Cache TTL (time to live) in days
CACHE_TTL_DAYS = 7


def _get_cache_key(geoids: List[str], years: List[int], filters: Dict[str, Any] = None) -> str:
    """
    Generate a cache key from query parameters.
    
    Args:
        geoids: List of GEOIDs
        years: List of years
        filters: Optional filters dictionary
        
    Returns:
        MD5 hash string for cache key
    """
    # Create a unique string from parameters
    params_str = json.dumps({
        'geoids': sorted(geoids),
        'years': sorted(years),
        'filters': filters or {}
    }, sort_keys=True)
    
    # Generate MD5 hash
    return hashlib.md5(params_str.encode()).hexdigest()


def _get_cache_file_path(cache_key: str, data_type: str) -> Path:
    """
    Get cache file path for a given cache key and data type.
    
    Args:
        cache_key: Cache key (MD5 hash)
        data_type: Type of data ('hmda', 'census', 'hud', 'historical_census')
        
    Returns:
        Path to cache file
    """
    return CACHE_DIR / f"{cache_key}_{data_type}.pkl"


def _is_cache_valid(cache_file: Path) -> bool:
    """
    Check if cache file is still valid (not expired).
    
    Args:
        cache_file: Path to cache file
        
    Returns:
        True if cache is valid, False otherwise
    """
    if not cache_file.exists():
        return False
    
    # Check file modification time
    file_age = datetime.now().timestamp() - cache_file.stat().st_mtime
    age_days = file_age / (24 * 60 * 60)
    
    return age_days < CACHE_TTL_DAYS


def save_hmda_data(geoids: List[str], years: List[int], filters: Dict[str, Any], 
                   data: pd.DataFrame) -> bool:
    """
    Save HMDA query results to cache.
    
    Args:
        geoids: List of GEOIDs
        years: List of years
        filters: Filters dictionary
        data: DataFrame with HMDA data
        
    Returns:
        True if saved successfully
    """
    try:
        cache_key = _get_cache_key(geoids, years, filters)
        cache_file = _get_cache_file_path(cache_key, 'hmda')
        
        # Save DataFrame as pickle
        data.to_pickle(cache_file)
        
        # Save metadata
        metadata_file = cache_file.with_suffix('.json')
        metadata = {
            'geoids': geoids,
            'years': years,
            'filters': filters,
            'cached_at': datetime.now().isoformat(),
            'row_count': len(data),
            'columns': list(data.columns)
        }
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Cached HMDA data: {len(data)} rows, cache key: {cache_key[:8]}...")
        return True
    except Exception as e:
        logger.error(f"Error saving HMDA cache: {e}")
        return False


def load_hmda_data(geoids: List[str], years: List[int], filters: Dict[str, Any] = None) -> Optional[pd.DataFrame]:
    """
    Load HMDA query results from cache.
    
    Args:
        geoids: List of GEOIDs
        years: List of years
        filters: Optional filters dictionary
        
    Returns:
        DataFrame if found in cache, None otherwise
    """
    try:
        cache_key = _get_cache_key(geoids, years, filters)
        cache_file = _get_cache_file_path(cache_key, 'hmda')
        
        if not _is_cache_valid(cache_file):
            logger.debug(f"Cache expired or not found for key: {cache_key[:8]}...")
            return None
        
        # Load DataFrame from pickle
        data = pd.read_pickle(cache_file)
        logger.info(f"Loaded HMDA data from cache: {len(data)} rows, cache key: {cache_key[:8]}...")
        return data
    except Exception as e:
        logger.warning(f"Error loading HMDA cache: {e}")
        return None


def save_census_data(geoids: List[str], census_data: Dict[str, Any]) -> bool:
    """
    Save census demographics data to cache.
    
    Args:
        geoids: List of GEOIDs
        census_data: Census data dictionary
        
    Returns:
        True if saved successfully
    """
    try:
        cache_key = _get_cache_key(geoids, [], None)  # Census doesn't depend on years/filters
        cache_file = _get_cache_file_path(cache_key, 'census')
        
        with open(cache_file, 'wb') as f:
            pickle.dump(census_data, f)
        
        logger.info(f"Cached census data for {len(geoids)} counties, cache key: {cache_key[:8]}...")
        return True
    except Exception as e:
        logger.error(f"Error saving census cache: {e}")
        return False


def load_census_data(geoids: List[str]) -> Optional[Dict[str, Any]]:
    """
    Load census demographics data from cache.
    
    Args:
        geoids: List of GEOIDs
        
    Returns:
        Census data dictionary if found, None otherwise
    """
    try:
        cache_key = _get_cache_key(geoids, [], None)
        cache_file = _get_cache_file_path(cache_key, 'census')
        
        if not _is_cache_valid(cache_file):
            return None
        
        with open(cache_file, 'rb') as f:
            data = pickle.load(f)
        
        logger.info(f"Loaded census data from cache for {len(geoids)} counties")
        return data
    except Exception as e:
        logger.warning(f"Error loading census cache: {e}")
        return None


def save_historical_census_data(geoids: List[str], historical_data: Dict[str, Any]) -> bool:
    """
    Save historical census data to cache.
    
    Args:
        geoids: List of GEOIDs
        historical_data: Historical census data dictionary
        
    Returns:
        True if saved successfully
    """
    try:
        cache_key = _get_cache_key(geoids, [], None)
        cache_file = _get_cache_file_path(cache_key, 'historical_census')
        
        with open(cache_file, 'wb') as f:
            pickle.dump(historical_data, f)
        
        logger.info(f"Cached historical census data for {len(geoids)} counties")
        return True
    except Exception as e:
        logger.error(f"Error saving historical census cache: {e}")
        return False


def load_historical_census_data(geoids: List[str]) -> Optional[Dict[str, Any]]:
    """
    Load historical census data from cache.
    
    Args:
        geoids: List of GEOIDs
        
    Returns:
        Historical census data dictionary if found, None otherwise
    """
    try:
        cache_key = _get_cache_key(geoids, [], None)
        cache_file = _get_cache_file_path(cache_key, 'historical_census')
        
        if not _is_cache_valid(cache_file):
            return None
        
        with open(cache_file, 'rb') as f:
            data = pickle.load(f)
        
        # Debug: Log structure of cached data
        if data:
            logger.info(f"[DEBUG] Loaded historical census data from cache with {len(data)} counties")
            if len(data) > 0:
                first_geoid = list(data.keys())[0]
                first_county = data[first_geoid]
                logger.info(f"[DEBUG] Cached county ({first_geoid}) type: {type(first_county)}")
                logger.info(f"[DEBUG] Cached county ({first_geoid}) keys: {list(first_county.keys()) if isinstance(first_county, dict) else 'Not a dict'}")
                if isinstance(first_county, dict) and 'time_periods' in first_county:
                    logger.info(f"[DEBUG] Cached time_periods keys: {list(first_county['time_periods'].keys())}")
                else:
                    logger.warning(f"[DEBUG] Cached data missing time_periods! County data: {first_county}")
        else:
            logger.warning(f"[DEBUG] Cached historical census data is empty!")
        
        logger.info(f"Loaded historical census data from cache")
        return data
    except Exception as e:
        logger.warning(f"Error loading historical census cache: {e}")
        return None


def save_hud_data(geoids: List[str], hud_data: Dict[str, Any]) -> bool:
    """
    Save HUD income data to cache.
    
    Args:
        geoids: List of GEOIDs
        hud_data: HUD data dictionary
        
    Returns:
        True if saved successfully
    """
    try:
        cache_key = _get_cache_key(geoids, [], None)
        cache_file = _get_cache_file_path(cache_key, 'hud')
        
        with open(cache_file, 'wb') as f:
            pickle.dump(hud_data, f)
        
        logger.info(f"Cached HUD data for {len(geoids)} counties")
        return True
    except Exception as e:
        logger.error(f"Error saving HUD cache: {e}")
        return False


def clear_cache(data_type: Optional[str] = None) -> int:
    """
    Clear cache files.
    
    Args:
        data_type: Optional specific data type to clear ('hmda', 'census', 'hud', 'historical_census').
                   If None, clears all cache files.
    
    Returns:
        Number of files deleted
    """
    deleted_count = 0
    
    if data_type:
        # Clear specific data type
        pattern = f"*_{data_type}.pkl"
        cache_files = list(CACHE_DIR.glob(pattern))
        for cache_file in cache_files:
            try:
                cache_file.unlink()
                deleted_count += 1
                logger.info(f"Deleted cache file: {cache_file.name}")
            except Exception as e:
                logger.warning(f"Error deleting cache file {cache_file.name}: {e}")
    else:
        # Clear all cache files
        cache_files = list(CACHE_DIR.glob("*.pkl"))
        for cache_file in cache_files:
            try:
                cache_file.unlink()
                deleted_count += 1
                logger.info(f"Deleted cache file: {cache_file.name}")
            except Exception as e:
                logger.warning(f"Error deleting cache file {cache_file.name}: {e}")
    
    logger.info(f"Cleared {deleted_count} cache file(s)")
    return deleted_count


def load_hud_data(geoids: List[str]) -> Optional[Dict[str, Any]]:
    """
    Load HUD income data from cache.
    
    Args:
        geoids: List of GEOIDs
        
    Returns:
        HUD data dictionary if found, None otherwise
    """
    try:
        cache_key = _get_cache_key(geoids, [], None)
        cache_file = _get_cache_file_path(cache_key, 'hud')
        
        if not _is_cache_valid(cache_file):
            return None
        
        with open(cache_file, 'rb') as f:
            data = pickle.load(f)
        
        logger.info(f"Loaded HUD data from cache")
        return data
    except Exception as e:
        logger.warning(f"Error loading HUD cache: {e}")
        return None


def clear_cache(data_type: Optional[str] = None):
    """
    Clear cache files.
    
    Args:
        data_type: Optional data type to clear ('hmda', 'census', 'hud', 'historical_census')
                   If None, clears all cache files
    """
    try:
        if data_type:
            pattern = f"*_{data_type}.pkl"
        else:
            pattern = "*.pkl"
        
        cache_files = list(CACHE_DIR.glob(pattern))
        for cache_file in cache_files:
            cache_file.unlink()
            # Also delete metadata file if it exists
            metadata_file = cache_file.with_suffix('.json')
            if metadata_file.exists():
                metadata_file.unlink()
        
        logger.info(f"Cleared {len(cache_files)} cache files")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")

