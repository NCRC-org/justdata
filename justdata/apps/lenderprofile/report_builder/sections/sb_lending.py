"""Small business lending section."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from justdata.apps.lenderprofile.report_builder.helpers import _format_currency

def build_sb_lending(
    institution_data: Dict[str, Any],
    sb_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build small business lending section from CRA data.

    Shows lender's SB lending volume by year compared to national totals,
    plus geographic breakdown by state.

    Args:
        institution_data: Complete institution data
        sb_data: CRA small business lending data from BigQueryCRAClient

    Returns:
        Dictionary with yearly lending, national comparison, and top states
    """
    if not sb_data or not sb_data.get('has_data'):
        return {
            'has_data': False,
            'error': sb_data.get('error') if sb_data else 'No CRA data available'
        }

    yearly = sb_data.get('yearly_lending', {})
    national = sb_data.get('national_lending', {})
    top_states = sb_data.get('top_states', {})
    market_share = sb_data.get('market_share', [])

    # Format for chart display
    years = yearly.get('years', [])
    lender_counts = yearly.get('loan_counts', [])
    lender_amounts = yearly.get('loan_amounts', [])  # In thousands

    national_counts = national.get('loan_counts', [])
    national_amounts = national.get('loan_amounts', [])

    # Calculate totals
    total_loans = sum(lender_counts) if lender_counts else 0
    total_amount = sum(lender_amounts) if lender_amounts else 0  # In thousands

    # Format top states for bubble chart
    states = top_states.get('states', [])
    state_counts = top_states.get('loan_counts', [])
    state_percentages = top_states.get('percentages', [])

    # Build by_state dict for chart compatibility
    by_state = {}
    for i, state in enumerate(states):
        by_state[state] = {
            'count': state_counts[i] if i < len(state_counts) else 0,
            'pct': state_percentages[i] if i < len(state_percentages) else 0
        }

    return {
        'has_data': True,
        'respondent_id': sb_data.get('respondent_id'),
        'lender_name': sb_data.get('lender_name'),
        'data_source': sb_data.get('data_source', 'CRA Data'),

        # Yearly data for chart
        'years': years,
        'lender_loan_counts': lender_counts,
        'lender_loan_amounts': lender_amounts,  # In thousands
        'national_loan_counts': national_counts,
        'national_loan_amounts': national_amounts,

        # Summary metrics
        'total_loans': total_loans,
        'total_amount_thousands': total_amount,
        'market_share': market_share,

        # State breakdown
        'top_states': states,
        'state_counts': state_counts,
        'state_percentages': state_percentages,
        'by_state': by_state,

        # States by year for interactive chart
        'states_by_year': sb_data.get('states_by_year', {})
    }


