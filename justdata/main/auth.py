"""
Access control system for JustData applications.
Implements user type-based access control based on the access matrix.
Integrates Firebase Authentication and Firestore for user management.

User Types (8 tiers):
- public_anonymous: No account, not logged in
- public_registered: Google sign-in, basic access
- just_economy_club: Free tier with limited features
- member: NCRC Member ($900/yr)
- member_premium: Member Plus tier
- non_member_org: Institutional/organizational access
- staff: NCRC Staff (@ncrc.org domain)
- admin: Administrator

Access Levels:
- full: Full access to all features
- limited: Can view reports, limited geography, no exports
- locked: Visible but requires membership upgrade
- hidden: Not visible to user type
"""

import os
import json
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, request, jsonify, g
from typing import Optional, Literal, Dict, List

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth, firestore

# ========================================
# Constants
# ========================================

# Admin users (seeded with admin access)
ADMIN_EMAILS = [
    'jrichardson@ncrc.org',
    'jedlebi@ncrc.org'
]

# User types matching the 8-tier system
UserType = Literal[
    'public_anonymous',
    'public_registered',
    'just_economy_club',
    'member',
    'member_premium',
    'non_member_org',
    'staff',
    'admin'
]

# Access levels
AccessLevel = Literal['full', 'limited', 'locked', 'hidden']

# Valid user types list for validation
VALID_USER_TYPES = [
    'public_anonymous',
    'public_registered',
    'just_economy_club',
    'member',
    'member_premium',
    'non_member_org',
    'staff',
    'admin'
]

# Access matrix matching the User Access Matrix
# Format: app_name: {user_type: access_level}
ACCESS_MATRIX = {
    # ========================================
    # AI-Driven Reports
    # ========================================
    'lendsight': {
        'public_anonymous': 'locked',
        'public_registered': 'limited',
        'just_economy_club': 'limited',
        'member': 'full',
        'member_premium': 'full',
        'non_member_org': 'full',
        'staff': 'full',
        'admin': 'full'
    },
    'branchseeker': {
        'public_anonymous': 'locked',
        'public_registered': 'locked',
        'just_economy_club': 'limited',
        'member': 'full',
        'member_premium': 'full',
        'non_member_org': 'full',
        'staff': 'full',
        'admin': 'full'
    },
    'branchsight': {
        'public_anonymous': 'locked',
        'public_registered': 'locked',
        'just_economy_club': 'limited',
        'member': 'full',
        'member_premium': 'full',
        'non_member_org': 'full',
        'staff': 'full',
        'admin': 'full'
    },
    'bizsight': {
        'public_anonymous': 'locked',
        'public_registered': 'locked',
        'just_economy_club': 'limited',
        'member': 'full',
        'member_premium': 'full',
        'non_member_org': 'full',
        'staff': 'full',
        'admin': 'full'
    },
    'commentmaker': {
        'public_anonymous': 'full',
        'public_registered': 'full',
        'just_economy_club': 'full',
        'member': 'full',
        'member_premium': 'full',
        'non_member_org': 'full',
        'staff': 'full',
        'admin': 'full'
    },
    'justpolicy': {
        'public_anonymous': 'full',
        'public_registered': 'full',
        'just_economy_club': 'full',
        'member': 'full',
        'member_premium': 'full',
        'non_member_org': 'full',
        'staff': 'full',
        'admin': 'full'
    },
    'lenderprofile': {
        'public_anonymous': 'hidden',
        'public_registered': 'hidden',
        'just_economy_club': 'hidden',
        'member': 'hidden',
        'member_premium': 'hidden',
        'non_member_org': 'hidden',
        'staff': 'full',
        'admin': 'full'
    },
    'mergermeter': {
        'public_anonymous': 'hidden',
        'public_registered': 'hidden',
        'just_economy_club': 'hidden',
        'member': 'hidden',
        'member_premium': 'hidden',
        'non_member_org': 'hidden',
        'staff': 'full',
        'admin': 'full'
    },
    'electwatch': {
        'public_anonymous': 'hidden',
        'public_registered': 'hidden',
        'just_economy_club': 'hidden',
        'member': 'hidden',
        'member_premium': 'hidden',
        'non_member_org': 'hidden',
        'staff': 'full',
        'admin': 'full'
    },

    # ========================================
    # Interactive Tools
    # ========================================
    'branchmapper': {
        'public_anonymous': 'locked',
        'public_registered': 'locked',
        'just_economy_club': 'locked',
        'member': 'full',
        'member_premium': 'full',
        'non_member_org': 'full',
        'staff': 'full',
        'admin': 'full'
    },
    'dataexplorer': {
        'public_anonymous': 'locked',
        'public_registered': 'locked',
        'just_economy_club': 'locked',
        'member': 'locked',
        'member_premium': 'full',
        'non_member_org': 'full',
        'staff': 'full',
        'admin': 'full'
    },

    # ========================================
    # Administrative
    # ========================================
    'analytics': {
        'public_anonymous': 'hidden',
        'public_registered': 'hidden',
        'just_economy_club': 'hidden',
        'member': 'hidden',
        'member_premium': 'hidden',
        'non_member_org': 'hidden',
        'staff': 'full',
        'admin': 'full'
    },
    'admin': {
        'public_anonymous': 'hidden',
        'public_registered': 'hidden',
        'just_economy_club': 'hidden',
        'member': 'hidden',
        'member_premium': 'hidden',
        'non_member_org': 'hidden',
        'staff': 'hidden',
        'admin': 'full'
    },
    'administration': {
        'public_anonymous': 'hidden',
        'public_registered': 'hidden',
        'just_economy_club': 'hidden',
        'member': 'hidden',
        'member_premium': 'hidden',
        'non_member_org': 'hidden',
        'staff': 'hidden',
        'admin': 'full'
    },

    # ========================================
    # Internal/Staff Tools
    # ========================================
    'loantrends': {
        'public_anonymous': 'hidden',
        'public_registered': 'hidden',
        'just_economy_club': 'hidden',
        'member': 'hidden',
        'member_premium': 'hidden',
        'non_member_org': 'hidden',
        'staff': 'full',
        'admin': 'full'
    },
    'memberview': {
        'public_anonymous': 'hidden',
        'public_registered': 'hidden',
        'just_economy_club': 'hidden',
        'member': 'hidden',
        'member_premium': 'hidden',
        'non_member_org': 'hidden',
        'staff': 'full',
        'admin': 'full'
    }
}

# Feature permissions by user type
FEATURE_PERMISSIONS = {
    'public_anonymous': {
        'geographic_limit': 'none',
        'max_counties': 0,
        'can_export': False,
        'export_formats': [],
        'ai_reports': False,
        'description': 'Not logged in - limited access'
    },
    'public_registered': {
        'geographic_limit': 'own_county_only',
        'max_counties': 1,
        'can_export': False,
        'export_formats': [],
        'ai_reports': False,
        'description': 'Registered user - limited to own county'
    },
    'just_economy_club': {
        'geographic_limit': 'own_county_only',
        'max_counties': 1,
        'can_export': False,
        'export_formats': [],
        'ai_reports': False,
        'description': 'Just Economy Club - free tier with limited access'
    },
    'member': {
        'geographic_limit': 'multiple_counties',
        'max_counties': 3,
        'can_export': True,
        'export_formats': ['excel', 'pdf', 'powerpoint'],
        'ai_reports': True,
        'description': 'NCRC Member - $900/yr, full access to most apps'
    },
    'member_premium': {
        'geographic_limit': 'multiple_counties',
        'max_counties': None,
        'can_export': True,
        'export_formats': ['excel', 'pdf', 'powerpoint', 'csv'],
        'ai_reports': True,
        'dataexplorer_enhanced': True,
        'description': 'Member Premium - enhanced features and DataExplorer access'
    },
    'non_member_org': {
        'geographic_limit': 'unlimited',
        'max_counties': None,
        'can_export': True,
        'export_formats': ['excel', 'pdf', 'powerpoint', 'csv'],
        'ai_reports': True,
        'dataexplorer_enhanced': True,
        'description': 'Institutional - unlimited geography, full exports'
    },
    'staff': {
        'geographic_limit': 'unlimited',
        'max_counties': None,
        'can_export': True,
        'export_formats': ['excel', 'pdf', 'powerpoint', 'csv', 'json'],
        'ai_reports': True,
        'dataexplorer_enhanced': True,
        'internal_tools': True,
        'description': 'NCRC Staff - full access to all features'
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
        'description': 'Administrator - full access including administration'
    }
}

# Tier pricing information
TIER_PRICING = {
    'public_anonymous': {'price': 0, 'billing': 'free', 'label': 'Guest'},
    'public_registered': {'price': 0, 'billing': 'free', 'label': 'Registered'},
    'just_economy_club': {'price': 0, 'billing': 'free', 'label': 'Just Economy Club'},
    'member': {'price': 900, 'billing': 'yearly', 'label': 'Member'},
    'member_premium': {'price_range': (500, 750), 'billing': 'yearly', 'label': 'Member Premium', 'addon': True},
    'non_member_org': {'price_range': (5000, 15000), 'billing': 'yearly', 'label': 'Institutional'},
    'staff': {'price': 0, 'billing': 'free', 'label': 'Staff', 'internal': True},
    'admin': {'price': 0, 'billing': 'free', 'label': 'Admin', 'internal': True}
}


# ========================================
# Firebase Initialization
# ========================================

_firebase_app = None
_firestore_client = None


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
        cred = credentials.Certificate(creds_path)
    elif creds_json:
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


def get_firestore_client():
    """Get or initialize Firestore client."""
    global _firestore_client
    if _firestore_client is None:
        if get_firebase_app():
            _firestore_client = firestore.client()
    return _firestore_client


# ========================================
# Firestore User Management
# ========================================

def get_user_doc(uid: str) -> Optional[dict]:
    """
    Get user document from Firestore.

    Args:
        uid: Firebase Auth UID

    Returns:
        User document dict or None if not found
    """
    db = get_firestore_client()
    if not db:
        return None

    try:
        doc = db.collection('users').document(uid).get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"Error getting user doc: {e}")
        return None


def create_or_update_user_doc(uid: str, email: str, display_name: str = None,
                               photo_url: str = None, email_verified: bool = False) -> dict:
    """
    Create or update user document in Firestore.

    Args:
        uid: Firebase Auth UID
        email: User's email address
        display_name: User's display name
        photo_url: User's profile photo URL
        email_verified: Whether email is verified

    Returns:
        The user document dict
    """
    db = get_firestore_client()
    if not db:
        # Return a default user dict if Firestore is unavailable
        return {
            'uid': uid,
            'email': email,
            'displayName': display_name,
            'userType': determine_user_type(email, email_verified),
            'emailVerified': email_verified
        }

    try:
        user_ref = db.collection('users').document(uid)
        doc = user_ref.get()

        now = datetime.utcnow()

        if doc.exists:
            # Update existing user
            user_data = doc.to_dict()
            update_data = {
                'lastLoginAt': now,
                'loginCount': (user_data.get('loginCount', 0) or 0) + 1,
                'emailVerified': email_verified
            }

            # Update display name and photo if provided
            if display_name:
                update_data['displayName'] = display_name
            if photo_url:
                update_data['photoURL'] = photo_url

            # Check if user type should be upgraded (e.g., @ncrc.org verified)
            current_type = user_data.get('userType', 'public_registered')
            new_type = determine_user_type(email, email_verified, current_type)
            if new_type != current_type:
                update_data['userType'] = new_type

            user_ref.update(update_data)

            # Return merged data
            user_data.update(update_data)
            return user_data
        else:
            # Create new user
            user_type = determine_user_type(email, email_verified)
            user_data = {
                'uid': uid,
                'email': email,
                'displayName': display_name or email.split('@')[0],
                'photoURL': photo_url,
                'userType': user_type,
                'organization': None,
                'jobTitle': None,
                'county': None,
                'emailVerified': email_verified,
                'createdAt': now,
                'lastLoginAt': now,
                'loginCount': 1
            }
            user_ref.set(user_data)

            # Log registration activity
            log_activity(uid, email, 'registration', metadata={'userType': user_type})

            return user_data

    except Exception as e:
        print(f"Error creating/updating user doc: {e}")
        return {
            'uid': uid,
            'email': email,
            'displayName': display_name,
            'userType': determine_user_type(email, email_verified),
            'emailVerified': email_verified
        }


def determine_user_type(email: str, email_verified: bool = False,
                         current_type: str = None) -> UserType:
    """
    Determine user type based on email and verification status.

    Args:
        email: User's email address
        email_verified: Whether email is verified
        current_type: Current user type (if upgrading)

    Returns:
        Appropriate user type
    """
    if not email:
        return 'public_anonymous'

    email_lower = email.lower()

    # Check admin list first
    if email_lower in [e.lower() for e in ADMIN_EMAILS]:
        return 'admin'

    # Check NCRC domain
    if email_lower.endswith('@ncrc.org'):
        # Verified NCRC emails get staff access
        if email_verified:
            return 'staff'
        # Unverified NCRC emails still get staff (they signed in with Google)
        return 'staff'

    # If current type is set by admin, don't downgrade
    if current_type and current_type in ['member', 'member_premium', 'non_member_org',
                                          'just_economy_club', 'staff', 'admin']:
        return current_type

    # Default to public_registered for authenticated users
    return 'public_registered'


def update_user_type(uid: str, user_type: UserType) -> bool:
    """
    Update a user's type in Firestore (admin function).

    Args:
        uid: Firebase Auth UID
        user_type: New user type

    Returns:
        True if successful, False otherwise
    """
    if user_type not in VALID_USER_TYPES:
        return False

    db = get_firestore_client()
    if not db:
        return False

    try:
        db.collection('users').document(uid).update({
            'userType': user_type,
            'userTypeUpdatedAt': datetime.utcnow()
        })
        return True
    except Exception as e:
        print(f"Error updating user type: {e}")
        return False


def log_activity(uid: str, email: str, action: str, app: str = None,
                 county: str = None, metadata: dict = None):
    """
    Log user activity to Firestore for analytics.

    Args:
        uid: Firebase Auth UID
        email: User's email
        action: Action type ('login', 'report_generated', 'export', etc.)
        app: Application name (optional)
        county: County/geography (optional)
        metadata: Additional context (optional)
    """
    db = get_firestore_client()
    if not db:
        return

    try:
        activity_data = {
            'uid': uid,
            'email': email,
            'action': action,
            'app': app,
            'county': county,
            'metadata': metadata or {},
            'timestamp': datetime.utcnow()
        }
        db.collection('activity').add(activity_data)
    except Exception as e:
        print(f"Error logging activity: {e}")


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
        id_token = auth_header[7:]
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
    """Decorator to require Firebase authentication for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Authentication required',
                    'code': 'auth_required'
                }), 401
            return redirect(url_for('landing'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin user type."""
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
    """Decorator to require staff or admin user type."""
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


# ========================================
# User Type Functions
# ========================================

def get_user_type() -> UserType:
    """
    Get current user type from session or Firestore.
    """
    # If user_type is explicitly set in session, use that
    if 'user_type' in session:
        return session['user_type']

    # If user is authenticated, check Firestore or determine from email
    if is_authenticated():
        user = get_current_user()
        if user:
            # Try to get from Firestore
            uid = user.get('uid')
            if uid:
                user_doc = get_user_doc(uid)
                if user_doc and user_doc.get('userType'):
                    return user_doc['userType']

            # Fall back to determining from email
            email = user.get('email', '')
            email_verified = user.get('email_verified', False)
            return determine_user_type(email, email_verified)

        return 'public_registered'

    # Not authenticated
    return 'public_anonymous'


def set_user_type(user_type: UserType):
    """Set user type in session."""
    if user_type in VALID_USER_TYPES:
        session['user_type'] = user_type
        session.permanent = True
    else:
        raise ValueError(f"Invalid user type: {user_type}. Valid types: {VALID_USER_TYPES}")


# ========================================
# Access Control Functions
# ========================================

def get_app_access(app_name: str, user_type: Optional[UserType] = None) -> AccessLevel:
    """Get access level for an app based on user type."""
    if user_type is None:
        user_type = get_user_type()

    app_name = app_name.lower()
    return ACCESS_MATRIX.get(app_name, {}).get(user_type, 'hidden')


def has_access(app_name: str, required_level: AccessLevel = 'full',
               user_type: Optional[UserType] = None) -> bool:
    """Check if user has required access level for an app."""
    access_level = get_app_access(app_name, user_type)

    # Access hierarchy: hidden < locked < limited < full
    access_hierarchy = {'hidden': 0, 'locked': 1, 'limited': 2, 'full': 3}

    return access_hierarchy.get(access_level, 0) >= access_hierarchy.get(required_level, 0)


def require_access(app_name: str, required_level: AccessLevel = 'limited'):
    """Decorator to require access level for a route."""
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
                return redirect(url_for('landing'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_user_permissions(user_type: Optional[UserType] = None) -> dict:
    """Get feature permissions for a user type."""
    if user_type is None:
        user_type = get_user_type()

    return FEATURE_PERMISSIONS.get(user_type, FEATURE_PERMISSIONS['public_anonymous']).copy()


def is_app_visible(app_name: str, user_type: Optional[UserType] = None) -> bool:
    """Check if an app should be visible to a user type."""
    access_level = get_app_access(app_name, user_type)
    return access_level != 'hidden'


def get_visible_apps(user_type: Optional[UserType] = None) -> List[str]:
    """Get list of apps visible to a user type."""
    if user_type is None:
        user_type = get_user_type()

    return [app for app in ACCESS_MATRIX.keys() if is_app_visible(app, user_type)]


def get_apps_by_access_level(access_level: AccessLevel, user_type: Optional[UserType] = None) -> List[str]:
    """Get list of apps with a specific access level for a user type."""
    if user_type is None:
        user_type = get_user_type()

    return [app for app, levels in ACCESS_MATRIX.items()
            if levels.get(user_type) == access_level]


def get_tier_info(user_type: Optional[UserType] = None) -> dict:
    """Get pricing and tier information for a user type."""
    if user_type is None:
        user_type = get_user_type()

    return TIER_PRICING.get(user_type, TIER_PRICING['public_anonymous']).copy()


def get_access_matrix_for_display() -> Dict[str, Dict[str, AccessLevel]]:
    """Get the full access matrix for display purposes."""
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
    """Get current authentication status and user info."""
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
    Creates or updates user document in Firestore.
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

    # Create or update user in Firestore
    uid = decoded.get('uid')
    email = decoded.get('email')
    display_name = user_data.get('displayName', decoded.get('name', ''))
    photo_url = user_data.get('photoURL', decoded.get('picture'))
    email_verified = decoded.get('email_verified', False)

    firestore_user = create_or_update_user_doc(
        uid=uid,
        email=email,
        display_name=display_name,
        photo_url=photo_url,
        email_verified=email_verified
    )

    # Store user in session
    user = {
        'uid': uid,
        'email': email,
        'name': display_name or email.split('@')[0],
        'picture': photo_url,
        'email_verified': email_verified,
        'provider': decoded.get('firebase', {}).get('sign_in_provider', 'unknown')
    }
    set_session_user(user)

    # Get user type from Firestore document
    user_type = firestore_user.get('userType', 'public_registered')
    set_user_type(user_type)

    # Log login activity
    log_activity(uid, email, 'login')

    return jsonify({
        'success': True,
        'user': user,
        'user_type': user_type,
        'permissions': get_user_permissions(user_type)
    })


@auth_bp.route('/logout', methods=['POST'])
def auth_logout():
    """Clear user session on logout."""
    clear_session_user()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })


@auth_bp.route('/set-user-type', methods=['POST'])
def set_user_type_endpoint():
    """Set user type in session (admin function)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Check if current user is admin
    current_type = get_user_type()
    if current_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    requested_type = data.get('user_type')
    target_uid = data.get('uid')

    if requested_type not in VALID_USER_TYPES:
        return jsonify({
            'error': f'Invalid user type: {requested_type}',
            'valid_types': VALID_USER_TYPES
        }), 400

    if target_uid:
        # Update another user's type in Firestore
        success = update_user_type(target_uid, requested_type)
        if not success:
            return jsonify({'error': 'Failed to update user type'}), 500
    else:
        # Update own session
        set_user_type(requested_type)

    return jsonify({
        'success': True,
        'user_type': requested_type,
        'permissions': get_user_permissions(requested_type),
        'visible_apps': get_visible_apps(requested_type)
    })


@auth_bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    """List all users (admin only)."""
    db = get_firestore_client()
    if not db:
        return jsonify({'error': 'Database not available'}), 500

    try:
        users_ref = db.collection('users')

        # Apply filters if provided
        user_type_filter = request.args.get('userType')
        if user_type_filter:
            users_ref = users_ref.where('userType', '==', user_type_filter)

        # Get users
        users = []
        for doc in users_ref.stream():
            user_data = doc.to_dict()
            users.append({
                'uid': user_data.get('uid'),
                'email': user_data.get('email'),
                'displayName': user_data.get('displayName'),
                'userType': user_data.get('userType'),
                'organization': user_data.get('organization'),
                'lastLoginAt': user_data.get('lastLoginAt'),
                'loginCount': user_data.get('loginCount', 0)
            })

        return jsonify({
            'users': users,
            'count': len(users)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/users/<uid>', methods=['PUT'])
@admin_required
def update_user(uid: str):
    """Update a user (admin only)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    db = get_firestore_client()
    if not db:
        return jsonify({'error': 'Database not available'}), 500

    try:
        user_ref = db.collection('users').document(uid)

        # Build update data (only allow certain fields)
        update_data = {}
        allowed_fields = ['userType', 'organization', 'jobTitle', 'county']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]

        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400

        update_data['updatedAt'] = datetime.utcnow()
        user_ref.update(update_data)

        return jsonify({
            'success': True,
            'updated_fields': list(update_data.keys())
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
