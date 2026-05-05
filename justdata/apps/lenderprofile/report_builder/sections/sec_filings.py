"""SEC filings analysis section."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from justdata.apps.lenderprofile.report_builder.helpers import _is_recent
from justdata.apps.lenderprofile.report_builder.sections.ai_intelligence_data import (
    _collect_comprehensive_data,
    _generate_comprehensive_key_findings,
)

def build_sec_filings_analysis(
    institution_data: Dict[str, Any],
    cik: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build SEC Filing Overview with 8-10 AI-generated key findings.

    Analyzes data from:
    - SEC 10-K and 10-Q filings (NCRC-relevant topics)
    - HMDA mortgage lending data
    - Branch network data
    - Small business lending data
    - Recent news
    - Executive leadership

    Returns 8-10 bulleted key findings covering all data sources.
    """
    # Get company info
    institution = institution_data.get('institution', {})
    company_name = institution.get('name', 'The company')

    # Collect data from all sources for AI analysis
    data_summary = _collect_comprehensive_data(institution_data)

    if not data_summary.get('has_any_data'):
        return {
            'has_data': False,
            'message': 'No data available for SEC filing overview'
        }

    # Generate 8-10 key findings using AI
    key_findings = _generate_comprehensive_key_findings(company_name, data_summary)

    return {
        'has_data': True,
        'key_findings': key_findings,
        'data_sources': data_summary.get('sources_used', []),
        'filings_analyzed': data_summary.get('sec_filings', [])
    }


