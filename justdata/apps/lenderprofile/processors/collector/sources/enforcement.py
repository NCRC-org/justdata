"""Enforcement data fetcher."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def _get_enforcement_data(collector, name: str) -> Dict[str, Any]:
    """Get CFPB enforcement data."""
    actions = collector.cfpb_client.search_enforcement_actions(name)
    
    return {
        'actions': actions,
        'total_actions': len(actions),
        'recent_actions': [a for a in actions if collector._is_recent(a.get('date', ''))]
    }

