"""Lending footprint section."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from justdata.apps.lenderprofile.report_builder.helpers import _format_currency

def build_lending_footprint(
    institution_data: Dict[str, Any],
    hmda_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build lending footprint section from HMDA data.

    Shows top metros where the lender concentrates lending activity.
    Especially important for mortgage companies that don't have branches.

    Args:
        institution_data: Complete institution data
        hmda_data: HMDA lending footprint data from BigQueryHMDAClient

    Returns:
        Dictionary with:
        - top_metros: Top 10 metros by application count
        - states: State-level breakdown
        - concentration: Geographic concentration metrics
        - lender_type: Bank, Mortgage Company, Credit Union, etc.
    """
    # Get lender type from institution data
    identifiers = institution_data.get('identifiers', {})
    details = institution_data.get('details', {})

    lender_type = (
        identifiers.get('type') or
        identifiers.get('lender_type') or
        details.get('type_name') or
        'Unknown'
    )

    # Normalize lender type
    lender_type_lower = lender_type.lower()
    if 'mortgage' in lender_type_lower:
        lender_category = 'Mortgage Company'
    elif 'credit union' in lender_type_lower or 'cu' == lender_type_lower:
        lender_category = 'Credit Union'
    elif 'bank' in lender_type_lower:
        lender_category = 'Bank'
    else:
        lender_category = lender_type

    if not hmda_data:
        return {
            'has_data': False,
            'lender_type': lender_category,
            'top_metros': [],
            'states': [],
            'message': 'No HMDA lending data available.'
        }

    # Get yearly data from the actual data structure
    by_year = hmda_data.get('by_year', {})
    states_by_year = hmda_data.get('states_by_year', {})
    by_purpose_year = hmda_data.get('by_purpose_year', {})
    year = hmda_data.get('year')

    # Calculate total applications across all years
    total_applications = sum(by_year.values()) if by_year else 0

    # Calculate unique states from states_by_year
    all_states = set()
    state_totals = {}  # For building state breakdown
    for year_key, year_states in states_by_year.items():
        if isinstance(year_states, list):
            all_states.update(year_states)
            for s in year_states:
                state_totals[s] = state_totals.get(s, 0) + 1  # Count years active
        elif isinstance(year_states, dict):
            all_states.update(year_states.keys())
            for s, count in year_states.items():
                state_totals[s] = state_totals.get(s, 0) + count

    # Build formatted states for display (sorted by total activity)
    formatted_states = []
    sorted_states = sorted(state_totals.items(), key=lambda x: -x[1])
    for state, count in sorted_states[:10]:
        pct = (count / total_applications * 100) if total_applications > 0 else 0
        formatted_states.append({
            'state': state,
            'applications': count,
            'pct_of_total': round(pct, 1)
        })

    # Create by_state dict for chart
    by_state = {s['state']: s['applications'] for s in formatted_states}

    # Calculate concentration metrics
    state_count = len(all_states)
    is_national = state_count >= 40
    top_5_pct = sum(s['pct_of_total'] for s in formatted_states[:5]) if formatted_states else 0
    is_concentrated = top_5_pct > 60

    concentration = {
        'top_5_metros_pct': 0,  # No metro data available in current structure
        'is_concentrated': is_concentrated,
        'is_national': is_national
    }

    return {
        'has_data': total_applications > 0 or len(all_states) > 0,
        'lender_type': lender_category,
        'year': year,
        'total_applications': total_applications,
        'top_metros': [],  # Not available in current data structure
        'states': formatted_states,
        'by_state': by_state,
        'top_states': formatted_states,
        'total_states': state_count,
        'total_metros': 0,  # Not available in current data structure
        'concentration': concentration,
        'footprint_description': _describe_footprint(lender_category, state_count, concentration),
        # Multi-year data for trend charts
        'by_year': by_year,
        'states_by_year': states_by_year,
        'national_by_year': hmda_data.get('national_by_year', {}),
        # Loan purpose data for stacked column chart
        'by_purpose_year': by_purpose_year,
        'national_by_purpose_year': hmda_data.get('national_by_purpose_year', {})
    }


def _describe_footprint(lender_type: str, state_count: int, concentration: Dict[str, Any]) -> str:
    """Generate a natural language description of the lender's footprint."""
    is_national = concentration.get('is_national', False)
    is_concentrated = concentration.get('is_concentrated', False)
    top_5_pct = concentration.get('top_5_metros_pct', 0)

    if is_national:
        scope = "national"
    elif state_count >= 20:
        scope = "multi-regional"
    elif state_count >= 5:
        scope = "regional"
    else:
        scope = "local"

    if is_concentrated:
        focus = f"concentrated in top 5 metros ({top_5_pct:.0f}% of lending)"
    else:
        focus = "diversified across markets"

    return f"{scope.capitalize()} {lender_type.lower()} with lending {focus}."


