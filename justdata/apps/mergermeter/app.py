#!/usr/bin/env python3
"""
MergerMeter Flask web application - Bank merger analysis tool.
"""

from flask import render_template, request, jsonify
import os

from justdata.shared.web.app_factory import create_app
from .config import TEMPLATES_DIR, STATIC_DIR
from .version import __version__

# Create the Flask app
app = create_app(
    'mergermeter',
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)


@app.route('/')
def index():
    """Main page with the merger analysis form"""
    return render_template('analysis_template.html', version=__version__)


# Health check endpoint is automatically registered by app_factory


@app.route('/data')
def data():
    """Return app data (placeholder for future implementation)"""
    return jsonify({
        'message': 'MergerMeter data endpoint',
        'status': 'coming_soon'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8083))
    app.run(debug=True, host='0.0.0.0', port=port)

