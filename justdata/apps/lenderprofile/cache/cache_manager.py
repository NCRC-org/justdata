#!/usr/bin/env python3
"""
Cache Manager for LenderProfile
Provides Redis caching with in-memory fallback.
"""

import os
import logging
import json
import hashlib
from typing import Optional, Any, Dict
from datetime import datetime, timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available, using in-memory cache only")

from justdata.apps.lenderprofile.config import (
    CACHE_TTL_GLEIF, CACHE_TTL_FINANCIAL, CACHE_TTL_BRANCH,
    CACHE_TTL_CRA, CACHE_TTL_COURT_SEARCH, CACHE_TTL_COURT_DETAILS,
    CACHE_TTL_NEWS, CACHE_TTL_ORG_CHART, CACHE_TTL_SEC, CACHE_TTL_ENFORCEMENT
)

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Cache manager with Redis primary and in-memory fallback.
    """
    
    def __init__(self):
        """Initialize cache manager."""
        self.redis_client = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        
        # Try to connect to Redis
        if REDIS_AVAILABLE:
            try:
                redis_host = os.getenv('REDIS_HOST', 'localhost')
                redis_port = int(os.getenv('REDIS_PORT', 6379))
                redis_db = int(os.getenv('REDIS_DB', 0))
                
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache connected")
            except Exception as e:
                logger.warning(f"Redis not available, using in-memory cache: {e}")
                self.redis_client = None
    
    def _make_key(self, prefix: str, *args) -> str:
        """Generate cache key."""
        key_str = ':'.join(str(arg) for arg in args)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        return f"lenderintel:{prefix}:{key_hash}"
    
    def get(self, prefix: str, *args) -> Optional[Any]:
        """
        Get cached value.
        
        Args:
            prefix: Cache prefix (e.g., 'fdic', 'gleif')
            *args: Key components
            
        Returns:
            Cached value or None
        """
        key = self._make_key(prefix, *args)
        
        # Try Redis first
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        
        # Fallback to memory
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            # Check expiration
            if datetime.now() < entry['expires']:
                return entry['value']
            else:
                del self.memory_cache[key]
        
        return None
    
    def set(self, prefix: str, value: Any, ttl: int, *args) -> bool:
        """
        Set cached value.
        
        Args:
            prefix: Cache prefix
            value: Value to cache
            ttl: Time to live in seconds
            *args: Key components
            
        Returns:
            True if successful
        """
        key = self._make_key(prefix, *args)
        
        # Try Redis first
        if self.redis_client:
            try:
                self.redis_client.setex(key, ttl, json.dumps(value))
                return True
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
        
        # Fallback to memory
        expires = datetime.now() + timedelta(seconds=ttl)
        self.memory_cache[key] = {
            'value': value,
            'expires': expires
        }
        
        # Clean up expired entries periodically
        if len(self.memory_cache) > 1000:
            self._cleanup_memory_cache()
        
        return True
    
    def _cleanup_memory_cache(self):
        """Remove expired entries from memory cache."""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self.memory_cache.items()
            if entry['expires'] < now
        ]
        for key in expired_keys:
            del self.memory_cache[key]
    
    def get_ttl(self, cache_type: str) -> int:
        """
        Get TTL for a cache type.
        
        Args:
            cache_type: Type of cache ('gleif', 'financial', 'branch', etc.)
            
        Returns:
            TTL in seconds
        """
        ttl_map = {
            'gleif': CACHE_TTL_GLEIF,
            'financial': CACHE_TTL_FINANCIAL,
            'branch': CACHE_TTL_BRANCH,
            'cra': CACHE_TTL_CRA,
            'court_search': CACHE_TTL_COURT_SEARCH,
            'court_details': CACHE_TTL_COURT_DETAILS,
            'news': CACHE_TTL_NEWS,
            'org_chart': CACHE_TTL_ORG_CHART,
            'sec': CACHE_TTL_SEC,
            'enforcement': CACHE_TTL_ENFORCEMENT
        }
        return ttl_map.get(cache_type, 3600)  # Default 1 hour

