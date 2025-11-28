"""
Main Flask application for MemberView.
"""
from flask import Flask, render_template
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import blueprints with error handling
try:
    from map_routes import map_bp
except Exception as e:
    logger.error(f"Error importing map_routes: {e}", exc_info=True)
    map_bp = None

# Import search routes - handle different file structures
search_bp = None
try:
    # Try importing from app subdirectory
    import sys
    from pathlib import Path
    BASE_DIR = Path(__file__).parent
    app_dir = BASE_DIR / 'app'
    if (app_dir / 'search_routes.py').exists():
        sys.path.insert(0, str(BASE_DIR))
        import importlib.util
        spec = importlib.util.spec_from_file_location("search_routes", app_dir / 'search_routes.py')
        search_routes_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(search_routes_module)
        search_bp = search_routes_module.search_bp
    else:
        # Try direct import
        from search_routes import search_bp
except Exception as e:
    logger.error(f"Error importing search_routes: {e}", exc_info=True)
    search_bp = None


def create_app():
    """Create and configure Flask application."""
    import os
    from pathlib import Path
    
    # Get template and static directories
    BASE_DIR = Path(__file__).parent
    
    # Use root templates directory (where index.html is)
    # Blueprints can use their own template folders
    if (BASE_DIR / 'templates').exists():
        TEMPLATES_DIR = str(BASE_DIR / 'templates')
        STATIC_DIR = str(BASE_DIR / 'static')
    elif (BASE_DIR / 'web' / 'templates').exists():
        TEMPLATES_DIR = str(BASE_DIR / 'web' / 'templates')
        STATIC_DIR = str(BASE_DIR / 'web' / 'static')
    else:
        # Fallback
        TEMPLATES_DIR = str(BASE_DIR / 'templates')
        STATIC_DIR = str(BASE_DIR / 'static')
    
    # Verify directories exist
    if not Path(TEMPLATES_DIR).exists():
        logger.warning(f"Templates directory not found: {TEMPLATES_DIR}")
    if not Path(STATIC_DIR).exists():
        logger.warning(f"Static directory not found: {STATIC_DIR}")
    
    app = Flask(__name__, 
                template_folder=TEMPLATES_DIR,
                static_folder=STATIC_DIR)
    app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    
    # Register shared static folder for NCRC logo and shared CSS
    from flask import send_from_directory
    JUSTDATA_BASE = BASE_DIR.parent.parent
    SHARED_STATIC = str(JUSTDATA_BASE / 'shared' / 'web' / 'static')
    
    @app.route('/shared/<path:filename>')
    def shared_static(filename):
        return send_from_directory(SHARED_STATIC, filename)
    
    # Register blueprints (with error handling)
    if map_bp is not None:
        try:
            app.register_blueprint(map_bp)
        except Exception as e:
            logger.error(f"Error registering map blueprint: {e}", exc_info=True)
    else:
        logger.warning("Map blueprint not available - map features will be disabled")
    
    if search_bp is not None:
        try:
            app.register_blueprint(search_bp)
        except Exception as e:
            logger.error(f"Error registering search blueprint: {e}", exc_info=True)
    else:
        logger.warning("Search blueprint not available - search features will be disabled")
    
    @app.route('/')
    def index():
        """Home page."""
        try:
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error rendering index template: {e}", exc_info=True)
            return f"Error loading page: {str(e)}", 500
    
    @app.route('/map')
    def member_map():
        """Member map page."""
        try:
            return render_template('member_map.html')
        except Exception as e:
            logger.error(f"Error rendering map template: {e}", exc_info=True)
            return f"Error loading map: {str(e)}", 500
    
    @app.route('/search')
    def search_page_direct():
        """Member search page - direct route (fallback if blueprint fails)."""
        try:
            # Check if we have web/templates or templates directory
            if (BASE_DIR / 'web' / 'templates' / 'member_search.html').exists():
                return render_template('member_search.html')
            elif (BASE_DIR / 'templates' / 'member_search.html').exists():
                return render_template('member_search.html')
            else:
                return "Search page template not found. Please check file structure.", 500
        except Exception as e:
            logger.error(f"Error rendering search template: {e}", exc_info=True)
            return f"Error loading search page: {str(e)}", 500
    
    @app.route('/member/<member_id>')
    def member_detail(member_id):
        """Member detail page."""
        return render_template('member_detail.html', member_id=member_id)
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=8082)

