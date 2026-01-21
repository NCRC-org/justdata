"""
Access control system for JustData applications.
Implements user type-based access control based on the access matrix.
Integrates Firebase Authentication for user identity.

User Tiers (from pricing matrix):
- public: Free, no account required
- economy: Just Economy Club (Free)
- member: NCRC Member ($900/yr)
- member_plus: Member Plus tier ($500-750/yr add-on)
- institutional: Institutional tier ($5K-15K/yr)
- staff: NCRC Staff (Free)
- admin: Administrator (Free)

Access Levels:
- full: Full access to all features
- partial/limited: Can view reports, limited geography, no exports
- locked: Visible but requires membership upgrade
- hidden: Not visible to user type
"""

import os
import json
from functools import wraps
from flask import session, redirect, url_for, request, jsonify, g
from typing import Optional, Literal, Dict, List

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

# ========================================
# Firebase Initialization
# ========================================

_firebase_app = None

def init_firebase():
    """Initialize Firebase Admin SDK using credentials from environment."""
    global _firebase_app

    if _firebase_app is not None:
        return _firebase_app

    # Check if already initialized
    try:
        _firebase_app = firebase_admin.get_app()
        return _firebase_app
    except ValueError:
        pass  # Not initialized yet

    # Get credentials from environment
    creds_path = os.environ.get('FIREBASE_CREDENTIALS')
    creds_json = os.environ.get('FIREBASE_CREDENTIALS_JSON')

    if creds_path and os.path.exists(creds_path):
        # Load from file path
        cred = credentials.Certificate(creds_path)
    elif creds_json:
        # Load from JSON string (for cloud deployments)
        cred_dict = json.loads(creds_json)
        cred = credentials.Certificate(cred_dict)
    else:
        print("Warning: Firebase credentials not found. Authentication disabled.")
        return None

    _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def get_firebase_app():
    """Get or initialize Firebase app."""
    global _firebase_app
    if _firebase_app is None:
        init_firebase()
    return _firebase_app


# ========================================
# Firebase User Authentication
# ========================================

def verify_firebase_token(id_token: str) -> Optional[dict]:
    """
    Verify a Firebase ID token and return the decoded token.

    Args:
        id_token: The Firebase ID token from the client

    Returns:
        Decoded token dict with user info, or None if invalid
    """
    if not get_firebase_app():
        return None

    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        return decoded_token
    except firebase_auth.InvalidIdTokenError:
        return None
    except firebase_auth.ExpiredIdTokenError:
        return None
    except Exception as e:
        print(f"Firebase token verification error: {e}")
        return None


def get_current_user() -> Optional[dict]:
    """
    Get the current authenticated user from the request.
    Checks Authorization header for Bearer token or session.

    Returns:
        User dict with uid, email, name, etc. or None if not authenticated
    """
    # Check if already loaded in request context
    if hasattr(g, 'current_user'):
        return g.current_user

    user = None

    # Check Authorization header first (API calls)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        id_token = auth_header[7:]  # Remove 'Bearer ' prefix
        decoded = verify_firebase_token(id_token)
        if decoded:
            user = {
                'uid': decoded.get('uid'),
                'email': decoded.get('email'),
                'name': decoded.get('name', decoded.get('email', '').split('@')[0]),
                'picture': decoded.get('picture'),
                'email_verified': decoded.get('email_verified', False),
                'provider': decoded.get('firebase', {}).get('sign_in_provider', 'unknown')
            }

    # Fall back to session-stored user
    if not user and 'firebase_user' in session:
        user = session['firebase_user']

    g.current_user = user
    return user


def set_session_user(user_data: dict):
    """Store user data in session after frontend authentication."""
    session['firebase_user'] = user_data
    session.permanent = True


def clear_session_user():
    """Clear user data from session on logout."""
    session.pop('firebase_user', None)
    session.pop('user_type', None)


def is_authenticated() -> bool:
    """Check if current request has an authenticated user."""
    return get_current_user() is not None


# ========================================
# Authentication Decorators
# ========================================

def login_required(f):
    """
    Decorator to require Firebase authentication for a route.

    Usage:
        @app.route('/protected')
        @login_required
        def protected_route():
            user = get_current_user()
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'auth_required'
                }), 401
            # Redirect to landing page for HTML requests
            return redirect(url_for('landing'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to require admin user type.

    Usage:
        @app.route('/admin')
        @admin_required
        def admin_route():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'auth_required'
                }), 401
            return redirect(url_for('landing'))

        user_type = get_user_type()
        if user_type != 'admin':
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Admin access required',
                    'code': 'admin_required',
                    'user_type': user_type
                }), 403
            return redirect(url_for('landing'))

        return f(*args, **kwargs)
    return decorated_function


def staff_required(f):
    """
    Decorator to require staff or admin user type.

    Usage:
        @app.route('/internal')
        @staff_required
        def internal_route():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'auth_required'
                }), 401
            return redirect(url_for('landing'))

        user_type = get_user_type()
        if user_type not in ('staff', 'admin'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Staff access required',
                    'code': 'staff_required',
                    'user_type': user_type
                }), 403
            return redirect(url_for('landing'))

        return f(*args, **kwargs)
    return decorated_function

# User types matching the pricing tiers
UserType = Literal['public', 'economy', 'member', 'member_plus', 'institutional', 'staff', 'admin']

# Access levels
AccessLevel = Literal['full', 'partial', 'locked', 'hidden']

# Valid user types list for validation
VALID_USER_TYPES = ['public', 'economy', 'member', 'member_plus', 'institutional', 'staff', 'admin']

# Access matrix matching the User Access Matrix
# Format: app_name: {user_type: access_level}
ACCESS_MATRIX = {
    # ========================================
    # AI-Driven Reports
    # ========================================
    'lendsight': {
        'public': 'partial',      # Limited - own county only, view-only, no exports
        'economy': 'partial',     # Limited - own county only, view-only, no exports
        'member': 'full',
        'member_plus': 'full',
        'institutional': 'full',
        'staff': 'full',
        'admin': 'full'
    },
    'branchseeker': {
        'public': 'locked',       # Visible but requires membership
        'economy': 'locked',
        'member': 'full',
        'member_plus': 'full',
        'institutional': 'full',
        'staff': 'full',
        'admin': 'full'
    },
    'branchsight': {
        'public': 'locked',       # Visible but requires membership
        'economy': 'locked',
        'member': 'full',
        'member_plus': 'full',
        'institutional': 'full',
        'staff': 'full',
        'admin': 'full'
    },
    'bizsight': {
        'public': 'locked',
        'economy': 'locked',
        'member': 'full',
        'member_plus': 'full',
        'institutional': 'full',
        'staff': 'full',
        'admin': 'full'
    },
    'commentmaker': {
        # In Development - available to all users when released
        'public': 'full',
        'economy': 'full',
        'member': 'full',
        'member_plus': 'full',
        'institutional': 'full',
        'staff': 'full',
        'admin': 'full'
    },
    'justpolicy': {
        # In Development - available to all users when released
        'public': 'full',
        'economy': 'full',
        'member': 'full',
        'member_plus': 'full',
        'institutional': 'full',
        'staff': 'full',
        'admin': 'full'
    },
    'lenderprofile': {
        'public': 'hidden',
        'economy': 'hidden',
        'member': 'hidden',
        'member_plus': 'hidden',
        'institutional': 'hidden',
        'staff': 'full',
        'admin': 'full'
    },
    'mergermeter': {
        'public': 'hidden',
        'economy': 'hidden',
        'member': 'hidden',
        'member_plus': 'hidden',
        'institutional': 'hidden',
        'staff': 'full',
        'admin': 'full'
    },
    
    # ========================================
    # Interactive Tools
    # ========================================
    'branchmapper': {
        'public': 'locked',
        'economy': 'locked',
        'member': 'full',
        'member_plus': 'full',
        'institutional': 'full',
        'staff': 'full',
        'admin': 'full'
    },
    'dataexplorer': {
        'public': 'locked',
        'economy': 'locked',
        'member': 'locked',        # Requires Member Plus add-on
        'member_plus': 'full',     # Full** - includes enhanced features
        'institutional': 'full',
        'staff': 'full',
        'admin': 'full'
    },
    
    # ========================================
    # Administrative
    # ========================================
    'analytics': {
        'public': 'hidden',
        'economy': 'hidden',
        'member': 'hidden',
        'member_plus': 'hidden',
        'institutional': 'hidden',
        'staff': 'full',
        'admin': 'full'
    },
    'admin': {
        'public': 'hidden',
        'economy': 'hidden',
        'member': 'hidden',
        'member_plus': 'hidden',
        'institutional': 'hidden',
        'staff': 'hidden',
        'admin': 'full'
    },
    
    # ========================================
    # Internal/Staff Tools (not in public matrix)
    # ========================================
    'loantrends': {
        'public': 'hidden',
        'economy': 'hidden',
        'member': 'hidden',
        'member_plus': 'hidden',
        'institutional': 'hidden',
        'staff': 'full',
        'admin': 'full'
    },
    'memberview': {
        'public': 'hidden',
        'economy': 'hidden',
        'member': 'hidden',
        'member_plus': 'hidden',
        'institutional': 'hidden',
        'staff': 'full',
        'admin': 'full'
    }
}

# Feature permissions by user type (for granular control)
FEATURE_PERMISSIONS = {
    'public': {
        'geographic_limit': 'own_county_only',
        'max_counties': 1,
        'can_export': False,
        'export_formats': [],
        'ai_reports': False,
        'description': 'Free access - view-only, single county'
    },
    'economy': {
        'geographic_limit': 'own_county_only',
        'max_counties': 1,
        'can_export': False,
        'export_formats': [],
        'ai_reports': False,
        'description': 'Just Economy Club - free tier with limited access'
    },
    'member': {
        'geographic_limit': 'multiple_counties',
        'max_counties': 3,  # Up to 3 counties/metro areas
        'can_export': True,
        'export_formats': ['excel', 'pdf', 'powerpoint'],
        'ai_reports': True,
        'description': 'NCRC Member - $900/yr, full access to most apps'
    },
    'member_plus': {
        'geographic_limit': 'multiple_counties',
        'max_counties': None,  # 5+ counties or unlimited
        'can_export': True,
        'export_formats': ['excel', 'pdf', 'powerpoint', 'csv'],
        'ai_reports': True,
        'dataexplorer_enhanced': True,  # Advanced filtering, bulk exports, custom reports, historical data
        'description': 'Member Plus - $500-750/yr add-on, unlocks DataExplorer with enhanced features'
    },
    'institutional': {
        'geographic_limit': 'unlimited',
        'max_counties': None,
        'can_export': True,
        'export_formats': ['excel', 'pdf', 'powerpoint', 'csv'],
        'ai_reports': True,
        'dataexplorer_enhanced': True,
        'description': 'Institutional - $5K-15K/yr, unlimited geography, CSV exports'
    },
    'staff': {
        'geographic_limit': 'unlimited',
        'max_counties': None,
        'can_export': True,
        'export_formats': ['excel', 'pdf', 'powerpoint', 'csv', 'json'],
        'ai_reports': True,
        'dataexplorer_enhanced': True,
        'internal_tools': True,
        'description': 'NCRC Staff - full access to all features and formats'
    },
    'admin': {
        'geographic_limit': 'unlimited',
        'max_counties': None,
        'can_export': True,
        'export_formats': ['excel', 'pdf', 'powerpoint', 'csv', 'json'],
        'ai_reports': True,
        'dataexplorer_enhanced': True,
        'internal_tools': True,
        'admin_access': True,
        'description': 'Administrator - full access including administration panel'
    }
}

# Tier pricing information (for reference/display)
TIER_PRICING = {
    'public': {'price': 0, 'billing': 'free', 'label': 'Public'},
    'economy': {'price': 0, 'billing': 'free', 'label': 'Just Economy Club'},
    'member': {'price': 900, 'billing': 'yearly', 'label': 'Member'},
    'member_plus': {'price_range': (500, 750), 'billing': 'yearly', 'label': 'Member Plus', 'addon': True},
    'institutional': {'price_range': (5000, 15000), 'billing': 'yearly', 'label': 'Institutional'},
    'staff': {'price': 0, 'billing': 'free', 'label': 'Staff', 'internal': True},
    'admin': {'price': 0, 'billing': 'free', 'label': 'Admin', 'internal': True}
}


def get_user_type() -> UserType:
    """
    Get current user type from session.
    For authenticated users, defaults to 'public' (free tier).
    For development/testing, defaults to 'staff' if not authenticated.
    """
    # If user_type is explicitly set in session, use that
    if 'user_type' in session:
        return session['user_type']

    # If user is authenticated but no tier set, default to public
    if is_authenticated():
        return 'public'

    # For development: default to staff for unauthenticated users
    # In production, this should return 'public'
    return 'staff'


def set_user_type(user_type: UserType):
    """Set user type in session."""
    if user_type in VALID_USER_TYPES:
        session['user_type'] = user_type
        session.permanent = True
    else:
        raise ValueError(f"Invalid user type: {user_type}. Valid types: {VALID_USER_TYPES}")


def get_app_access(app_name: str, user_type: Optional[UserType] = None) -> AccessLevel:
    """
    Get access level for an app based on user type.
    
    Args:
        app_name: Name of the application (lowercase)
        user_type: User type (defaults to current session user type)
    
    Returns:
        Access level: 'full', 'partial', 'locked', or 'hidden'
    """
    if user_type is None:
        user_type = get_user_type()
    
    app_name = app_name.lower()
    return ACCESS_MATRIX.get(app_name, {}).get(user_type, 'hidden')


def has_access(app_name: str, required_level: AccessLevel = 'full', 
               user_type: Optional[UserType] = None) -> bool:
    """
    Check if user has required access level for an app.
    
    Args:
        app_name: Name of the application
        required_level: Minimum required access level
        user_type: User type (defaults to current session user type)
    
    Returns:
        True if user has access, False otherwise
    """
    access_level = get_app_access(app_name, user_type)
    
    # Access hierarchy: hidden < locked < partial < full
    access_hierarchy = {'hidden': 0, 'locked': 1, 'partial': 2, 'full': 3}
    
    return access_hierarchy.get(access_level, 0) >= access_hierarchy.get(required_level, 0)


def require_access(app_name: str, required_level: AccessLevel = 'partial'):
    """
    Decorator to require access level for a route.
    
    Usage:
        @app.route('/some-route')
        @require_access('bizsight', 'full')
        def some_route():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not has_access(app_name, required_level):
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({
                        'error': 'Access denied',
                        'required_level': required_level,
                        'user_type': get_user_type(),
                        'app': app_name
                    }), 403
                # Redirect to landing page with message
                return redirect(url_for('landing'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_user_permissions(user_type: Optional[UserType] = None) -> dict:
    """
    Get feature permissions for a user type.
    
    Args:
        user_type: User type (defaults to current session user type)
    
    Returns:
        Dictionary with permission details
    """
    if user_type is None:
        user_type = get_user_type()
    
    return FEATURE_PERMISSIONS.get(user_type, FEATURE_PERMISSIONS['public']).copy()


def is_app_visible(app_name: str, user_type: Optional[UserType] = None) -> bool:
    """
    Check if an app should be visible to a user type.
    
    Args:
        app_name: Name of the application
        user_type: User type (defaults to current session user type)
    
    Returns:
        True if app should be visible, False if hidden
    """
    access_level = get_app_access(app_name, user_type)
    return access_level != 'hidden'


def get_visible_apps(user_type: Optional[UserType] = None) -> List[str]:
    """
    Get list of apps visible to a user type.
    
    Args:
        user_type: User type (defaults to current session user type)
    
    Returns:
        List of visible app names
    """
    if user_type is None:
        user_type = get_user_type()
    
    return [app for app in ACCESS_MATRIX.keys() if is_app_visible(app, user_type)]


def get_apps_by_access_level(access_level: AccessLevel, user_type: Optional[UserType] = None) -> List[str]:
    """
    Get list of apps with a specific access level for a user type.
    
    Args:
        access_level: The access level to filter by
        user_type: User type (defaults to current session user type)
    
    Returns:
        List of app names with the specified access level
    """
    if user_type is None:
        user_type = get_user_type()
    
    return [app for app, levels in ACCESS_MATRIX.items() 
            if levels.get(user_type) == access_level]


def get_tier_info(user_type: Optional[UserType] = None) -> dict:
    """
    Get pricing and tier information for a user type.
    
    Args:
        user_type: User type (defaults to current session user type)
    
    Returns:
        Dictionary with tier pricing info
    """
    if user_type is None:
        user_type = get_user_type()
    
    return TIER_PRICING.get(user_type, TIER_PRICING['public']).copy()


def get_access_matrix_for_display() -> Dict[str, Dict[str, AccessLevel]]:
    """
    Get the full access matrix for display purposes (e.g., in admin panel).
    
    Returns:
        The complete ACCESS_MATRIX dictionary
    """
    return ACCESS_MATRIX.copy()


def can_export(user_type: Optional[UserType] = None) -> bool:
    """Check if user type can export reports."""
    permissions = get_user_permissions(user_type)
    return permissions.get('can_export', False)


def get_export_formats(user_type: Optional[UserType] = None) -> List[str]:
    """Get available export formats for user type."""
    permissions = get_user_permissions(user_type)
    return permissions.get('export_formats', [])


def get_geographic_limit(user_type: Optional[UserType] = None) -> str:
    """Get geographic limit for user type."""
    permissions = get_user_permissions(user_type)
    return permissions.get('geographic_limit', 'own_county_only')


def get_max_counties(user_type: Optional[UserType] = None) -> Optional[int]:
    """Get maximum counties allowed for user type (None = unlimited)."""
    permissions = get_user_permissions(user_type)
    return permissions.get('max_counties', 1)


# ========================================
# Authentication API Blueprint
# ========================================

from flask import Blueprint

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/status', methods=['GET'])
def auth_status():
    """
    Get current authentication status and user info.

    Returns:
        JSON with authenticated status, user info, and permissions
    """
    user = get_current_user()
    user_type = get_user_type()
    permissions = get_user_permissions(user_type)

    return jsonify({
        'authenticated': user is not None,
        'user': user,
        'user_type': user_type,
        'permissions': permissions,
        'visible_apps': get_visible_apps(user_type),
        'tier_info': get_tier_info(user_type)
    })


@auth_bp.route('/login', methods=['POST'])
def auth_login():
    """
    Store user session after Firebase frontend authentication.
    Called by frontend after successful Firebase sign-in.

    Request body:
        {
            "idToken": "firebase_id_token",
            "user": {
                "uid": "...",
                "email": "...",
                "displayName": "...",
                "photoURL": "..."
            }
        }

    Returns:
        JSON with success status and user type
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    id_token = data.get('idToken')
    user_data = data.get('user', {})

    if not id_token:
        return jsonify({'error': 'No ID token provided'}), 400

    # Verify the token
    decoded = verify_firebase_token(id_token)
    if not decoded:
        return jsonify({'error': 'Invalid or expired token'}), 401

    # Store user in session
    user = {
        'uid': decoded.get('uid'),
        'email': decoded.get('email'),
        'name': user_data.get('displayName', decoded.get('name', '')),
        'picture': user_data.get('photoURL', decoded.get('picture')),
        'email_verified': decoded.get('email_verified', False),
        'provider': decoded.get('firebase', {}).get('sign_in_provider', 'unknown')
    }
    set_session_user(user)

    # Get or set user type (could look up from database in future)
    user_type = get_user_type()

    return jsonify({
        'success': True,
        'user': user,
        'user_type': user_type,
        'permissions': get_user_permissions(user_type)
    })


@auth_bp.route('/logout', methods=['POST'])
def auth_logout():
    """
    Clear user session on logout.

    Returns:
        JSON with success status
    """
    clear_session_user()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })


@auth_bp.route('/set-user-type', methods=['POST'])
def set_user_type_endpoint():
    """
    Set user type in session (for tier selection).

    Request body:
        {"user_type": "member"}

    Returns:
        JSON with success status and updated permissions
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    requested_type = data.get('user_type')
    if requested_type not in VALID_USER_TYPES:
        return jsonify({
            'error': f'Invalid user type: {requested_type}',
            'valid_types': VALID_USER_TYPES
        }), 400

    set_user_type(requested_type)

    return jsonify({
        'success': True,
        'user_type': requested_type,
        'permissions': get_user_permissions(requested_type),
        'visible_apps': get_visible_apps(requested_type)
    })
