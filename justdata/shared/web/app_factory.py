"""
Flask application factory for creating consistent web apps.
Shared across BranchSight, BizSight, LendSight, MergerMeter, and other JustData apps.
"""

from flask import Flask, jsonify
from jinja2 import ChoiceLoader, FileSystemLoader
from datetime import datetime
import os


# Shared fallback secret key for all JustData apps (consistent across instances)
# In production, SECRET_KEY should ALWAYS be set via environment variable
_FALLBACK_SECRET_KEY = 'justdata-shared-secret-key-set-SECRET_KEY-in-production'

# Path to shared templates
SHARED_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')


def create_app(app_name: str, template_folder: str = None, static_folder: str = None, config: dict = None):
    """
    Create a Flask application with consistent configuration.

    Args:
        app_name: Name of the application (e.g., 'branchsight', 'bizsight', 'lendsight')
        template_folder: Path to templates folder
        static_folder: Path to static files folder
        config: Additional configuration dictionary

    Returns:
        Flask application instance
    """
    app = Flask(
        app_name,
        template_folder=template_folder,
        static_folder=static_folder
    )

    # Add shared templates directory to Jinja search path
    # This allows apps to include shared templates like report_interstitial.html
    if template_folder:
        app.jinja_loader = ChoiceLoader([
            FileSystemLoader(template_folder),
            FileSystemLoader(SHARED_TEMPLATES_DIR)
        ])

    # Get SECRET_KEY from environment - use consistent fallback across all apps
    # This ensures sessions persist across different apps in the unified platform
    secret_key = os.environ.get('SECRET_KEY')
    if secret_key:
        app.secret_key = secret_key
    else:
        app.secret_key = _FALLBACK_SECRET_KEY
        print(f"[{app_name}] WARNING: SECRET_KEY not set in environment, using fallback. "
              "Set SECRET_KEY environment variable in production for secure sessions.")

    # Configure session for better persistence
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Apply custom configuration
    if config:
        app.config.update(config)
    
    # Register standard health check endpoint
    @app.route('/health')
    def health():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'app': app_name,
            'timestamp': datetime.now().isoformat()
        })
    
    return app


def register_standard_routes(app: Flask, index_handler, analyze_handler, progress_handler, download_handler, data_handler=None):
    """
    Register standard routes for all applications.
    
    Args:
        app: Flask application instance
        index_handler: Handler for main page (/)
        analyze_handler: Handler for analysis (/analyze POST)
        progress_handler: Handler for progress tracking (/progress/<job_id>)
        download_handler: Handler for downloads (/download)
        data_handler: Optional handler for data endpoint (e.g., /counties, /entities)
    """
    app.add_url_rule('/', 'index', index_handler, methods=['GET'])
    app.add_url_rule('/analyze', 'analyze', analyze_handler, methods=['POST'])
    app.add_url_rule('/progress/<job_id>', 'progress', progress_handler, methods=['GET'])
    app.add_url_rule('/download', 'download', download_handler, methods=['GET'])
    
    if data_handler:
        app.add_url_rule('/data', 'data', data_handler, methods=['GET'])

