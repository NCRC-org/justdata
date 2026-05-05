"""Risk factors section."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from justdata.apps.lenderprofile.report_builder.helpers import (
    _categorize_risks,
    _truncate_text,
)

def build_risk_factors(
    institution_data: Dict[str, Any],
    sec_parsed: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build risk factors section from SEC 10-K Item 1A.
    """
    sec_data = institution_data.get('sec', {})

    if not sec_parsed:
        sec_parsed = sec_data.get('parsed', {})

    sections = sec_parsed.get('sections', {}) if sec_parsed else {}
    item1a = sections.get('item1a_risks', '')

    # Extract categorized risks
    risk_categories = _categorize_risks(item1a)

    return {
        'risk_text': _truncate_text(item1a, 3000),
        'risk_categories': risk_categories,
        'has_data': bool(item1a)
    }


