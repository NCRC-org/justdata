"""
Main Flask application for JustData.
Serves as the central entry point with all sub-apps as blueprints.
"""

from flask import Flask, render_template, session, request, jsonify, send_from_directory, redirect
from justdata.main.auth import (
    get_user_type, set_user_type, get_app_access, get_user_permissions,
    auth_bp, init_firebase, get_current_user, is_authenticated, is_privileged_user,
    login_required, admin_required
)
from justdata.main.auth.access_overlay import is_tester, testing_gate_admits
from justdata.main.config import MainConfig
import os


# Paths that don't require privileged access
EXEMPT_PATHS = [
    '/health',
    '/favicon.ico',
    '/static/',
    '/shared/',
    '/api/auth/',  # Auth routes for login/logout
    '/api/platform-stats',  # Public homepage stats (no auth; avoids 127.0.0.1 vs localhost cookie mismatch)
    '/mergermeter/api/generate',  # API key auth, not Firebase — used by codebot
    '/mergermeter/api/search-banks-ext',  # API key auth — used by codebot for entity resolution
]


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

    # Session cookie settings for cross-path persistence
    app.config['SESSION_COOKIE_PATH'] = '/'  # Ensure cookie is sent for all paths
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Allow cross-site GET requests
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Security: prevent JS access
    # Use secure cookies only in production (HTTPS)
    app.config['SESSION_COOKIE_SECURE'] = not MainConfig.DEBUG

    # Session lifetime - 30 days
    from datetime import timedelta
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

    # Initialize Firebase Authentication
    try:
        init_firebase()
        print("[INFO] Firebase initialized successfully")
    except Exception as e:
        print(f"[WARN] Firebase initialization failed: {e}")

    # Register authentication blueprint
    app.register_blueprint(auth_bp)
    print("[INFO] Auth blueprint registered at /api/auth")

    # Context processor to make auth info available in all templates
    @app.context_processor
    def inject_auth():
        """Make authentication info available to all templates."""
        return {
            'current_user': get_current_user(),
            'is_authenticated': is_authenticated(),
            'user_type': get_user_type()
        }

    # Context processor for the shared shell (nav drawer, footer, version).
    # nav_groups/secondary_pages come from shared/web/registry.py. visible_apps
    # is kept as-is, though no shipped template reads it any more.
    # App-wide, so every blueprint's templates get the shell context --
    # including the ones still using the legacy shared_header.html include
    # directly rather than extending base_app.html (see the step 2 PR/L5 log
    # for why shared_header.html itself was kept rather than deleted).
    @app.context_processor
    def inject_shell():
        """Make the platform-shell nav list and version available to templates."""
        from justdata.main.auth import get_access_row
        from justdata.shared.utils.versions import get_version
        from justdata.shared.web.registry import SECONDARY_PAGES, resolve_registry

        shell_user_type = get_user_type()
        shell_app_order = [
            ('lendsight', 'LendSight', '/lendsight'),
            ('bizsight', 'BizSight', '/bizsight'),
            ('branchsight', 'BranchSight', '/branchsight'),
            ('branchmapper', 'BranchMapper', '/branchmapper'),
            ('mergermeter', 'MergerMeter', '/mergermeter'),
            ('dataexplorer', 'DataExplorer', '/dataexplorer'),
            ('analytics', 'Analytics', '/analytics'),
            ('admin', 'Administration', '/admin/users'),
        ]
        visible_apps = []
        for shell_key, shell_name, shell_url in shell_app_order:
            shell_access = get_app_access(shell_key, shell_user_type)
            if shell_access == 'hidden':
                continue
            visible_apps.append({
                'key': shell_key,
                'name': shell_name,
                'url': shell_url,
                'access': shell_access,
            })

        return {
            'visible_apps': visible_apps,
            'nav_groups': resolve_registry(get_access_row, shell_user_type),
            'secondary_pages': SECONDARY_PAGES,
            'platform_version': get_version('platform'),
        }

    # Daily analytics aggregation trigger
    @app.before_request
    def check_daily_analytics():
        """
        Check if daily analytics aggregation needs to run.

        The first visitor after midnight ET triggers a background job
        to aggregate yesterday's analytics data. This runs at most
        once per day and doesn't affect the user's request.
        """
        # Only check on HTML page requests (not API, static files, etc.)
        if request.endpoint and not request.path.startswith(('/api/', '/static/', '/favicon')):
            try:
                from justdata.shared.services.analytics_aggregator import check_and_trigger_aggregation
                check_and_trigger_aggregation()
            except Exception as e:
                # Don't let analytics check failures affect the request
                pass

    # Access restriction for non-privileged users
    @app.before_request
    def check_privileged_access():
        """
        Check if user has privileged access (staff, senior_executive, or admin).
        Non-privileged users see a restricted view with only header, footer, and NCRC logo.
        On the testing deploy, tester roles and the exact public paths also pass.
        """
        # Skip check for exempt paths (static files, health check, auth routes)
        path = request.path
        for exempt in EXEMPT_PATHS:
            if path.startswith(exempt):
                return None

        # Testing deploy only: tester roles, anyone on the exact public paths
        # (/, /about, /contact), and a signed-in public_registered user on
        # /apps. See main/auth/access_overlay.py.
        if testing_gate_admits(path, get_user_type(), signed_in=is_authenticated()):
            return None

        # Check if user is privileged
        if not is_privileged_user():
            # For API requests, return 403 JSON response
            if request.is_json or path.startswith('/api/'):
                return jsonify({
                    'error': 'Access restricted',
                    'message': 'This application is currently restricted to authorized staff only.',
                    'user_type': get_user_type()
                }), 403

            # For regular requests, render the restricted access page
            return render_template(
                'access_restricted.html',
                app_description='JustData - NCRC Data Analysis Platform',
            ), 200

        return None

    # Favicon route
    @app.route('/favicon.ico')
    def favicon():
        """Serve favicon from static folder."""
        return send_from_directory(
            MainConfig.STATIC_DIR,
            'favicon.png',
            mimetype='image/png'
        )

    # Shared JS files route
    @app.route('/shared/<path:filename>')
    def shared_files(filename):
        """Serve shared static files (JS modules, etc.)."""
        from pathlib import Path
        shared_js_dir = Path(MainConfig.STATIC_DIR) / 'js'
        if shared_js_dir.exists() and (shared_js_dir / filename).exists():
            return send_from_directory(str(shared_js_dir), filename)
        return '', 404

    # Main landing page route
    @app.route('/')
    def landing():
        """Public landing page (spec 02): what JustData is, what is in it,
        who it is for and where to go next. Facts come from
        main/landing_content.py; the roster renders from nav_groups.

        hero_cta picks the call to action:
          "apps"    staff, and tester roles on the testing deploy (can open apps)
          "request" signed in but without app access (public_registered)
          "signin"  signed out
        """
        from justdata.main.landing_content import DATA_INVENTORY, PLATFORM_STATS, count_words

        user_type = get_user_type()
        if is_privileged_user(user_type) or is_tester(user_type):
            hero_cta = 'apps'
        elif is_authenticated():
            hero_cta = 'request'
        else:
            hero_cta = 'signin'

        return render_template(
            'home.html',
            app_name='JustData',
            app_description=(
                'JustData turns federal mortgage, small business and branch records '
                'into analysis that holds up in a hearing, a newsroom or a negotiation.'
            ),
            data_inventory=DATA_INVENTORY,
            platform_stats=PLATFORM_STATS,
            hero_cta=hero_cta,
            count_words=count_words,
        )

    # App launcher: the ACCESS_MATRIX-driven grid that used to live on '/'.
    @app.route('/apps')
    def apps_index():
        """App launcher grid, grouped and gated by ACCESS_MATRIX.

        app_groups is built here (not in inject_shell(), which serves the
        nav sidebar's flat list) because this page needs per-app
        descriptions and a fixed group/heading structure the nav doesn't
        carry.
        """
        user_type = get_user_type()

        home_group_defs = [
            ('Reports', [
                ('lendsight', 'LendSight',
                 'Mortgage lending analysis with AI-generated narratives identifying disparities and compliance concerns.',
                 '/lendsight'),
                ('bizsight', 'BizSight',
                 'Small business lending patterns using CRA data with AI-powered gap analysis.',
                 '/bizsight'),
                ('branchsight', 'BranchSight',
                 'Bank branch network analysis tracking openings, closings, and market concentration.',
                 '/branchsight'),
            ]),
            ('Data tools', [
                ('branchmapper', 'BranchMapper',
                 'Interactive map of branch locations with demographic overlays and filters.',
                 '/branchmapper'),
                ('dataexplorer', 'DataExplorer',
                 'Query the full HMDA dataset with custom filters. Export raw data for your own analysis.',
                 '/dataexplorer'),
                ('mergermeter', 'MergerMeter',
                 'Bank merger impact analysis with CBA goal recommendations and peer comparisons.',
                 '/mergermeter'),
            ]),
            ('Staff tools', [
                ('analytics', 'Analytics',
                 'Monitor platform usage, report generation, and feature adoption.',
                 '/analytics'),
                ('admin', 'Administration',
                 'Manage user accounts, permissions, and system integrations.',
                 '/admin/users'),
            ]),
        ]

        app_groups = []
        for heading, group_apps in home_group_defs:
            visible = []
            for key, name, description, url in group_apps:
                access = get_app_access(key, user_type)
                if access == 'hidden':
                    continue
                visible.append({
                    'key': key,
                    'name': name,
                    'description': description,
                    'url': url,
                    'access': access,
                })
            if visible:
                app_groups.append({'heading': heading, 'apps': visible})

        return render_template(
            'apps.html',
            app_name='Apps',
            app_description='Launch a JustData tool.',
            app_groups=app_groups,
        )

    # About page route
    @app.route('/about')
    def about():
        """About page."""
        return render_template(
            'about.html',
            app_description=(
                "Learn about JustData, NCRC's comprehensive data analysis platform "
                "providing insights across banking, mortgage, small business, and "
                "member management."
            ),
        )

    # Contact page route
    @app.route('/contact')
    def contact():
        """Contact Us page."""
        return render_template(
            'contact.html',
            app_description=(
                'Contact JustData and the National Community Reinvestment Coalition '
                'for questions, support, or partnership opportunities.'
            ),
        )

    # Email verified landing page
    @app.route('/email-verified')
    def email_verified():
        """
        Landing page after user clicks email verification link.
        Firebase handles the actual verification - this page just
        prompts the user to refresh their session.
        """
        return render_template(
            'email_verified.html',
            app_description='Email verification confirmation for JustData',
        )

    # Register blueprints
    register_blueprints(app)
    
    # Register dashboard routes (after landing route to avoid conflicts)
    from justdata.shared.web.dashboard_routes import register_dashboard_routes
    register_dashboard_routes(app)
    
    # API endpoint to set user type (for testing/demo)
    @app.route('/api/set-user-type', methods=['POST'])
    @login_required
    @admin_required
    def api_set_user_type():
        """Set user type (admin only - prevents privilege escalation)."""
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
        apps = ['lendsight', 'branchsight', 'branchmapper', 'bizsight', 
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
        from justdata.shared.utils.versions import get_version
        return jsonify({
            'status': 'healthy',
            'app': 'justdata',
            'version': get_version('platform')
        })

    # Platform stats cache
    _stats_cache = {'data': None, 'timestamp': None}

    @app.route('/api/platform-stats')
    def api_platform_stats():
        """Get platform statistics for homepage display.

        Returns:
            - mortgage_records: Total HMDA records available
            - lenders_tracked: Unique lenders (LEIs) in HMDA data
            - reports_generated: Total report events from analytics
            - active_researchers: Unique users from analytics

        Results are cached for 1 hour.
        """
        from datetime import datetime, timedelta
        import time

        # Check cache (1 hour TTL); skip if ?refresh=1
        cache_ttl = 3600  # 1 hour in seconds
        now = time.time()
        skip_cache = request.args.get('refresh', '').strip() == '1'

        if not skip_cache and (_stats_cache['data'] is not None and
            _stats_cache['timestamp'] is not None and
            now - _stats_cache['timestamp'] < cache_ttl):
            return jsonify(_stats_cache['data'])

        include_debug = request.args.get('debug', '').strip() == '1'
        stats = {
            'mortgage_records': 0,
            'lenders_tracked': 0,
            'reports_generated': 0,
            'active_researchers': 0,
            'cached_at': datetime.utcnow().isoformat()
        }
        if include_debug:
            stats['_debug'] = {'client_ok': False, 'hmda_error': None, 'reports_error': None, 'firestore_error': None}

        try:
            from justdata.shared.utils.bigquery_client import get_bigquery_client
            # Use analytics service account for platform stats
            client = get_bigquery_client(project_id='justdata-ncrc', app_name='analytics')
            if include_debug:
                stats['_debug']['client_ok'] = client is not None
            if client:
                # Get mortgage records and lenders count from HMDA (2018+)
                try:
                    query = """
                        SELECT
                            COUNT(*) as total_records,
                            COUNT(DISTINCT lei) as unique_leis
                        FROM `justdata-ncrc.dataexplorer.de_hmda`
                        WHERE activity_year >= 2018
                    """
                    result = client.query(query).result()
                    for row in result:
                        stats['mortgage_records'] = row.total_records or 0
                        stats['lenders_tracked'] = row.unique_leis or 0
                        break
                except Exception as e:
                    print(f"[WARN] Failed to get HMDA stats: {e}")
                    if include_debug:
                        stats['_debug']['hmda_error'] = str(e)

                # Get reports count from analytics
                try:
                    query = """
                        SELECT COUNT(*) as total
                        FROM `justdata-ncrc.firebase_analytics.all_events`
                        WHERE event_name IN (
                            'lendsight_report', 'bizsight_report', 'branchsight_report',
                            'branchmapper_report', 'mergermeter_report',
                            'dataexplorer_area_report', 'dataexplorer_lender_report'
                        )
                    """
                    result = client.query(query).result()
                    for row in result:
                        stats['reports_generated'] = row.total or 0
                        break
                except Exception as e:
                    print(f"[WARN] Failed to get report count: {e}")
                    if include_debug:
                        stats['_debug']['reports_error'] = str(e)

                # Get unique researchers from Firestore (users who have logged in)
                try:
                    from justdata.main.auth import get_firestore_client
                    db = get_firestore_client()
                    if db:
                        users_ref = db.collection('users')
                        users = users_ref.stream()
                        active_count = sum(1 for u in users if u.to_dict().get('loginCount', 0) > 0)
                        stats['active_researchers'] = active_count
                except Exception as e:
                    print(f"[WARN] Failed to get active users from Firestore: {e}")
                    if include_debug:
                        stats['_debug']['firestore_error'] = str(e)

        except Exception as e:
            print(f"[WARN] Failed to connect to BigQuery: {e}")
            if include_debug:
                stats['_debug']['client_ok'] = False
                stats['_debug']['hmda_error'] = stats['_debug'].get('hmda_error') or str(e)

        # Update cache (don't cache debug payload)
        cache_payload = {k: v for k, v in stats.items() if k != '_debug'}
        _stats_cache['data'] = cache_payload
        _stats_cache['timestamp'] = now

        return jsonify(stats)

    # Admin Users Dashboard
    @app.route('/admin/users')
    @login_required
    @admin_required
    def admin_users():
        """Admin user management page - requires admin access."""
        from justdata.main.auth import VALID_USER_TYPES
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        from flask import url_for

        user_type = get_user_type()

        permissions = get_user_permissions(user_type)

        # Create Jinja2 environment with Flask's url_for function
        env = Environment(
            loader=FileSystemLoader(MainConfig.TEMPLATES_DIR),
            autoescape=select_autoescape(['html', 'xml'])
        )
        env.globals['url_for'] = url_for

        template = env.get_template('admin-users.html')
        # Raw Environment skips context processors, so pass the shell context
        # (nav_groups, secondary_pages, platform_version) explicitly.
        return template.render(
            user_type=user_type,
            permissions=permissions,
            valid_user_types=VALID_USER_TYPES,
            current_user=get_current_user(),
            **inject_shell()
        )

    return app


def register_blueprints(app: Flask):
    """Register all sub-application blueprints."""
    
    # Import and register blueprints
    # We'll create these in the next steps
    try:
        from justdata.apps.branchsight.blueprint import branchsight_bp
        app.register_blueprint(branchsight_bp, url_prefix='/branchsight')
    except ImportError:
        print("[WARN] BranchSight blueprint not yet created")
    
    try:
        from justdata.apps.bizsight.blueprint import bizsight_bp
        app.register_blueprint(bizsight_bp, url_prefix='/bizsight')
    except ImportError:
        print("[WARN] BizSight blueprint not yet created")
    
    try:
        from justdata.apps.lendsight.blueprint import lendsight_bp
        app.register_blueprint(lendsight_bp, url_prefix='/lendsight')
        print("[INFO] LendSight blueprint registered successfully")
    except Exception as e:
        import traceback
        print(f"[ERROR] Failed to load LendSight blueprint: {e}")
        traceback.print_exc()
    
    try:
        from justdata.apps.mergermeter.blueprint import mergermeter_bp
        app.register_blueprint(mergermeter_bp, url_prefix='/mergermeter')
    except ImportError:
        print("[WARN] MergerMeter blueprint not yet created")
    
    try:
        from justdata.apps.branchmapper.blueprint import branchmapper_bp
        app.register_blueprint(branchmapper_bp, url_prefix='/branchmapper')
    except ImportError:
        print("[WARN] BranchMapper blueprint not yet created")

    try:
        from justdata.apps.dotlender.blueprint import dotlender_bp
        app.register_blueprint(dotlender_bp, url_prefix='/dotlender')
    except ImportError:
        print("[WARN] DotLender blueprint not yet created")

    try:
        from justdata.apps.dataexplorer.blueprint import dataexplorer_bp
        app.register_blueprint(dataexplorer_bp, url_prefix='/dataexplorer')
    except ImportError:
        print("[WARN] DataExplorer blueprint not yet created")
    
    try:
        from justdata.apps.memberview.blueprint import memberview_bp
        app.register_blueprint(memberview_bp, url_prefix='/memberview')
    except ImportError:
        print("[WARN] MemberView blueprint not yet created")
    
    # Apps in development (from User Access Matrix)
    try:
        from justdata.apps.commentmaker.blueprint import commentmaker_bp
        app.register_blueprint(commentmaker_bp, url_prefix='/commentmaker')
    except ImportError:
        print("[WARN] CommentMaker blueprint not yet created (In Development)")
    
    try:
        from justdata.apps.justpolicy.blueprint import justpolicy_bp
        app.register_blueprint(justpolicy_bp, url_prefix='/justpolicy')
    except ImportError:
        print("[WARN] JustPolicy blueprint not yet created (In Development)")
    
    # Administrative tools
    try:
        from justdata.apps.analytics.blueprint import analytics_bp
        app.register_blueprint(analytics_bp, url_prefix='/analytics')
    except ImportError:
        print("[WARN] Analytics blueprint not yet created")

    # ElectWatch - archived 2026-08-31, source code retained under justdata/apps/electwatch/
    # for possible revival; blueprint intentionally not registered.

    # Redlining Dashboard - Staff/Admin fair lending analysis
    try:
        from justdata.apps.redlining.blueprint import redlining_bp
        app.register_blueprint(redlining_bp, url_prefix='/redlining')
        print("[INFO] Redlining blueprint registered at /redlining")
    except ImportError as e:
        print(f"[WARN] Redlining blueprint not yet created: {e}")

