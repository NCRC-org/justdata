"""
Flask application factory for creating consistent web apps.
Shared across BranchSeeker, BizSight, and LendSight.
"""

from flask import Flask, jsonify
from datetime import datetime
import os


def create_app(app_name: str, template_folder: str = None, static_folder: str = None, config: dict = None):
    """
    Create a Flask application with consistent configuration.
    
    Args:
        app_name: Name of the application (e.g., 'branchseeker', 'bizsight', 'lendsight')
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

