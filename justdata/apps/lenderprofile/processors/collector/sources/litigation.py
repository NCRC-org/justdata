"""Litigation (CourtListener) data fetcher."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def _get_litigation_data(collector, name: str) -> Dict[str, Any]:
    """Get CourtListener litigation data."""
    cache_key = f'litigation_{name}'
    cached = collector.cache.get('court_search', cache_key)
    if cached:
        return cached
    
    # Search for institution as party
    dockets = collector.courtlistener_client.search_dockets(
        f'party_name:"{name}"',
        filed_after='2015-01-01',
        limit=20
    )
    
    result = {
        'cases': dockets,
        'total_cases': len(dockets)
    }
    
    if dockets:
        collector.cache.set('court_search', result, collector.cache.get_ttl('court_search'), cache_key)
    
    return result

