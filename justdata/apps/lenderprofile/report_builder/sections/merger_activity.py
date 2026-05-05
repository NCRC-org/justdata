"""Merger and acquisition activity section."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from justdata.apps.lenderprofile.report_builder.helpers import (
    _format_currency,
    _is_recent,
)

def build_merger_activity(institution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build M&A activity section.

    Includes:
    - Pending acquisitions (from 8-K filings or news)
    - Historical acquisitions (from SEC 10-K)
    - Expected branch changes
    """
    merger_data = institution_data.get('mergers', {})
    sec_data = institution_data.get('sec', {})
    sec_parsed = institution_data.get('sec_parsed', {})

    # Historical acquisitions from SEC 10-K
    historical = sec_parsed.get('business_combinations', []) if sec_parsed else []

    # Pending from merger data (8-K filings, news, etc.)
    pending = merger_data.get('pending', [])

    # Format pending acquisitions for display
    formatted_pending = []
    for item in pending:
        formatted_pending.append({
            'date': item.get('date', ''),
            'target': item.get('target', item.get('description', '')),
            'description': item.get('description', ''),
            'url': item.get('url', '')
        })

    return {
        'pending_acquisitions': formatted_pending,
        'historical_acquisitions': historical,
        'total_pending': len(formatted_pending),
        'total_historical': len(historical),
        'expected_branch_changes': merger_data.get('expected_closures', []),
        'has_pending': len(formatted_pending) > 0,
        'has_data': bool(formatted_pending or historical)
    }


