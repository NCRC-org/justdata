"""Federal Register data fetcher."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def _get_federal_register_data(collector, name: str) -> Dict[str, Any]:
    """Get Federal Register merger notices."""
    documents = collector.federal_register_client.search_merger_notices(name)
    
    return {
        'merger_notices': documents,
        'pending_mergers': [d for d in documents if 'pending' in d.get('status', '').lower()]
    }

