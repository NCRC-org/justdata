"""
Flask routes for JustData dashboard pages.
These routes serve the HTML dashboard pages (landing, admin, analytics, status).
"""

from flask import render_template, Blueprint
import os

from justdata.main.auth import staff_required

# Get the templates directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'justdata', 'shared', 'web', 'templates')

# Create a Blueprint for dashboard routes
dashboard_bp = Blueprint(
    'dashboard',
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=os.path.join(BASE_DIR, 'justdata', 'shared', 'web', 'static'),
    static_url_path='/static'
)


@dashboard_bp.route('/admin')
def admin_dashboard():
    """Serve the administration dashboard."""
    from justdata.main.auth import has_access
    from flask import redirect, url_for
    # Admin dashboard requires developer access
    if not has_access('admin', 'full'):
        return redirect(url_for('landing'))
    # Pass landing_url to template
    return render_template('admin-dashboard.html', landing_url=url_for('landing'))


# NOTE: The /analytics route is now handled by the analytics blueprint
# in justdata/apps/analytics/blueprint.py which uses real BigQuery data.
# The old analytics-dashboard.html template with mock data is deprecated.


@dashboard_bp.route('/status')
@staff_required
def status_dashboard():
    """Serve the status dashboard (staff roles only).

    Internal page; it had no access check of its own and relied on the global
    staff-only gate, which tester roles pass on the testing deploy.
    """
    from flask import url_for
    return render_template('status-dashboard.html', landing_url=url_for('landing'))


def register_dashboard_routes(app):
    """
    Register dashboard routes with a Flask application.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(dashboard_bp)

