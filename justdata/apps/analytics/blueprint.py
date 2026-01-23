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

# Base template context
BASE_CONTEXT = {
    'app_name': 'Analytics',
    'app_description': 'Internal staff analytics for JustData usage patterns and coalition opportunities',
    'app_subtitle': 'Staff Analytics Tool'
}


def get_context(breadcrumb_items=None):
    """Get template context with optional breadcrumbs."""
    ctx = BASE_CONTEXT.copy()
    if breadcrumb_items:
        ctx['breadcrumb_items'] = breadcrumb_items
    return ctx


# ============================================
# Page Routes
# ============================================

@analytics_bp.route('/')
@login_required
@staff_required
def dashboard():
    """Main analytics dashboard."""
    breadcrumbs = [{'name': 'Analytics', 'url': '/analytics'}]
    return render_template('analytics/dashboard.html', **get_context(breadcrumbs))


@analytics_bp.route('/user-map')
@login_required
@staff_required
def user_map():
    """User locations map view."""
    breadcrumbs = [
        {'name': 'Analytics', 'url': '/analytics'},
        {'name': 'Report Locations', 'url': '/analytics/user-map'}
    ]
    return render_template('analytics/user_map.html', **get_context(breadcrumbs))


@analytics_bp.route('/research-map')
@login_required
@staff_required
def research_map():
    """Research activity map view."""
    breadcrumbs = [
        {'name': 'Analytics', 'url': '/analytics'},
        {'name': 'Research Activity', 'url': '/analytics/research-map'}
    ]
    return render_template('analytics/research_map.html', **get_context(breadcrumbs))


@analytics_bp.route('/lender-map')
@login_required
@staff_required
def lender_map():
    """Lender interest map view."""
    breadcrumbs = [
        {'name': 'Analytics', 'url': '/analytics'},
        {'name': 'Lender Interest', 'url': '/analytics/lender-map'}
    ]
    return render_template('analytics/lender_map.html', **get_context(breadcrumbs))


@analytics_bp.route('/coalitions')
@login_required
@staff_required
def coalitions():
    """Coalition opportunities table view."""
    breadcrumbs = [
        {'name': 'Analytics', 'url': '/analytics'},
        {'name': 'Coalitions', 'url': '/analytics/coalitions'}
    ]
    return render_template('analytics/coalitions.html', **get_context(breadcrumbs))


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
        # User type filtering
        user_types = request.args.getlist('user_types')
        exclude_user_types = request.args.getlist('exclude_user_types')
        data = get_user_locations(
            days=days,
            state=state,
            user_types=user_types if user_types else None,
            exclude_user_types=exclude_user_types if exclude_user_types else None
        )
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
        # User type filtering
        user_types = request.args.getlist('user_types')
        exclude_user_types = request.args.getlist('exclude_user_types')
        data = get_research_activity(
            days=days,
            app=app,
            state=state,
            user_types=user_types if user_types else None,
            exclude_user_types=exclude_user_types if exclude_user_types else None
        )
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
        # User type filtering
        user_types = request.args.getlist('user_types')
        exclude_user_types = request.args.getlist('exclude_user_types')
        data = get_lender_interest(
            days=days,
            min_users=min_users,
            user_types=user_types if user_types else None,
            exclude_user_types=exclude_user_types if exclude_user_types else None
        )
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


@analytics_bp.route('/api/user-types')
@login_required
@staff_required
def api_user_types():
    """Get list of distinct user types for filtering."""
    try:
        from .bigquery_client import get_bigquery_client, EVENTS_TABLE
        client = get_bigquery_client()
        query = f"""
            SELECT DISTINCT user_type
            FROM `{EVENTS_TABLE}`
            WHERE user_type IS NOT NULL
            ORDER BY user_type
        """
        results = client.query(query).result()
        user_types = [row.user_type for row in results if row.user_type]
        return jsonify({'success': True, 'data': user_types})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@analytics_bp.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'app': 'analytics'})
