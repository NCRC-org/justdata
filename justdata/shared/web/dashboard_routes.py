"""
Flask routes for JustData dashboard pages.
These routes serve the HTML dashboard pages (landing, admin, analytics, status).
"""

from flask import render_template, Blueprint
import os

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


@dashboard_bp.route('/analytics')
def analytics_dashboard():
    """Serve the analytics dashboard."""
    from justdata.main.auth import has_access
    from flask import redirect, url_for
    # Analytics requires staff access
    if not has_access('analytics', 'full'):
        return redirect(url_for('landing'))
    # Pass landing_url to template
    return render_template('analytics-dashboard.html', landing_url=url_for('landing'))


@dashboard_bp.route('/status')
def status_dashboard():
    """Serve the status dashboard."""
    from flask import url_for
    return render_template('status-dashboard.html', landing_url=url_for('landing'))


def register_dashboard_routes(app):
    """
    Register dashboard routes with a Flask application.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(dashboard_bp)

