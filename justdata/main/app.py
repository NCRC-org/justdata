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
    
    # Create app with shared templates folder as base
    # This allows blueprints to extend base_app.html
    app = Flask(
        'justdata',
        template_folder=MainConfig.TEMPLATES_DIR,  # Shared templates folder
        static_folder=MainConfig.STATIC_DIR
    )
    
    # Configuration
    app.secret_key = MainConfig.SECRET_KEY
    app.config['DEBUG'] = MainConfig.DEBUG
    app.config['SESSION_PERMANENT'] = True
    
    # Main landing page route
    @app.route('/')
    def landing():
        """Main landing page with app selection."""
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        from flask import url_for
        
        user_type = get_user_type()
        permissions = get_user_permissions(user_type)
        
        # Create Jinja2 environment with Flask's url_for function
        env = Environment(
            loader=FileSystemLoader(MainConfig.TEMPLATES_DIR),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Add Flask's url_for to the template globals
        env.globals['url_for'] = url_for
        
        template = env.get_template('justdata_landing_page.html')
        return template.render(user_type=user_type, permissions=permissions)
    
    # About page route
    @app.route('/about')
    def about():
        """About page."""
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        from flask import url_for
        
        user_type = get_user_type()
        permissions = get_user_permissions(user_type)
        
        # Create Jinja2 environment with Flask's url_for function
        env = Environment(
            loader=FileSystemLoader(MainConfig.TEMPLATES_DIR),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Add Flask's url_for to the template globals
        env.globals['url_for'] = url_for
        
        template = env.get_template('about.html')
        return template.render(user_type=user_type, permissions=permissions)
    
    # Contact page route
    @app.route('/contact')
    def contact():
        """Contact Us page."""
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        from flask import url_for
        
        user_type = get_user_type()
        permissions = get_user_permissions(user_type)
        
        # Create Jinja2 environment with Flask's url_for function
        env = Environment(
            loader=FileSystemLoader(MainConfig.TEMPLATES_DIR),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Add Flask's url_for to the template globals
        env.globals['url_for'] = url_for
        
        template = env.get_template('contact.html')
        return template.render(user_type=user_type, permissions=permissions)
    
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
    
    try:
        from justdata.apps.dataexplorer.blueprint import dataexplorer_bp
        app.register_blueprint(dataexplorer_bp, url_prefix='/dataexplorer')
    except ImportError:
        print("⚠️  DataExplorer blueprint not yet created")
    
    try:
        from justdata.apps.lenderprofile.blueprint import lenderprofile_bp
        app.register_blueprint(lenderprofile_bp, url_prefix='/lenderprofile')
    except ImportError:
        print("⚠️  LenderProfile blueprint not yet created")
    
    try:
        from justdata.apps.loantrends.blueprint import loantrends_bp
        app.register_blueprint(loantrends_bp, url_prefix='/loantrends')
    except ImportError:
        print("⚠️  LoanTrends blueprint not yet created")
    
    try:
        from justdata.apps.memberview.blueprint import memberview_bp
        app.register_blueprint(memberview_bp, url_prefix='/memberview')
    except ImportError:
        print("⚠️  MemberView blueprint not yet created")
    
    # Apps in development (from User Access Matrix)
    try:
        from justdata.apps.commentmaker.blueprint import commentmaker_bp
        app.register_blueprint(commentmaker_bp, url_prefix='/commentmaker')
    except ImportError:
        print("⚠️  CommentMaker blueprint not yet created (In Development)")
    
    try:
        from justdata.apps.justpolicy.blueprint import justpolicy_bp
        app.register_blueprint(justpolicy_bp, url_prefix='/justpolicy')
    except ImportError:
        print("⚠️  JustPolicy blueprint not yet created (In Development)")
    
    # Administrative tools
    try:
        from justdata.apps.analytics.blueprint import analytics_bp
        app.register_blueprint(analytics_bp, url_prefix='/analytics')
    except ImportError:
        print("⚠️  Analytics blueprint not yet created")

