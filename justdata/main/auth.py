"""
Access control system for JustData applications.
Implements user type-based access control based on the access matrix.

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

from functools import wraps
from flask import session, redirect, url_for, request, jsonify
from typing import Optional, Literal, Dict, List

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
    Defaults to 'public' if not set.
    """
    return session.get('user_type', 'public')


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
