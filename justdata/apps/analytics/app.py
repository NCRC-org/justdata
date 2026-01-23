"""
Flask application factory for Analytics app.
"""

from flask import Flask
from .config import config


def create_app():
    """Create and configure the Analytics Flask application."""
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    app.config['SECRET_KEY'] = config.APP_NAME + '-secret-key'
    app.config['DEBUG'] = config.DEBUG

    # Register blueprint
    from .blueprint import analytics_bp
    app.register_blueprint(analytics_bp)

    return app


# Create app instance for imports
app = create_app()
