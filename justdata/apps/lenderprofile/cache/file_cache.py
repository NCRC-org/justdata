#!/usr/bin/env python3
"""
File-based Persistent Cache for LenderProfile Development
Saves all API responses to JSON files for offline iteration and debugging.

Usage:
    from justdata.apps.lenderprofile.cache.file_cache import FileCache

    cache = FileCache("fifth_third")

    # Save data
    cache.save("fdic", fdic_data)
    cache.save("cfpb", cfpb_data)

    # Load data (returns None if not cached)
    fdic_data = cache.load("fdic")

    # Check if all data is cached
    if cache.is_complete():
        data = cache.load_all()
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class FileCache:
    """
    Persistent file-based cache for development.
    Saves each data source to a separate JSON file for easy inspection/editing.
    """

    # Standard data sources collected by DataCollector
    STANDARD_SOURCES = [
        'identifiers',
        'fdic_financials',
        'cfpb_metadata',
        'gleif',
        'sec',
        'seeking_alpha',
        'litigation',
        'news',
        'enforcement',
        'cfpb_complaints',
        'federal_register',
        'federal_reserve',
        'regulations',
        'hmda_footprint',
        'hierarchy',
        'corporate_structure',
        'complaints_processed',
        'analyst_ratings',
        'litigation_processed',
        'news_processed',
        'sec_parsed',
        'mergers',
        'branch_network',
    ]

    def __init__(self, institution_name: str, cache_dir: str = None):
        """
        Initialize file cache for an institution.

        Args:
            institution_name: Name of institution (used as folder name)
            cache_dir: Optional custom cache directory
        """
        self.institution_name = institution_name
        # Sanitize name for filesystem
        safe_name = self._sanitize_name(institution_name)

        if cache_dir:
            self.cache_dir = Path(cache_dir) / safe_name
        else:
            # Default to apps/lenderprofile/cache/data/<institution>
            self.cache_dir = Path(__file__).parent / "data" / safe_name

        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Metadata file
        self.meta_file = self.cache_dir / "_metadata.json"

        logger.info(f"FileCache initialized at: {self.cache_dir}")

    def _sanitize_name(self, name: str) -> str:
        """Sanitize institution name for use as directory name."""
        # Replace spaces and special chars with underscores
        safe = name.lower().replace(' ', '_')
        safe = ''.join(c if c.isalnum() or c == '_' else '_' for c in safe)
        # Remove consecutive underscores
        while '__' in safe:
            safe = safe.replace('__', '_')
        return safe.strip('_')

    def _get_file_path(self, source: str) -> Path:
        """Get file path for a data source."""
        return self.cache_dir / f"{source}.json"

    def save(self, source: str, data: Any) -> bool:
        """
        Save data for a source to a JSON file.

        Args:
            source: Data source name (e.g., 'fdic', 'cfpb_complaints')
            data: Data to save (must be JSON serializable)

        Returns:
            True if successful
        """
        try:
            file_path = self._get_file_path(source)

            # Convert to JSON-serializable format
            json_data = self._make_serializable(data)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, default=str)

            # Update metadata
            self._update_metadata(source)

            logger.info(f"Cached {source} to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving {source} to cache: {e}")
            return False

    def load(self, source: str) -> Optional[Any]:
        """
        Load data for a source from cache.

        Args:
            source: Data source name

        Returns:
            Cached data or None if not found
        """
        file_path = self._get_file_path(source)

        if not file_path.exists():
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded {source} from cache")
            return data
        except Exception as e:
            logger.error(f"Error loading {source} from cache: {e}")
            return None

    def save_all(self, data: Dict[str, Any]) -> int:
        """
        Save all data sources from a dictionary.

        Args:
            data: Dictionary with source names as keys

        Returns:
            Number of sources saved
        """
        saved = 0
        for source, source_data in data.items():
            if source_data is not None:
                if self.save(source, source_data):
                    saved += 1
        return saved

    def load_all(self) -> Dict[str, Any]:
        """
        Load all cached data sources.

        Returns:
            Dictionary with all cached data
        """
        data = {}
        for source in self.STANDARD_SOURCES:
            cached = self.load(source)
            if cached is not None:
                data[source] = cached

        # Also load any non-standard sources that exist
        for file_path in self.cache_dir.glob("*.json"):
            source = file_path.stem
            if source not in data and not source.startswith('_'):
                cached = self.load(source)
                if cached is not None:
                    data[source] = cached

        return data

    def exists(self, source: str) -> bool:
        """Check if a source is cached."""
        return self._get_file_path(source).exists()

    def get_cached_sources(self) -> List[str]:
        """Get list of all cached source names."""
        sources = []
        for file_path in self.cache_dir.glob("*.json"):
            if not file_path.name.startswith('_'):
                sources.append(file_path.stem)
        return sorted(sources)

    def is_complete(self, required_sources: List[str] = None) -> bool:
        """
        Check if all required sources are cached.

        Args:
            required_sources: List of required sources (defaults to core sources)

        Returns:
            True if all required sources are cached
        """
        if required_sources is None:
            # Core sources that should exist for a complete profile
            required_sources = [
                'identifiers', 'cfpb_complaints', 'gleif'
            ]

        for source in required_sources:
            if not self.exists(source):
                return False
        return True

    def clear(self) -> int:
        """
        Clear all cached data for this institution.

        Returns:
            Number of files deleted
        """
        deleted = 0
        for file_path in self.cache_dir.glob("*.json"):
            try:
                file_path.unlink()
                deleted += 1
            except Exception as e:
                logger.error(f"Error deleting {file_path}: {e}")
        return deleted

    def get_metadata(self) -> Dict[str, Any]:
        """Get cache metadata."""
        if self.meta_file.exists():
            with open(self.meta_file, 'r') as f:
                return json.load(f)
        return {}

    def _update_metadata(self, source: str):
        """Update metadata when a source is saved."""
        meta = self.get_metadata()
        meta['institution'] = self.institution_name
        meta['cache_dir'] = str(self.cache_dir)
        meta['last_updated'] = datetime.now().isoformat()

        if 'sources' not in meta:
            meta['sources'] = {}
        meta['sources'][source] = {
            'cached_at': datetime.now().isoformat(),
            'file': f"{source}.json"
        }

        with open(self.meta_file, 'w') as f:
            json.dump(meta, f, indent=2)

    def _make_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format."""
        import numpy as np
        import pandas as pd

        if obj is None:
            return None
        elif isinstance(obj, (str, int, float, bool)):
            return obj
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient='records')
        elif isinstance(obj, pd.Series):
            return obj.to_dict()
        elif isinstance(obj, dict):
            return {str(k): self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return self._make_serializable(obj.__dict__)
        else:
            return str(obj)

    def __repr__(self):
        sources = self.get_cached_sources()
        return f"FileCache('{self.institution_name}', sources={len(sources)}, dir='{self.cache_dir}')"


class CachingDataCollector:
    """
    Wrapper around DataCollector that adds file-based caching.
    """

    def __init__(self, institution_name: str, use_cache: bool = True, cache_dir: str = None):
        """
        Initialize caching data collector.

        Args:
            institution_name: Name of institution
            use_cache: Whether to use cached data if available
            cache_dir: Optional custom cache directory
        """
        from justdata.apps.lenderprofile.processors.data_collector import DataCollector

        self.institution_name = institution_name
        self.use_cache = use_cache
        self.cache = FileCache(institution_name, cache_dir)
        self.collector = DataCollector()

    def collect_with_cache(self, identifiers: Dict[str, Any], force_refresh: bool = False) -> Dict[str, Any]:
        """
        Collect data with caching.

        Args:
            identifiers: Resolved identifiers
            force_refresh: If True, ignore cache and fetch fresh data

        Returns:
            Complete institution data
        """
        # Check if we have complete cached data
        if self.use_cache and not force_refresh and self.cache.is_complete():
            logger.info(f"Loading complete profile from cache for {self.institution_name}")
            cached_data = self.cache.load_all()
            # Add institution wrapper
            cached_data['institution'] = {
                'name': self.institution_name,
                'identifiers': identifiers
            }
            return cached_data

        # Collect fresh data
        logger.info(f"Collecting fresh data for {self.institution_name}")
        data = self.collector.collect_all_data(identifiers, self.institution_name)

        # Save to cache
        saved = self.cache.save_all(data)
        logger.info(f"Saved {saved} data sources to cache")

        return data

    def get_cache(self) -> FileCache:
        """Get the file cache instance."""
        return self.cache


# Convenience function
def get_cached_data(institution_name: str) -> Optional[Dict[str, Any]]:
    """
    Quick function to load cached data for an institution.

    Args:
        institution_name: Name of institution

    Returns:
        Cached data or None
    """
    cache = FileCache(institution_name)
    if cache.is_complete():
        return cache.load_all()
    return None
