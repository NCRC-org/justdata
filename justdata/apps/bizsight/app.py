#!/usr/bin/env python3
"""
BizSight Flask web application.
Uses the same routing patterns as BranchSeeker.
"""

from flask import render_template, request, jsonify
import os

from justdata.shared.web.app_factory import create_app, register_standard_routes
from justdata.core.config.app_config import BizSightConfig

# Template and static directories (shared)
TEMPLATES_DIR = os.path.join(BizSightConfig.BASE_DIR, 'shared', 'web', 'templates')
STATIC_DIR = os.path.join(BizSightConfig.BASE_DIR, 'shared', 'web', 'static')

# Create the Flask app
app = create_app(
    'bizsight',
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)


def index():
    """Main page with the analysis form"""
    return render_template('analysis_template.html')


def progress_handler(job_id):
    """Progress tracking endpoint"""
    # To be implemented
    return jsonify({'progress': 0})


def analyze():
    """Handle analysis request"""
    # To be implemented
    return jsonify({'success': False, 'error': 'Not yet implemented'})


def download():
    """Download the generated reports"""
    # To be implemented
    return jsonify({'error': 'Not yet implemented'}), 404


def data():
    """Return data for the application"""
    # To be implemented
    return jsonify([])


# Register standard routes
register_standard_routes(
    app,
    index_handler=index,
    analyze_handler=analyze,
    progress_handler=progress_handler,
    download_handler=download,
    data_handler=data
)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))
    app.run(debug=True, host='0.0.0.0', port=port)

