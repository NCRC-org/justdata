"""
Access control system for JustData applications.
Implements user type-based access control based on the access matrix.
"""

from functools import wraps
from flask import session, redirect, url_for, request, jsonify
from typing import Optional, Literal

# User types
UserType = Literal['public', 'economy', 'member', 'partner', 'staff', 'developer']

# Access levels
AccessLevel = Literal['full', 'partial', 'locked', 'hidden']

# Access matrix matching the user access matrix
ACCESS_MATRIX = {
    'lendsight': {
        'public': 'partial',
        'economy': 'partial',
        'member': 'full',
        'partner': 'full',
        'staff': 'full',
        'developer': 'full'
    },
    'branchseeker': {
        'public': 'locked',
        'economy': 'partial',
        'member': 'full',
        'partner': 'full',
        'staff': 'full',
        'developer': 'full'
    },
    'branchmapper': {
        'public': 'locked',
        'economy': 'partial',
        'member': 'full',
        'partner': 'full',
        'staff': 'full',
        'developer': 'full'
    },
    'bizsight': {
        'public': 'locked',
        'economy': 'partial',
        'member': 'full',
        'partner': 'full',
        'staff': 'full',
        'developer': 'full'
    },
    'mergermeter': {
        'public': 'hidden',
        'economy': 'hidden',
        'member': 'hidden',
        'partner': 'hidden',
        'staff': 'full',
        'developer': 'full'
    },
    'memberview': {
        'public': 'hidden',
        'economy': 'hidden',
        'member': 'hidden',
        'partner': 'hidden',
        'staff': 'full',
        'developer': 'full'
    },
    'analytics': {
        'public': 'hidden',
        'economy': 'hidden',
        'member': 'hidden',
        'partner': 'hidden',
        'staff': 'full',
        'developer': 'full'
    },
    'admin': {
        'public': 'hidden',
        'economy': 'hidden',
        'member': 'hidden',
        'partner': 'hidden',
        'staff': 'hidden',
        'developer': 'full'
    },
    'dataexplorer': {
        'public': 'hidden',
        'economy': 'hidden',
        'member': 'full',
        'partner': 'full',
        'staff': 'full',
        'developer': 'full'
    },
    'lenderprofile': {
        'public': 'hidden',
        'economy': 'hidden',
        'member': 'full',
        'partner': 'full',
        'staff': 'full',
        'developer': 'full'
    },
    'loantrends': {
        'public': 'hidden',
        'economy': 'hidden',
        'member': 'full',
        'partner': 'full',
        'staff': 'full',
        'developer': 'full'
    }
}

# Feature permissions by user type
FEATURE_PERMISSIONS = {
    'public': {
        'geographic_limit': 'own_county_only',
        'can_export': False,
        'export_formats': []
    },
    'economy': {
        'geographic_limit': 'own_county_only',
        'can_export': False,
        'export_formats': []
    },
    'member': {
        'geographic_limit': 'multiple_counties',
        'can_export': True,
        'export_formats': ['excel', 'powerpoint', 'pdf']
    },
    'partner': {
        'geographic_limit': 'multiple_counties',
        'can_export': True,
        'export_formats': ['excel', 'powerpoint', 'pdf']
    },
    'staff': {
        'geographic_limit': 'unlimited',
        'can_export': True,
        'export_formats': ['excel', 'powerpoint', 'pdf', 'csv']
    },
    'developer': {
        'geographic_limit': 'unlimited',
        'can_export': True,
        'export_formats': ['excel', 'powerpoint', 'pdf', 'csv']
    }
}


def get_user_type() -> UserType:
    """
    Get current user type from session.
    Defaults to 'public' if not set.
    """
    return session.get('user_type', 'public')


def set_user_type(user_type: UserType):
    """Set user type in session."""
    if user_type in ['public', 'economy', 'member', 'partner', 'staff', 'developer']:
        session['user_type'] = user_type
        session.permanent = True
    else:
        raise ValueError(f"Invalid user type: {user_type}")


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
    required_hierarchy = {'hidden': 0, 'locked': 1, 'partial': 2, 'full': 3}
    
    return access_hierarchy.get(access_level, 0) >= required_hierarchy.get(required_level, 0)


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
                    return jsonify({'error': 'Access denied', 'required': required_level}), 403
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

