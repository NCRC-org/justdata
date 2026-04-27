"""Official-related route handlers (list / detail / trends / profile).

Route-handler implementations extracted from blueprint.py. Each
function uses Flask's request context the same way it did inline
in the blueprint; the blueprint now contains thin wrappers that call
into here.
"""
import json
import logging
import threading
import uuid
from pathlib import Path
from urllib.parse import unquote

from flask import jsonify, render_template, request, Response, session

from justdata.main.auth import (
    admin_required,
    get_user_type,
    login_required,
    require_access,
    staff_required,
)
from justdata.shared.utils.progress_tracker import (
    create_progress_tracker,
    get_analysis_result,
    get_progress,
    store_analysis_result,
)

logger = logging.getLogger(__name__)


def official_profile(official_id):
    """Individual official profile page."""
    breadcrumb_items = [
        {'name': 'ElectWatch', 'url': '/electwatch'},
        {'name': 'Official Profile', 'url': f'/electwatch/official/{official_id}'}
    ]
    return render_template(
        'official_profile.html',
        version=__version__,
        official_id=official_id,
        app_name='ElectWatch',
        breadcrumb_items=breadcrumb_items
    )

def api_officials():
    """
    Officials API endpoint with filtering support.

    Query params:
        - chamber: 'house' or 'senate'
        - party: 'R', 'D', or 'I'
        - state: Two-letter state code
        - industry: Industry sector code
        - sort: 'score', 'total', 'contributions', 'trades'
        - limit: Number of results (default 100)
    """
    try:
        from justdata.apps.electwatch.services.data_store import get_officials

        # Get filter parameters
        chamber = request.args.get('chamber')
        party = request.args.get('party')
        state = request.args.get('state')
        industry = request.args.get('industry')
        sort_by = request.args.get('sort', 'score')
        limit = request.args.get('limit', 100, type=int)

        officials = get_officials()

        # Apply filters
        filtered = officials

        if chamber:
            filtered = [o for o in filtered if o.get('chamber', '').lower() == chamber.lower()]
        if party:
            filtered = [o for o in filtered if o.get('party', '').upper() == party.upper()]
        if state:
            filtered = [o for o in filtered if o.get('state', '').upper() == state.upper()]
        if industry:
            # top_industries can be list of objects [{code, name}] or list of strings
            filtered = [o for o in filtered if any(
                (ind.get('code') == industry if isinstance(ind, dict) else ind == industry)
                for ind in o.get('top_industries', [])
            )]

        # Sort
        if sort_by == 'score':
            filtered.sort(key=lambda x: x.get('involvement_score', 0), reverse=True)
        elif sort_by == 'contributions':
            filtered.sort(key=lambda x: x.get('contributions', 0), reverse=True)
        elif sort_by == 'trades':
            filtered.sort(key=lambda x: x.get('stock_trades_max', 0), reverse=True)
        else:
            filtered.sort(key=lambda x: x.get('total_amount', 0), reverse=True)

        # Apply limit
        if limit:
            filtered = filtered[:limit]

        return jsonify({'success': True, 'officials': filtered})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def api_official(official_id):
    """Single official API endpoint."""
    try:
        from justdata.apps.electwatch.services.data_store import get_official
        official = get_official(official_id)
        if official:
            return jsonify({'success': True, 'official': official})
        return jsonify({'success': False, 'error': 'Official not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def api_official_trends(official_id):
    """
    Get time-series trend data for a specific official.

    Returns quarterly aggregated data for trades and contributions,
    suitable for rendering trend charts.

    Response:
    {
        "success": true,
        "official_id": "ted_cruz",
        "name": "Ted Cruz",
        "trades_by_quarter": [
            {"quarter": "Q1 2024", "purchases": 50000, "sales": 25000, "net": 25000, "count": 5},
            ...
        ],
        "contributions_by_quarter": [
            {"quarter": "Q1 2024", "amount": 100000, "count": 10},
            ...
        ],
        "trade_trend": "increasing|decreasing|stable",
        "has_trend_data": true
    }
    """
    try:
        from justdata.apps.electwatch.services.data_store import (
            get_official, compute_official_trends
        )

        official = get_official(official_id)
        if not official:
            return jsonify({'success': False, 'error': 'Official not found'}), 404

        # Check if trend data was pre-computed during weekly update
        if official.get('trades_by_quarter'):
            return jsonify({
                'success': True,
                'official_id': official_id,
                'name': official.get('name', ''),
                'trades_by_quarter': official.get('trades_by_quarter', []),
                'contributions_by_quarter': official.get('contributions_by_quarter', []),
                'trade_trend': official.get('trade_trend', 'stable'),
                'has_trend_data': official.get('has_trend_data', False)
            })

        # Compute trends on-demand if not pre-computed
        trend_data = compute_official_trends(official)

        return jsonify({
            'success': True,
            'official_id': official_id,
            'name': official.get('name', ''),
            **trend_data
        })

    except Exception as e:
        logger.error(f"Error getting trends for {official_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

