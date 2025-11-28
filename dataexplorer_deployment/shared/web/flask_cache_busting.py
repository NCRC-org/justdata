#!/usr/bin/env python3
"""
Shared Flask cache-busting utilities.
Apply to all Flask apps to ensure consistent cache-busting behavior.
"""

from flask import Flask
from datetime import datetime
import time


def configure_flask_cache_busting(app: Flask):
    """
    Configure Flask app with aggressive cache-busting settings.
    Call this during app initialization.
    
    Args:
        app: Flask application instance
    """
    # Force DEBUG mode for development to enable auto-reload
    app.config['DEBUG'] = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True  # Force template reload on every request
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable static file caching
    app.config['EXPLAIN_TEMPLATE_LOADING'] = True  # Debug template loading
    
    # DISABLE Jinja2 bytecode cache completely
    app.jinja_env.bytecode_cache = None
    
    print("=" * 80, flush=True)
    print("CONFIGURED FLASK CACHE-BUSTING", flush=True)
    print(f"✓ Jinja2 bytecode_cache disabled: {app.jinja_env.bytecode_cache}", flush=True)
    print(f"✓ Template folder: {app.template_folder}", flush=True)
    print(f"✓ Static folder: {app.static_folder}", flush=True)
    print("=" * 80, flush=True)
    
    # Add before_request handler to clear cache
    @app.before_request
    def clear_template_cache():
        """Clear Jinja2 template cache before each request."""
        if hasattr(app, 'jinja_env'):
            app.jinja_env.bytecode_cache = None
            app.jinja_env.cache = {}
            app.jinja_env.auto_reload = True
            try:
                if hasattr(app.jinja_env.cache, 'clear'):
                    app.jinja_env.cache.clear()
            except:
                pass


def add_cache_busting_headers(response):
    """
    Add aggressive cache-busting headers to a Flask response.
    Use this on all route responses.
    
    Args:
        response: Flask response object
    
    Returns:
        Response with cache-busting headers added
    """
    timestamp = int(time.time())
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['ETag'] = f'"{timestamp}"'
    response.headers['Last-Modified'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
    return response

