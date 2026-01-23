"""
Flask Blueprint for Analytics application.

Provides admin-only routes for viewing user activity patterns,
research activity maps, and coalition-building opportunities.
"""

from flask import Blueprint, jsonify, request, render_template
from justdata.main.auth import login_required, admin_required, staff_required

from .bigquery_client import (
    get_user_locations,
    get_research_activity,
    get_lender_interest,
    get_coalition_opportunities,
    get_summary,
    get_user_activity_timeline
)

# Create blueprint
analytics_bp = Blueprint(
    'analytics',
    __name__,
    url_prefix='/analytics',
    template_folder='templates',
    static_folder='static',
    static_url_path='/analytics/static'
)


# ============================================
# Page Routes
# ============================================

@analytics_bp.route('/')
@login_required
@staff_required
def dashboard():
    """Main analytics dashboard."""
    return render_template('analytics/dashboard.html')


@analytics_bp.route('/user-map')
@login_required
@staff_required
def user_map():
    """User locations map view."""
    return render_template('analytics/user_map.html')


@analytics_bp.route('/research-map')
@login_required
@staff_required
def research_map():
    """Research activity map view."""
    return render_template('analytics/research_map.html')


@analytics_bp.route('/lender-map')
@login_required
@staff_required
def lender_map():
    """Lender interest map view."""
    return render_template('analytics/lender_map.html')


@analytics_bp.route('/coalitions')
@login_required
@staff_required
def coalitions():
    """Coalition opportunities table view."""
    return render_template('analytics/coalitions.html')


# ============================================
# API Routes
# ============================================

@analytics_bp.route('/api/summary')
@login_required
@staff_required
def api_summary():
    """Get summary metrics for dashboard."""
    try:
        days = request.args.get('days', 90, type=int)
        data = get_summary(days=days)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/api/user-locations')
@login_required
@staff_required
def api_user_locations():
    """Get user location clusters."""
    try:
        days = request.args.get('days', 90, type=int)
        state = request.args.get('state', None)
        data = get_user_locations(days=days, state=state)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/api/research-activity')
@login_required
@staff_required
def api_research_activity():
    """Get research activity by county."""
    try:
        days = request.args.get('days', 90, type=int)
        app = request.args.get('app', None)
        state = request.args.get('state', None)
        data = get_research_activity(days=days, app=app, state=state)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/api/lender-interest')
@login_required
@staff_required
def api_lender_interest():
    """Get lender interest data."""
    try:
        days = request.args.get('days', 90, type=int)
        min_users = request.args.get('min_users', 1, type=int)
        data = get_lender_interest(days=days, min_users=min_users)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/api/coalition-opportunities')
@login_required
@staff_required
def api_coalition_opportunities():
    """Get coalition-building opportunities."""
    try:
        days = request.args.get('days', 90, type=int)
        min_users = request.args.get('min_users', 3, type=int)
        entity_type = request.args.get('entity_type', None)
        data = get_coalition_opportunities(
            days=days,
            min_users=min_users,
            entity_type=entity_type
        )
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/api/timeline')
@login_required
@staff_required
def api_timeline():
    """Get activity timeline data."""
    try:
        days = request.args.get('days', 30, type=int)
        data = get_user_activity_timeline(days=days)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'app': 'analytics'})
