"""Business strategy section."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from justdata.apps.lenderprofile.report_builder.helpers import (
    _extract_business_segments,
    _extract_contraction_areas,
    _extract_growth_areas,
    _extract_strategic_priorities,
)

def build_business_strategy(
    institution_data: Dict[str, Any],
    sec_parsed: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build business strategy section from SEC 10-K Item 1 and Item 7.

    Extracts:
    - Business description and segments
    - Strategic priorities
    - Growth areas and expansion plans
    - Contraction or exit areas
    """
    sec_data = institution_data.get('sec', {})

    # Get parsed SEC data
    if not sec_parsed:
        sec_parsed = sec_data.get('parsed', {})

    sections = sec_parsed.get('sections', {}) if sec_parsed else {}

    # Item 1: Business Description
    item1 = sections.get('item1_business', '')

    # Item 7: Management's Discussion & Analysis
    item7 = sections.get('item7_mda', '')

    # Extract key themes (code-based extraction)
    business_segments = _extract_business_segments(item1)
    strategic_priorities = _extract_strategic_priorities(item7)
    growth_areas = _extract_growth_areas(item7)
    contraction_areas = _extract_contraction_areas(item7)

    return {
        'business_description': _truncate_text(item1, 2000),
        'business_segments': business_segments,
        'strategic_priorities': strategic_priorities,
        'growth_areas': growth_areas,
        'contraction_areas': contraction_areas,
        'mda_highlights': _truncate_text(item7, 2000),
        'has_data': bool(item1 or item7)
    }


