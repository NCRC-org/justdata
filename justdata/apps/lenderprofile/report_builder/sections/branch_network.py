"""Branch network section."""
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from justdata.apps.lenderprofile.report_builder.helpers import _format_currency

def build_branch_network(institution_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build branch network summary (simplified for intelligence focus).
    """
    branch_data = institution_data.get('branches', {})
    branches = branch_data.get('locations', [])
    analysis = branch_data.get('analysis', {})
    history = branch_data.get('history', {})

    total_branches = len(branches)

    # Group by state (top 10) for current year
    by_state = {}
    for branch in branches:
        state = branch.get('state') or branch.get('STALP', 'Unknown')
        if state not in by_state:
            by_state[state] = 0
        by_state[state] += 1

    # All states sorted by count (no limit)
    top_states = sorted(by_state.items(), key=lambda x: x[1], reverse=True)

    # Build states_by_year from history for interactive chart
    states_by_year = {}
    for year, year_branches in history.items():
        year_states = {}
        for branch in year_branches:
            state = branch.get('state') or branch.get('STALP', 'Unknown')
            if state not in year_states:
                year_states[state] = 0
            year_states[state] += 1
        # All states for this year, sorted by count
        all_year_states = sorted(year_states.items(), key=lambda x: x[1], reverse=True)
        states_by_year[year] = dict(all_year_states)

    # Trends - use total branches by year from analysis summary
    trends = {}
    if analysis:
        summary = analysis.get('summary', {})
        total_branches_by_year = summary.get('total_branches_by_year', {})
        net_change_by_year = analysis.get('net_change_by_year', {})
        trends = {
            'net_change': net_change_by_year,
            'by_year': total_branches_by_year,  # Total branches per year for chart
            'trend': 'expanding' if sum(net_change_by_year.values()) > 0 else 'contracting'
        }

    # National branch totals for comparison (FDIC data - approximate)
    # TODO: Replace with actual BigQuery data
    national_branches_by_year = {
        '2021': 76659,
        '2022': 74923,
        '2023': 72723,
        '2024': 70987,
        '2025': 69548
    }

    return {
        'total_branches': total_branches,
        'top_states': dict(top_states),
        'states_by_year': states_by_year,
        'trends': trends,
        'national_by_year': national_branches_by_year,
        'has_data': total_branches > 0
    }


