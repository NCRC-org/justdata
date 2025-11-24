"""
Main Flask application for JustData.
Serves as the central entry point with all sub-apps as blueprints.
"""

from flask import Flask, render_template, session, request, jsonify
from justdata.main.auth import get_user_type, set_user_type, get_app_access, get_user_permissions
from justdata.main.config import MainConfig
import os


def create_app():
    """Create and configure the main Flask application."""
    
    app = Flask(
        'justdata',
        template_folder=MainConfig.TEMPLATES_DIR,
        static_folder=MainConfig.STATIC_DIR
    )
    
    # Configuration
    app.secret_key = MainConfig.SECRET_KEY
    app.config['DEBUG'] = MainConfig.DEBUG
    app.config['SESSION_PERMANENT'] = True
    
    # Main landing page route (handled by main app)
    @app.route('/')
    @app.route('/landing')
    def landing():
        """Main landing page with app selection."""
        user_type = get_user_type()
        permissions = get_user_permissions(user_type)
        return render_template('justdata_landing_page.html', 
                             user_type=user_type,
                             permissions=permissions)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register dashboard routes (after landing route to avoid conflicts)
    from justdata.shared.web.dashboard_routes import register_dashboard_routes
    register_dashboard_routes(app)
    
    # API endpoint to set user type (for testing/demo)
    @app.route('/api/set-user-type', methods=['POST'])
    def api_set_user_type():
        """Set user type (for demo/testing purposes)."""
        data = request.get_json() or {}
        user_type = data.get('user_type', 'public')
        try:
            set_user_type(user_type)
            return jsonify({
                'success': True, 
                'user_type': user_type,
                'permissions': get_user_permissions(user_type)
            })
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
    
    # API endpoint to get access info
    @app.route('/api/access-info')
    def api_access_info():
        """Get access information for current user."""
        user_type = get_user_type()
        apps = ['lendsight', 'branchseeker', 'branchmapper', 'bizsight', 
                'mergermeter', 'memberview', 'analytics', 'admin']
        
        access_info = {}
        for app in apps:
            access_level = get_app_access(app, user_type)
            access_info[app] = {
                'access': access_level,
                'visible': access_level != 'hidden',
                'locked': access_level == 'locked'
            }
        
        return jsonify({
            'user_type': user_type,
            'permissions': get_user_permissions(user_type),
            'apps': access_info
        })
    
    # Health check
    @app.route('/health')
    def health():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'app': 'justdata',
            'version': MainConfig.APP_VERSION
        })
    
    return app


def register_blueprints(app: Flask):
    """Register all sub-application blueprints."""
    
    # Import and register blueprints
    # We'll create these in the next steps
    try:
        from justdata.apps.branchseeker.blueprint import branchseeker_bp
        app.register_blueprint(branchseeker_bp, url_prefix='/branchseeker')
    except ImportError:
        print("⚠️  BranchSeeker blueprint not yet created")
    
    try:
        from justdata.apps.bizsight.blueprint import bizsight_bp
        app.register_blueprint(bizsight_bp, url_prefix='/bizsight')
    except ImportError:
        print("⚠️  BizSight blueprint not yet created")
    
    try:
        from justdata.apps.lendsight.blueprint import lendsight_bp
        app.register_blueprint(lendsight_bp, url_prefix='/lendsight')
    except ImportError:
        print("⚠️  LendSight blueprint not yet created")
    
    try:
        from justdata.apps.mergermeter.blueprint import mergermeter_bp
        app.register_blueprint(mergermeter_bp, url_prefix='/mergermeter')
    except ImportError:
        print("⚠️  MergerMeter blueprint not yet created")
    
    try:
        from justdata.apps.branchmapper.blueprint import branchmapper_bp
        app.register_blueprint(branchmapper_bp, url_prefix='/branchmapper')
    except ImportError:
        print("⚠️  BranchMapper blueprint not yet created")

