"""Community investment / CRA section."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from justdata.apps.lenderprofile.report_builder.helpers import _format_currency

def build_community_investment(
    institution_data: Dict[str, Any],
    sec_parsed: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build community investment section from SEC 10-K data and XBRL API.

    Includes:
    - CRA rating and performance
    - Community development loans and investments
    - Affordable housing tax credits (from XBRL)
    - Charitable contributions and philanthropy
    - Community commitments (affordable housing, minority lending, etc.)

    Args:
        institution_data: Complete institution data
        sec_parsed: Parsed SEC 10-K data (may include merged XBRL data)

    Returns:
        Dictionary with community investment metrics
    """
    # Get community investment data from SEC parsing
    if not sec_parsed:
        sec_parsed = institution_data.get('sec_parsed', {})

    community_data = sec_parsed.get('community_investment', {}) if sec_parsed else {}

    # Also get CRA data from dedicated CRA source (may be more current)
    cra_data = institution_data.get('cra', {})

    # Use SEC-extracted CRA rating if available, else use CRA data source
    cra_rating = community_data.get('cra_rating') or cra_data.get('current_rating')
    cra_exam_date = cra_data.get('exam_date')

    # Community Development metrics (from text parsing)
    cd_data = community_data.get('community_development', {})
    cd_loans = cd_data.get('loans')
    cd_investments = cd_data.get('investments')
    cd_services = cd_data.get('services')

    # XBRL-sourced affordable housing data (more reliable when available)
    affordable_housing_tax_credits = community_data.get('affordable_housing_tax_credits')
    affordable_housing_amortization = community_data.get('affordable_housing_amortization')
    investment_tax_credit = community_data.get('investment_tax_credit')

    # Philanthropy
    charitable = community_data.get('charitable_contributions')
    foundation = community_data.get('foundation')

    # Commitments (affordable housing, minority lending, etc.)
    commitments = community_data.get('commitments', [])

    # Format amounts for display
    def format_amount(amount):
        if amount is None:
            return None
        if amount >= 1_000_000_000:
            return f"${amount / 1_000_000_000:.1f}B"
        elif amount >= 1_000_000:
            return f"${amount / 1_000_000:.0f}M"
        elif amount >= 1_000:
            return f"${amount / 1_000:.0f}K"
        else:
            return f"${amount:,.0f}"

    formatted_commitments = []
    for c in commitments:
        formatted_commitments.append({
            'amount': format_amount(c.get('amount')),
            'purpose': c.get('purpose', '').title()
        })

    has_data = bool(
        cra_rating or
        cd_loans or cd_investments or
        affordable_housing_tax_credits or
        charitable or foundation or
        commitments
    )

    return {
        'cra': {
            'rating': cra_rating,
            'exam_date': cra_exam_date
        },
        'community_development': {
            'loans': format_amount(cd_loans),
            'loans_raw': cd_loans,
            'investments': format_amount(cd_investments),
            'investments_raw': cd_investments,
            'services': cd_services
        },
        'affordable_housing': {
            'tax_credits': format_amount(affordable_housing_tax_credits),
            'tax_credits_raw': affordable_housing_tax_credits,
            'amortization': format_amount(affordable_housing_amortization),
            'amortization_raw': affordable_housing_amortization,
            'investment_tax_credit': format_amount(investment_tax_credit),
            'investment_tax_credit_raw': investment_tax_credit,
        },
        'philanthropy': {
            'charitable_contributions': format_amount(charitable),
            'charitable_raw': charitable,
            'foundation': {
                'name': foundation.get('name') if foundation else None,
                'assets': format_amount(foundation.get('amount')) if foundation else None
            } if foundation else None
        },
        'commitments': formatted_commitments,
        'has_data': has_data,
        'has_xbrl_data': sec_parsed.get('has_xbrl_data', False) if sec_parsed else False
    }


