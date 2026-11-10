"""
Flask application factory for creating consistent web apps.
Shared across BranchSight, BizSight, LendSight, MergerMeter, and other JustData apps.
"""

from flask import Flask, jsonify
from jinja2 import ChoiceLoader, FileSystemLoader
from datetime import datetime
import os
import secrets

from justdata.shared.utils.name_utils import strip_trailing_punctuation


# Defaults that once shipped in this repo. They are public, so a key equal to
# one of them signs nothing safely.
_PUBLIC_DEFAULT_KEYS = frozenset({
    'justdata-shared-secret-key-set-SECRET_KEY-in-production',
    'justdata-secret-key-change-in-production',
    'justdata-secret-key-change-this',
    'change-this-secret',
    'change-in-production',
})


def resolve_secret_key() -> str:
    """The key that signs session cookies, which carry the user's role.

    Outside FLASK_DEBUG the app refuses to start without SECRET_KEY, or with
    a key this repo once shipped as a default. Under FLASK_DEBUG a random key
    is used instead, so local sessions end when the process restarts.
    """
    key = os.environ.get('SECRET_KEY')
    if key and key not in _PUBLIC_DEFAULT_KEYS:
        return key
    if os.getenv('FLASK_DEBUG', '').lower() in ('1', 'true'):
        print("WARNING: SECRET_KEY not set; using a random key for this process (FLASK_DEBUG).")
        return secrets.token_hex(32)
    problem = 'is a public default' if key else 'is not set'
    raise RuntimeError(
        f"SECRET_KEY {problem}. It signs the session cookie, which carries the user's "
        "role, so the app will not start without a private key. Mount it from Secret "
        "Manager, or set FLASK_DEBUG=1 for local development."
    )

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

    app.secret_key = resolve_secret_key()

    # Configure session for better persistence
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Apply custom configuration
    if config:
        app.config.update(config)
    
    # Register Jinja2 template filters
    app.jinja_env.filters['clean_name'] = strip_trailing_punctuation

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

