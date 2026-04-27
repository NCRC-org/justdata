"""Regulations.gov data fetcher."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def _get_regulations_data(collector, name: str) -> Dict[str, Any]:
    """Get Regulations.gov comment letters."""
    result = collector.regulations_client.search_comments(
        organization_name=name,
        search_term=name,
        limit=20
    )
    
    comments = result.get('data', [])
    meta = result.get('meta', {})
    
    return {
        'comment_letters': comments,
        'total_comments': meta.get('totalElements', len(comments)),
        'meta': meta
    }

