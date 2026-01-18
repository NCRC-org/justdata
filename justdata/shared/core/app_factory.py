"""
Flask application factory for creating consistent web apps.
Shared across all JustData apps (LendSight, BizSight, BranchSight, etc.)
"""

from flask import Flask, jsonify, send_from_directory
from jinja2 import ChoiceLoader, FileSystemLoader
from datetime import datetime
import os
from pathlib import Path


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

    # Add shared templates folder to Jinja2 loader
    # This allows templates to {% include "shared_header.html" %} etc.
    shared_templates_dir = Path(__file__).parent.parent / 'web' / 'templates'
    if shared_templates_dir.exists() and template_folder:
        app.jinja_loader = ChoiceLoader([
            FileSystemLoader(template_folder),
            FileSystemLoader(str(shared_templates_dir))
        ])

    # Default configuration
    app.secret_key = os.environ.get('SECRET_KEY', f'{app_name}-secret-key-change-this')

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

    # Register favicon routes to serve from shared static folder
    # Path to shared static folder (one level up from shared/core)
    shared_static_dir = Path(__file__).parent.parent / 'web' / 'static'

    @app.route('/favicon.ico')
    def favicon_ico():
        """Serve favicon.ico from shared static folder"""
        favicon_path = shared_static_dir / 'favicon.ico'
        if favicon_path.exists():
            return send_from_directory(str(shared_static_dir), 'favicon.ico', mimetype='image/x-icon')
        # Fallback to favicon.png if favicon.ico doesn't exist
        favicon_png_path = shared_static_dir / 'favicon.png'
        if favicon_png_path.exists():
            return send_from_directory(str(shared_static_dir), 'favicon.png', mimetype='image/x-icon')
        return '', 204  # No Content if file doesn't exist

    @app.route('/favicon-32x32.png')
    def favicon_32x32():
        """Serve favicon-32x32.png from shared static folder"""
        favicon_path = shared_static_dir / 'favicon-32x32.png'
        if favicon_path.exists():
            return send_from_directory(str(shared_static_dir), 'favicon-32x32.png', mimetype='image/png')
        return '', 204  # No Content if file doesn't exist

    @app.route('/favicon-16x16.png')
    def favicon_16x16():
        """Serve favicon-16x16.png from shared static folder"""
        favicon_path = shared_static_dir / 'favicon-16x16.png'
        if favicon_path.exists():
            return send_from_directory(str(shared_static_dir), 'favicon-16x16.png', mimetype='image/png')
        return '', 204  # No Content if file doesn't exist

    return app


def register_standard_routes(app: Flask, index_handler, analyze_handler, progress_handler, download_handler,
                            report_handler=None, report_data_handler=None, data_handler=None):
    """
    Register standard routes for all report generator applications.

    Args:
        app: Flask application instance
        index_handler: Handler for main page (/)
        analyze_handler: Handler for analysis (/analyze POST)
        progress_handler: Handler for progress tracking (/progress/<job_id>)
        download_handler: Handler for downloads (/download)
        report_handler: Optional handler for report page (/report)
        report_data_handler: Optional handler for report data (/report-data)
        data_handler: Optional handler for data endpoint (e.g., /counties, /entities)
    """
    app.add_url_rule('/', 'index', index_handler, methods=['GET'])
    app.add_url_rule('/analyze', 'analyze', analyze_handler, methods=['POST'])
    app.add_url_rule('/progress/<job_id>', 'progress', progress_handler, methods=['GET'])
    app.add_url_rule('/download', 'download', download_handler, methods=['GET'])

    if report_handler:
        app.add_url_rule('/report', 'report', report_handler, methods=['GET'])

    if report_data_handler:
        app.add_url_rule('/report-data', 'report_data', report_data_handler, methods=['GET'])

    if data_handler:
        app.add_url_rule('/data', 'data', data_handler, methods=['GET'])
