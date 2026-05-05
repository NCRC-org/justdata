"""Regulatory risk section."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from justdata.apps.lenderprofile.report_builder.helpers import (
    _format_currency,
    _is_recent,
)

def build_regulatory_risk(institution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build regulatory risk section.

    Includes:
    - Enforcement actions
    - Consumer complaints summary
    - CRA rating and history
    """
    enforcement = institution_data.get('enforcement', {})
    cfpb_complaints = institution_data.get('cfpb_complaints', {})
    cra_data = institution_data.get('cra', {})

    # Enforcement actions
    actions = enforcement.get('actions', [])
    recent_actions = [a for a in actions if _is_recent(a.get('date'), years=3)]

    # Complaints
    complaint_total = cfpb_complaints.get('total', 0)
    complaint_trends = cfpb_complaints.get('trends', {})
    main_issues = cfpb_complaints.get('main_topics', [])[:5]
    main_products = cfpb_complaints.get('main_products', [])[:5]  # Top 5 product categories
    cfpb_company_name = cfpb_complaints.get('cfpb_company_name', '')

    # CRA
    cra_rating = cra_data.get('current_rating', '--')
    cra_exam_date = cra_data.get('exam_date')
    cra_history = cra_data.get('rating_history', [])

    return {
        'enforcement': {
            'total_actions': len(actions),
            'recent_actions': recent_actions,
            'recent_count': len(recent_actions)
        },
        'complaints': {
            'total': complaint_total,
            'trend': complaint_trends.get('recent_trend', 'stable'),
            'main_issues': main_issues,
            'main_categories': main_products,  # Top 5 product categories
            'by_year': complaint_trends.get('by_year', {}),
            'cfpb_company_name': cfpb_company_name,
            'latest_complaint_date': cfpb_complaints.get('latest_complaint_date'),
            # Multi-year data for trend charts
            'national_by_year': cfpb_complaints.get('national_by_year', {}),
            'categories_by_year': cfpb_complaints.get('categories_by_year', {})
        },
        'cra': {
            'current_rating': cra_rating,
            'exam_date': cra_exam_date,
            'history': cra_history[:5]
        },
        'has_data': bool(actions or complaint_total > 0 or cra_rating != '--')
    }


