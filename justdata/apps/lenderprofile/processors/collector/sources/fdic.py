"""FDIC data fetchers (institution + financials)."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def _get_fdic_institution(collector, cert: str) -> Dict[str, Any]:
    """Get FDIC institution details - REMOVED: Use CFPB/GLEIF instead."""
    return {}

def _get_fdic_financials(collector, cert: str) -> Dict[str, Any]:
    """
    Get FDIC Call Report data (Financial API).
    
    This is the ONLY FDIC API we use - for Call Report financial data.
    Branch data comes from BigQuery SOD tables, not FDIC Location API.
    Institution data comes from CFPB/GLEIF, not FDIC Institution API.
    
    Documentation: https://api.fdic.gov/banks/docs/
    """
    cache_key = f'fdic_financials_{cert}'
    cached = collector.cache.get('financial', cache_key)
    if cached:
        return cached
    
    try:
        # Use FDIC Financial API for Call Report data
        data = collector.fdic_client.get_financials(cert, fields=['ASSET', 'REPDTE', 'ROA', 'ROE', 'EQUITY', 'DEP', 'NETINC', 'LNLSNET', 'RBCT1J', 'NPAASSET', 'EEFFR'])
        result = {'data': data}
        if data:
            collector.cache.set('financial', result, collector.cache.get_ttl('financial'), cache_key)
        return result
    except Exception as e:
        logger.error(f"Error getting FDIC Call Report data for {cert}: {e}")
        return {'data': []}

# Note: Removed _get_fdic_branches - we use BigQuery SOD tables instead
# Note: Removed _get_fdic_institution - we use CFPB/GLEIF for institution data

