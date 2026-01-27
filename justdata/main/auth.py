"""
Access control system for JustData applications.
Implements user type-based access control based on the access matrix.
Integrates Firebase Authentication and Firestore for user management.

User Types (9 tiers):
- public_anonymous: No account, not logged in
- public_registered: Google sign-in, basic access
- just_economy_club: Free tier with limited features
- member: NCRC Member ($900/yr)
- member_premium: Member Plus tier
- non_member_org: Institutional/organizational access
- staff: NCRC Staff (@ncrc.org domain)
- senior_executive: NCRC Senior Executives (additional tools access)
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

# Senior Executive users (above staff, below admin)
SENIOR_EXECUTIVE_EMAILS = [
    'jvantol@ncrc.org',      # Jesse Van Tol
    'eforsythe@ncrc.org',    # Eden Forsythe
    'gdyson@ncrc.org',       # Gregory Dyson
    'crountree@ncrc.org',    # Caitie Rountree
    'mmathis@ncrc.org',      # Michael Mathis
    'sterry@ncrc.org',       # Sabrina Terry
    'tflynn@ncrc.org',       # Tara Flynn
    'jmatthews@ncrc.org',    # Jacelyn Matthews
    'awiltse@ncrc.org',      # Alyssa Wiltse
    'testexec@justdata.ncrc.org',  # Test Executive Account
    'testsenior@justdata.ncrc.org',  # Test Senior Executive (working login)
]

# User types matching the 9-tier system
UserType = Literal[
    'public_anonymous',
    'public_registered',
    'just_economy_club',
    'member',
    'member_premium',
    'non_member_org',
    'staff',
    'senior_executive',
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
    'senior_executive',
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
        'senior_executive': 'full',
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
        'senior_executive': 'full',
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
        'senior_executive': 'full',
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
        'senior_executive': 'full',
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
        'senior_executive': 'full',
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
        'senior_executive': 'full',
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
        'senior_executive': 'full',
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
        'senior_executive': 'full',
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
        'senior_executive': 'full',
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
        'senior_executive': 'full',
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
        'senior_executive': 'full',
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
        'staff': 'hidden',
        'senior_executive': 'full',
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
        'senior_executive': 'hidden',
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
        'senior_executive': 'hidden',
        'admin': 'full'
    },

    'redlining': {
        'public_anonymous': 'hidden',
        'public_registered': 'hidden',
        'just_economy_club': 'hidden',
        'member': 'hidden',
        'member_premium': 'hidden',
        'non_member_org': 'hidden',
        'staff': 'full',
        'senior_executive': 'full',
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
        'senior_executive': 'full',
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
        'senior_executive': 'full',
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
    'senior_executive': {
        'geographic_limit': 'unlimited',
        'max_counties': None,
        'can_export': True,
        'export_formats': ['excel', 'pdf', 'powerpoint', 'csv', 'json'],
        'ai_reports': True,
        'dataexplorer_enhanced': True,
        'internal_tools': True,
        'executive_tools': True,
        'description': 'NCRC Senior Executive - staff access plus executive-only tools'
    },
    'admin': {
        'geographic_limit': 'unlimited',
        'max_counties': None,
        'can_export': True,
        'export_formats': ['excel', 'pdf', 'powerpoint', 'csv', 'json'],
        'ai_reports': True,
        'dataexplorer_enhanced': True,
        'internal_tools': True,
        'executive_tools': True,
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
    'senior_executive': {'price': 0, 'billing': 'free', 'label': 'Senior Executive', 'internal': True},
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

    # Get credentials from environment (check multiple sources)
    creds_path = os.environ.get('FIREBASE_CREDENTIALS')
    creds_json = os.environ.get('FIREBASE_CREDENTIALS_JSON')

    # Fallback to BigQuery credentials (often same service account)
    if not creds_json:
        creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')

    if creds_path and os.path.exists(creds_path):
        cred = credentials.Certificate(creds_path)
        print(f"Firebase initialized with credentials from file: {creds_path}")
    elif creds_json:
        try:
            cred_dict = json.loads(creds_json)
            cred = credentials.Certificate(cred_dict)
            print("Firebase initialized with credentials from environment JSON")
        except json.JSONDecodeError as e:
            print(f"Error parsing Firebase credentials JSON: {e}")
            return None
    else:
        print("Warning: Firebase credentials not found. Authentication disabled.")
        print("  Checked: FIREBASE_CREDENTIALS, FIREBASE_CREDENTIALS_JSON, GOOGLE_APPLICATION_CREDENTIALS_JSON")
        return None

    try:
        _firebase_app = firebase_admin.initialize_app(cred)
        return _firebase_app
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        return None


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
                               photo_url: str = None, email_verified: bool = False,
                               auth_provider: str = None, organization: str = None,
                               first_name: str = None, last_name: str = None) -> dict:
    """
    Create or update user document in Firestore.

    Args:
        uid: Firebase Auth UID
        email: User's email address
        display_name: User's display name
        photo_url: User's profile photo URL
        email_verified: Whether email is verified
        auth_provider: The authentication provider ('google.com', 'password', etc.)

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
            'userType': determine_user_type(email, email_verified, auth_provider=auth_provider),
            'emailVerified': email_verified,
            'authProvider': auth_provider
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

            # Update auth provider if provided
            if auth_provider:
                update_data['authProvider'] = auth_provider

            # Update display name and photo if provided
            if display_name:
                update_data['displayName'] = display_name
            if photo_url:
                update_data['photoURL'] = photo_url

            # Update organization and name fields if provided (from registration)
            if organization:
                update_data['organization'] = organization
            if first_name:
                update_data['firstName'] = first_name
            if last_name:
                update_data['lastName'] = last_name

            # Check if user type should be upgraded (e.g., @ncrc.org verified)
            current_type = user_data.get('userType', 'public_registered')
            # Use stored auth provider if not provided in this call
            stored_provider = auth_provider or user_data.get('authProvider')
            new_type = determine_user_type(email, email_verified, current_type, auth_provider=stored_provider)
            if new_type != current_type:
                update_data['userType'] = new_type

            user_ref.update(update_data)

            # Return merged data
            user_data.update(update_data)
            return user_data
        else:
            # Create new user
            user_type = determine_user_type(email, email_verified, auth_provider=auth_provider)
            user_data = {
                'uid': uid,
                'email': email,
                'displayName': display_name or email.split('@')[0],
                'firstName': first_name,
                'lastName': last_name,
                'photoURL': photo_url,
                'userType': user_type,
                'organization': organization,
                'jobTitle': None,
                'county': None,
                'emailVerified': email_verified,
                'authProvider': auth_provider,
                'createdAt': now,
                'lastLoginAt': now,
                'loginCount': 1
            }
            user_ref.set(user_data)

            # Log registration activity
            log_activity(uid, email, 'registration', metadata={'userType': user_type, 'authProvider': auth_provider})

            return user_data

    except Exception as e:
        # Log with more detail for debugging
        import traceback
        print(f"ERROR creating/updating user doc for {email}: {e}")
        print(f"  Traceback: {traceback.format_exc()}")

        # Return fallback with correct user type (important for @ncrc.org users)
        fallback_type = determine_user_type(email, email_verified, auth_provider=auth_provider)
        print(f"  Using fallback userType: {fallback_type}")
        return {
            'uid': uid,
            'email': email,
            'displayName': display_name,
            'userType': fallback_type,
            'emailVerified': email_verified,
            'authProvider': auth_provider,
            '_firestore_failed': True  # Flag to indicate Firestore write failed
        }


def determine_user_type(email: str, email_verified: bool = False,
                         current_type: str = None, auth_provider: str = None) -> UserType:
    """
    Determine user type based on email and verification status.

    Args:
        email: User's email address
        email_verified: Whether email is verified
        current_type: Current user type (if upgrading)
        auth_provider: The authentication provider ('google.com', 'password', etc.)

    Returns:
        Appropriate user type
    """
    if not email:
        return 'public_anonymous'

    email_lower = email.lower()

    # Check admin list first
    if email_lower in [e.lower() for e in ADMIN_EMAILS]:
        return 'admin'

    # Check senior executive list
    if email_lower in [e.lower() for e in SENIOR_EXECUTIVE_EMAILS]:
        return 'senior_executive'

    # Check NCRC domain
    if email_lower.endswith('@ncrc.org'):
        # Google sign-in with @ncrc.org domain = trusted, give staff access
        if auth_provider == 'google.com':
            return 'staff'
        # Email/password sign-in requires email verification for staff access
        if email_verified:
            return 'staff'
        # Unverified @ncrc.org email/password users get public_registered until verified
        return 'public_registered'

    # If current type is set by admin, don't downgrade
    if current_type and current_type in ['member', 'member_premium', 'non_member_org',
                                          'just_economy_club', 'staff', 'senior_executive', 'admin']:
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
    """Decorator to require staff, senior_executive, or admin user type."""
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
        if user_type not in ('staff', 'senior_executive', 'admin'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Staff access required',
                    'code': 'staff_required',
                    'user_type': user_type
                }), 403
            return redirect(url_for('landing'))

        return f(*args, **kwargs)
    return decorated_function


def executive_required(f):
    """Decorator to require senior_executive or admin user type."""
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
        if user_type not in ('senior_executive', 'admin'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Executive access required',
                    'code': 'executive_required',
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
    auth_provider = decoded.get('firebase', {}).get('sign_in_provider', 'unknown')
    organization = user_data.get('organization')
    first_name = user_data.get('firstName')
    last_name = user_data.get('lastName')

    firestore_user = create_or_update_user_doc(
        uid=uid,
        email=email,
        display_name=display_name,
        photo_url=photo_url,
        email_verified=email_verified,
        auth_provider=auth_provider,
        organization=organization,
        first_name=first_name,
        last_name=last_name
    )

    # Store user in session
    user = {
        'uid': uid,
        'email': email,
        'name': display_name or email.split('@')[0],
        'picture': photo_url,
        'email_verified': email_verified,
        'provider': auth_provider
    }
    set_session_user(user)

    # Get user type from Firestore document
    user_type = firestore_user.get('userType', 'public_registered')
    set_user_type(user_type)

    # Log login activity
    log_activity(uid, email, 'login', metadata={'authProvider': auth_provider})

    # Check if user needs to verify email (for @ncrc.org email/password users)
    needs_verification = (
        email.lower().endswith('@ncrc.org') and
        auth_provider == 'password' and
        not email_verified
    )

    return jsonify({
        'success': True,
        'user': user,
        'user_type': user_type,
        'permissions': get_user_permissions(user_type),
        'needs_email_verification': needs_verification
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

        # Build a map of Firebase Auth users for provider info
        auth_users = {}
        if get_firebase_app():
            try:
                page = firebase_auth.list_users()
                while page:
                    for auth_user in page.users:
                        # Determine auth method from provider data
                        providers = [p.provider_id for p in auth_user.provider_data] if auth_user.provider_data else []
                        auth_method = 'google' if 'google.com' in providers else 'email'
                        auth_users[auth_user.uid] = {
                            'authMethod': auth_method,
                            'providers': providers
                        }
                    page = page.get_next_page()
            except Exception as e:
                print(f"Error fetching Firebase Auth users: {e}")

        # Get users
        users = []
        for doc in users_ref.stream():
            user_data = doc.to_dict()
            uid = doc.id

            # Convert Firestore timestamps to ISO strings
            created_at = user_data.get('createdAt')
            last_login = user_data.get('lastLoginAt')

            if created_at and hasattr(created_at, 'isoformat'):
                created_at = created_at.isoformat()
            elif created_at and hasattr(created_at, 'timestamp'):
                created_at = datetime.fromtimestamp(created_at.timestamp()).isoformat()

            if last_login and hasattr(last_login, 'isoformat'):
                last_login = last_login.isoformat()
            elif last_login and hasattr(last_login, 'timestamp'):
                last_login = datetime.fromtimestamp(last_login.timestamp()).isoformat()

            # Get auth method from Firebase Auth info
            auth_info = auth_users.get(uid, {})

            users.append({
                'uid': uid,
                'email': user_data.get('email'),
                'displayName': user_data.get('displayName'),
                'userType': user_data.get('userType'),
                'organization': user_data.get('organization'),
                'jobTitle': user_data.get('jobTitle'),
                'county': user_data.get('county'),
                'lastLoginAt': last_login,
                'createdAt': created_at,
                'loginCount': user_data.get('loginCount', 0),
                'emailVerified': user_data.get('emailVerified', False),
                'pendingActivation': user_data.get('pendingActivation', False),
                'authMethod': auth_info.get('authMethod', 'email'),
                'providerData': auth_info.get('providers', [])
            })

        return jsonify({
            'users': users,
            'count': len(users)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/users', methods=['POST'])
@admin_required
def create_user():
    """Create a new user (admin only). Creates Firestore document for pre-provisioned user."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email = data.get('email')
    if not email:
        return jsonify({'error': 'Email is required'}), 400

    display_name = data.get('displayName', email.split('@')[0])
    user_type = data.get('userType', 'public_registered')
    organization = data.get('organization')

    # Validate user type
    if user_type not in VALID_USER_TYPES:
        return jsonify({
            'error': f'Invalid user type: {user_type}',
            'valid_types': VALID_USER_TYPES
        }), 400

    db = get_firestore_client()
    if not db:
        return jsonify({'error': 'Database not available'}), 500

    try:
        # Check if user already exists by email
        existing = db.collection('users').where('email', '==', email).limit(1).stream()
        for doc in existing:
            return jsonify({
                'error': 'User with this email already exists',
                'uid': doc.id
            }), 409

        # Create a pending user document (will be linked when user logs in)
        # Use email hash as temporary UID
        import hashlib
        temp_uid = f"pending_{hashlib.md5(email.lower().encode()).hexdigest()[:16]}"

        now = datetime.utcnow()
        user_data = {
            'uid': temp_uid,
            'email': email,
            'displayName': display_name,
            'photoURL': None,
            'userType': user_type,
            'organization': organization,
            'jobTitle': data.get('jobTitle'),
            'county': data.get('county'),
            'emailVerified': False,
            'createdAt': now,
            'lastLoginAt': None,
            'loginCount': 0,
            'pendingActivation': True  # Flag for pre-provisioned users
        }

        db.collection('users').document(temp_uid).set(user_data)

        return jsonify({
            'success': True,
            'uid': temp_uid,
            'message': f'User {email} created. They can now sign in with Google to activate.',
            'user': user_data
        }), 201

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

        # Verify document exists first
        doc = user_ref.get()
        if not doc.exists:
            return jsonify({'error': f'User document not found for uid: {uid}'}), 404

        # Build update data (only allow certain fields)
        update_data = {}
        allowed_fields = ['userType', 'organization', 'jobTitle', 'county']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]

        if not update_data:
            return jsonify({'error': 'No valid fields to update'}), 400

        update_data['updatedAt'] = datetime.utcnow()

        # Log what we're updating for debugging
        print(f"[update_user] Updating user {uid}: {update_data}")

        user_ref.update(update_data)

        # Read back to verify the update worked
        updated_doc = user_ref.get()
        updated_data = updated_doc.to_dict() if updated_doc.exists else {}

        return jsonify({
            'success': True,
            'updated_fields': list(update_data.keys()),
            'current_values': {field: updated_data.get(field) for field in allowed_fields}
        })
    except Exception as e:
        print(f"[update_user] Error updating user {uid}: {e}")
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/resync', methods=['POST'])
def resync_user():
    """
    Resync current user's Firestore document.
    Useful if document wasn't created during initial login or after email verification.
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    uid = user.get('uid')
    email = user.get('email')
    email_verified = user.get('email_verified', False)
    auth_provider = user.get('provider', 'unknown')

    if not uid or not email:
        return jsonify({'error': 'Missing user data'}), 400

    # Force recreate/update the Firestore document
    firestore_user = create_or_update_user_doc(
        uid=uid,
        email=email,
        display_name=user.get('name'),
        photo_url=user.get('picture'),
        email_verified=email_verified,
        auth_provider=auth_provider
    )

    # Check if Firestore write failed
    if firestore_user.get('_firestore_failed'):
        return jsonify({
            'success': False,
            'error': 'Firestore write failed',
            'user_type': firestore_user.get('userType')
        }), 500

    # Update session with correct user type
    user_type = firestore_user.get('userType', 'public_registered')
    set_user_type(user_type)

    # Check if user needs to verify email
    needs_verification = (
        email.lower().endswith('@ncrc.org') and
        auth_provider == 'password' and
        not email_verified
    )

    return jsonify({
        'success': True,
        'user_type': user_type,
        'permissions': get_user_permissions(user_type),
        'needs_email_verification': needs_verification,
        'message': 'User document synced successfully'
    })


@auth_bp.route('/verification-status', methods=['GET'])
def get_verification_status():
    """
    Get current user's email verification status.
    Returns whether the user needs to verify their email for full access.
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    email = user.get('email', '')
    email_verified = user.get('email_verified', False)
    auth_provider = user.get('provider', 'unknown')

    # Determine if user needs verification
    is_ncrc_email = email.lower().endswith('@ncrc.org')
    is_email_password = auth_provider == 'password'
    needs_verification = is_ncrc_email and is_email_password and not email_verified

    # Get current and potential user type
    current_type = get_user_type()
    potential_type = 'staff' if is_ncrc_email and email_verified else current_type

    return jsonify({
        'email': email,
        'email_verified': email_verified,
        'auth_provider': auth_provider,
        'needs_verification': needs_verification,
        'is_ncrc_email': is_ncrc_email,
        'current_user_type': current_type,
        'potential_user_type': potential_type,
        'message': 'Verify your email to get staff access' if needs_verification else None
    })


@auth_bp.route('/email-verified', methods=['POST'])
def handle_email_verified():
    """
    Called after user verifies their email.
    Updates their user type if they're @ncrc.org.
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    uid = user.get('uid')
    email = user.get('email', '')
    auth_provider = user.get('provider', 'unknown')

    if not uid:
        return jsonify({'error': 'Missing user ID'}), 400

    db = get_firestore_client()
    if not db:
        return jsonify({'error': 'Database not available'}), 500

    try:
        # Update user document
        user_ref = db.collection('users').document(uid)
        update_data = {
            'emailVerified': True,
            'emailVerifiedAt': datetime.utcnow()
        }

        # If @ncrc.org user, upgrade to staff
        if email.lower().endswith('@ncrc.org'):
            new_type = determine_user_type(email, True, auth_provider=auth_provider)
            update_data['userType'] = new_type

            # Update session
            set_user_type(new_type)

            # Log the upgrade
            log_activity(uid, email, 'email_verified_upgrade', metadata={
                'new_user_type': new_type
            })
        else:
            new_type = get_user_type()

        user_ref.update(update_data)

        # Update session user
        session_user = session.get('firebase_user', {})
        session_user['email_verified'] = True
        set_session_user(session_user)

        return jsonify({
            'success': True,
            'user_type': new_type,
            'permissions': get_user_permissions(new_type),
            'message': 'Email verified successfully!' + (
                ' You now have staff access.' if email.lower().endswith('@ncrc.org') else ''
            )
        })

    except Exception as e:
        print(f"Error handling email verification: {e}")
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/sync-all', methods=['POST'])
@admin_required
def sync_all_users():
    """
    Sync all Firebase Auth users to Firestore (admin only).
    Creates missing documents and updates user types for @ncrc.org users.
    """
    if not get_firebase_app():
        return jsonify({'error': 'Firebase not initialized'}), 500

    db = get_firestore_client()
    if not db:
        return jsonify({'error': 'Firestore not available'}), 500

    try:
        # Get all Firebase Auth users
        results = {
            'created': [],
            'updated': [],
            'errors': [],
            'unchanged': []
        }

        # Iterate through Firebase Auth users (paginated)
        page = firebase_auth.list_users()
        while page:
            for auth_user in page.users:
                try:
                    uid = auth_user.uid
                    email = auth_user.email or ''

                    # Check if Firestore document exists
                    doc = db.collection('users').document(uid).get()

                    if doc.exists:
                        # Check if user type needs updating
                        user_data = doc.to_dict()
                        current_type = user_data.get('userType', 'public_registered')
                        expected_type = determine_user_type(email, auth_user.email_verified or False)

                        # Update if @ncrc.org user isn't staff/admin
                        if email.lower().endswith('@ncrc.org') and current_type not in ('staff', 'admin'):
                            db.collection('users').document(uid).update({
                                'userType': expected_type,
                                'userTypeUpdatedAt': datetime.utcnow()
                            })
                            results['updated'].append({
                                'email': email,
                                'old_type': current_type,
                                'new_type': expected_type
                            })
                        else:
                            results['unchanged'].append(email)
                    else:
                        # Create missing document
                        user_type = determine_user_type(email, auth_user.email_verified or False)
                        user_data = {
                            'uid': uid,
                            'email': email,
                            'displayName': auth_user.display_name or email.split('@')[0],
                            'photoURL': auth_user.photo_url,
                            'userType': user_type,
                            'organization': 'NCRC' if email.lower().endswith('@ncrc.org') else None,
                            'jobTitle': None,
                            'county': None,
                            'emailVerified': auth_user.email_verified or False,
                            'createdAt': datetime.utcnow(),
                            'lastLoginAt': datetime.utcnow(),
                            'loginCount': 0
                        }
                        db.collection('users').document(uid).set(user_data)
                        results['created'].append({
                            'email': email,
                            'user_type': user_type
                        })

                except Exception as e:
                    results['errors'].append({
                        'email': auth_user.email,
                        'error': str(e)
                    })

            # Get next page
            page = page.get_next_page()

        return jsonify({
            'success': True,
            'results': results,
            'summary': {
                'created': len(results['created']),
                'updated': len(results['updated']),
                'unchanged': len(results['unchanged']),
                'errors': len(results['errors'])
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/users/delete', methods=['POST'])
@admin_required
def delete_users():
    """
    Delete multiple users (admin only).
    Deletes from both Firebase Auth and Firestore.

    Safeguards:
    - Cannot delete admin users
    - Cannot delete your own account
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    uids = data.get('uids', [])
    if not uids:
        return jsonify({'error': 'No user IDs provided'}), 400

    # Get current user to prevent self-deletion
    current_user = get_current_user()
    current_uid = current_user.get('uid') if current_user else None

    db = get_firestore_client()
    if not db:
        return jsonify({'error': 'Database not available'}), 500

    results = []

    for uid in uids:
        result = {'uid': uid, 'success': False, 'error': None}

        try:
            # Prevent self-deletion
            if uid == current_uid:
                result['error'] = 'Cannot delete your own account'
                results.append(result)
                continue

            # Check if user is admin in Firestore
            user_doc = db.collection('users').document(uid).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                if user_data.get('userType') == 'admin':
                    result['error'] = 'Cannot delete admin users'
                    results.append(result)
                    continue

                # Store email for logging
                result['email'] = user_data.get('email')

            # Delete from Firebase Auth (if exists)
            try:
                firebase_auth.delete_user(uid)
            except firebase_auth.UserNotFoundError:
                # User doesn't exist in Auth, continue with Firestore deletion
                pass
            except Exception as auth_error:
                # Log but continue - Firestore deletion is also important
                print(f"Firebase Auth deletion failed for {uid}: {auth_error}")

            # Delete from Firestore
            db.collection('users').document(uid).delete()

            # Log the deletion
            admin_user = get_current_user()
            log_activity(
                uid=current_uid,
                email=admin_user.get('email') if admin_user else 'unknown',
                action='user_deleted',
                metadata={
                    'deleted_uid': uid,
                    'deleted_email': result.get('email'),
                    'timestamp': datetime.utcnow().isoformat()
                }
            )

            result['success'] = True

        except Exception as e:
            result['error'] = str(e)

        results.append(result)

    return jsonify({
        'success': all(r['success'] for r in results),
        'results': results,
        'deleted_count': sum(1 for r in results if r['success']),
        'failed_count': sum(1 for r in results if not r['success'])
    })


@auth_bp.route('/users/<uid>/reset-password', methods=['PUT'])
@admin_required
def reset_user_password(uid: str):
    """
    Reset a user's password (admin only).
    Uses Firebase Admin SDK to update the password.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    new_password = data.get('password')
    if not new_password:
        return jsonify({'error': 'Password is required'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    if not get_firebase_app():
        return jsonify({'error': 'Firebase not initialized'}), 500

    db = get_firestore_client()

    try:
        # Get user info for logging
        user_email = None
        if db:
            user_doc = db.collection('users').document(uid).get()
            if user_doc.exists:
                user_email = user_doc.to_dict().get('email')

        # Update password in Firebase Auth
        firebase_auth.update_user(uid, password=new_password)

        # Log the action
        admin_user = get_current_user()
        log_activity(
            uid=admin_user.get('uid') if admin_user else 'unknown',
            email=admin_user.get('email') if admin_user else 'unknown',
            action='password_reset',
            metadata={
                'target_uid': uid,
                'target_email': user_email,
                'timestamp': datetime.utcnow().isoformat()
            }
        )

        return jsonify({
            'success': True,
            'message': f'Password reset successfully for {user_email or uid}'
        })

    except firebase_auth.UserNotFoundError:
        return jsonify({'error': 'User not found in Firebase Auth'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========================================
# Member Access Request System
# ========================================

# HubSpot membership field configuration
HUBSPOT_MEMBERSHIP_FIELD = os.environ.get('HUBSPOT_MEMBERSHIP_FIELD', 'membership_status')

# Membership values that grant full member access
MEMBER_ACCESS_VALUES = ['CURRENT', 'LIFETIME MEMBER', 'NATIONAL PARTNER', 'RECIPROCAL']
GRACE_PERIOD_VALUES = ['GRACE PERIOD']
NO_ACCESS_VALUES = ['LAPSED', None, '']


def send_slack_member_request_notification(request_data: dict) -> bool:
    """
    Send notification to #justdata-new-user-requests Slack channel.
    Gracefully skips if webhook URL is not configured.

    Args:
        request_data: Dict with user_email, requested_org_name, user_role_at_org, created_at

    Returns:
        True if notification sent, False if skipped or failed
    """
    import requests as http_requests

    webhook_url = os.environ.get('SLACK_MEMBER_REQUEST_WEBHOOK')

    if not webhook_url:
        print("Slack webhook not configured, skipping notification")
        return False

    try:
        # Format timestamp for Slack
        created_at = request_data.get('created_at', datetime.utcnow())
        timestamp = int(created_at.timestamp()) if hasattr(created_at, 'timestamp') else int(datetime.utcnow().timestamp())

        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🆕 New Member Access Request",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*User:*\n{request_data.get('user_email', 'Unknown')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Organization:*\n{request_data.get('requested_org_name', 'Not specified')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Role:*\n{request_data.get('user_role_at_org', 'Not specified')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Submitted:*\n<!date^{timestamp}^{{date_short_pretty}} at {{time}}|Just now>"
                        }
                    ]
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Review in JustData Admin",
                                "emoji": True
                            },
                            "url": "https://justdata.org/admin/users?tab=requests",
                            "style": "primary"
                        }
                    ]
                }
            ]
        }

        response = http_requests.post(webhook_url, json=message, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Failed to send Slack notification: {e}")
        return False


@auth_bp.route('/member-request', methods=['POST'])
@login_required
def submit_member_request():
    """
    Submit a request for member access.
    Creates a pending request in Firestore for admin review.
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    org_name = data.get('organization_name', '').strip()
    user_role = data.get('user_role', '').strip()
    notes = data.get('notes', '').strip()

    if not org_name or not user_role:
        return jsonify({'error': 'Organization name and role are required'}), 400

    uid = user.get('uid')
    email = user.get('email')
    display_name = user.get('name', email.split('@')[0] if email else 'Unknown')

    db = get_firestore_client()
    if not db:
        return jsonify({'error': 'Database not available'}), 500

    try:
        # Check if user already has a pending request
        existing = db.collection('member_requests').where(
            'user_id', '==', uid
        ).where('status', '==', 'pending').limit(1).stream()

        if len(list(existing)) > 0:
            return jsonify({'error': 'You already have a pending request'}), 400

        # Check if user is already a member or higher
        user_doc = get_user_doc(uid)
        if user_doc:
            current_type = user_doc.get('userType', 'public_registered')
            if current_type in ['member', 'member_premium', 'non_member_org', 'staff', 'senior_executive', 'admin']:
                return jsonify({'error': 'You already have member access'}), 400

        now = datetime.utcnow()

        # Create the request
        request_data = {
            'user_id': uid,
            'user_email': email,
            'user_name': display_name,
            'requested_org_name': org_name,
            'user_role_at_org': user_role,
            'request_notes': notes,
            'status': 'pending',
            'created_at': now,
            'reviewed_at': None,
            'reviewed_by': None,
            'hubspot_company_id': None,
            'hubspot_company_name': None,
            'hubspot_membership_status': None,
            'denial_reason': None
        }

        # Add to Firestore
        doc_ref = db.collection('member_requests').add(request_data)
        request_id = doc_ref[1].id

        # Update user document with pending request status
        db.collection('users').document(uid).update({
            'memberRequestStatus': 'pending',
            'memberRequestId': request_id,
            'memberRequestedAt': now,
            'hasSeenMemberPrompt': True
        })

        # Log activity
        log_activity(uid, email, 'member_request_submitted', metadata={
            'request_id': request_id,
            'organization': org_name,
            'role': user_role
        })

        # Send Slack notification (gracefully skips if not configured)
        request_data['created_at'] = now
        send_slack_member_request_notification(request_data)

        return jsonify({
            'success': True,
            'request_id': request_id,
            'message': 'Request submitted successfully'
        }), 201

    except Exception as e:
        print(f"Error submitting member request: {e}")
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/member-request/dismiss-prompt', methods=['POST'])
@login_required
def dismiss_member_prompt():
    """
    Mark that user has seen the member prompt and chose to continue as guest.
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    uid = user.get('uid')

    db = get_firestore_client()
    if not db:
        return jsonify({'error': 'Database not available'}), 500

    try:
        db.collection('users').document(uid).update({
            'hasSeenMemberPrompt': True
        })

        return jsonify({
            'success': True,
            'message': 'Prompt dismissed'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/member-request/status', methods=['GET'])
@login_required
def get_member_request_status():
    """
    Get the current user's member request status.
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    uid = user.get('uid')

    db = get_firestore_client()
    if not db:
        return jsonify({'error': 'Database not available'}), 500

    try:
        user_doc = get_user_doc(uid)
        if not user_doc:
            return jsonify({
                'hasSeenMemberPrompt': False,
                'memberRequestStatus': None,
                'membershipStatus': None
            })

        return jsonify({
            'hasSeenMemberPrompt': user_doc.get('hasSeenMemberPrompt', False),
            'memberRequestStatus': user_doc.get('memberRequestStatus'),
            'memberRequestId': user_doc.get('memberRequestId'),
            'membershipStatus': user_doc.get('membershipStatus'),
            'organizationName': user_doc.get('organizationName')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/admin/member-requests', methods=['GET'])
@admin_required
def get_member_requests():
    """Get all member requests (admin only)."""
    status_filter = request.args.get('status', 'pending')

    db = get_firestore_client()
    if not db:
        return jsonify({'error': 'Database not available'}), 500

    try:
        query = db.collection('member_requests')

        if status_filter != 'all':
            query = query.where('status', '==', status_filter)

        query = query.order_by('created_at', direction=firestore.Query.DESCENDING)

        requests_list = []
        for doc in query.stream():
            req = doc.to_dict()
            req['id'] = doc.id

            # Convert timestamps to ISO strings
            if req.get('created_at') and hasattr(req['created_at'], 'isoformat'):
                req['created_at'] = req['created_at'].isoformat()
            if req.get('reviewed_at') and hasattr(req['reviewed_at'], 'isoformat'):
                req['reviewed_at'] = req['reviewed_at'].isoformat()

            requests_list.append(req)

        return jsonify({
            'requests': requests_list,
            'count': len(requests_list)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/admin/hubspot/companies/search', methods=['GET'])
@admin_required
def search_hubspot_companies():
    """Search HubSpot for companies by name (admin only)."""
    import requests as http_requests

    search_term = request.args.get('q', '').strip()

    if not search_term or len(search_term) < 2:
        return jsonify({'error': 'Search term must be at least 2 characters'}), 400

    hubspot_token = os.environ.get('HUBSPOT_ACCESS_TOKEN')
    if not hubspot_token:
        return jsonify({'error': 'HubSpot API not configured'}), 500

    url = "https://api.hubapi.com/crm/v3/objects/companies/search"
    headers = {
        "Authorization": f"Bearer {hubspot_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "filterGroups": [{
            "filters": [{
                "propertyName": "name",
                "operator": "CONTAINS_TOKEN",
                "value": search_term
            }]
        }],
        "properties": [
            "name",
            "city",
            "state",
            HUBSPOT_MEMBERSHIP_FIELD,
            "domain"
        ],
        "limit": 10
    }

    try:
        response = http_requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        results = response.json().get("results", [])

        companies = []
        for company in results:
            props = company.get("properties", {})
            membership_status = props.get(HUBSPOT_MEMBERSHIP_FIELD, "") or ""
            membership_status_upper = membership_status.upper().strip()

            has_access = membership_status_upper in MEMBER_ACCESS_VALUES or membership_status_upper in GRACE_PERIOD_VALUES
            is_grace_period = membership_status_upper in GRACE_PERIOD_VALUES

            companies.append({
                "id": company["id"],
                "name": props.get("name"),
                "city": props.get("city"),
                "state": props.get("state"),
                "membership_status": membership_status,
                "has_access": has_access,
                "is_grace_period": is_grace_period
            })

        return jsonify({'results': companies})

    except http_requests.exceptions.RequestException as e:
        return jsonify({'error': f'HubSpot API error: {str(e)}'}), 500


@auth_bp.route('/admin/member-requests/<request_id>/review', methods=['POST'])
@admin_required
def review_member_request(request_id):
    """Approve or deny a member request (admin only)."""
    admin_user = get_current_user()
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    action = data.get('action')  # "approve" or "deny"

    if action not in ['approve', 'deny']:
        return jsonify({'error': "Action must be 'approve' or 'deny'"}), 400

    db = get_firestore_client()
    if not db:
        return jsonify({'error': 'Database not available'}), 500

    try:
        # Get the request
        req_ref = db.collection('member_requests').document(request_id)
        req_doc = req_ref.get()

        if not req_doc.exists:
            return jsonify({'error': 'Request not found'}), 404

        req_data = req_doc.to_dict()

        if req_data['status'] != 'pending':
            return jsonify({'error': 'Request has already been reviewed'}), 400

        now = datetime.utcnow()
        admin_email = admin_user.get('email') if admin_user else 'unknown'

        if action == 'approve':
            hubspot_company_id = data.get('hubspot_company_id')
            hubspot_company_name = data.get('hubspot_company_name')
            hubspot_membership_status = data.get('hubspot_membership_status')

            if not hubspot_company_id:
                return jsonify({'error': 'Must select a HubSpot company to approve'}), 400

            # Update the request
            req_ref.update({
                'status': 'approved',
                'reviewed_at': now,
                'reviewed_by': admin_email,
                'hubspot_company_id': hubspot_company_id,
                'hubspot_company_name': hubspot_company_name,
                'hubspot_membership_status': hubspot_membership_status
            })

            # Update the user's Firestore document
            user_ref = db.collection('users').document(req_data['user_id'])
            user_ref.update({
                'userType': 'member',
                'organizationName': hubspot_company_name,
                'hubspotCompanyId': hubspot_company_id,
                'membershipStatus': hubspot_membership_status,
                'memberApprovedAt': now,
                'memberApprovedBy': admin_email,
                'memberRequestStatus': 'approved'
            })

            # Log activity
            log_activity(
                uid=admin_user.get('uid') if admin_user else 'unknown',
                email=admin_email,
                action='member_request_approved',
                metadata={
                    'request_id': request_id,
                    'user_email': req_data.get('user_email'),
                    'organization': hubspot_company_name
                }
            )

            return jsonify({
                'success': True,
                'message': f"Approved. {req_data['user_email']} now has member access."
            })

        else:  # deny
            denial_reason = data.get('denial_reason', 'Request denied')

            req_ref.update({
                'status': 'denied',
                'reviewed_at': now,
                'reviewed_by': admin_email,
                'denial_reason': denial_reason
            })

            # Update user document
            user_ref = db.collection('users').document(req_data['user_id'])
            user_ref.update({
                'memberRequestStatus': 'denied',
                'memberRequestDeniedReason': denial_reason
            })

            # Log activity
            log_activity(
                uid=admin_user.get('uid') if admin_user else 'unknown',
                email=admin_email,
                action='member_request_denied',
                metadata={
                    'request_id': request_id,
                    'user_email': req_data.get('user_email'),
                    'reason': denial_reason
                }
            )

            return jsonify({
                'success': True,
                'message': 'Request denied.'
            })

    except Exception as e:
        print(f"Error reviewing member request: {e}")
        return jsonify({'error': str(e)}), 500
