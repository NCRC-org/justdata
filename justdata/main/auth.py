"""
Access control system for JustData applications.
Implements user type-based access control based on the access matrix.
Integrates Firebase Authentication and Firestore for user management.

User Types (8 tiers):
- public_anonymous: No account, not logged in
- public_registered: Google sign-in, basic access
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
from typing import Optional, Literal, Dict, List, TYPE_CHECKING

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth, firestore

# Firebase client wrappers (extracted into services module)
from justdata.main.auth.services.firebase_client import (
    init_firebase,
    get_firebase_app,
    get_firestore_client,
    verify_firebase_token,
    get_user_doc,
)

# Type hints for membership lookup (avoid circular imports)
if TYPE_CHECKING:
    from justdata.apps.hubspot.membership import MembershipLookupResult

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

# User types matching the 8-tier system
UserType = Literal[
    'public_anonymous',
    'public_registered',
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
    'member',
    'member_premium',
    'non_member_org',
    'staff',
    'senior_executive',
    'admin'
]

# HubSpot membership_status values that grant member access (grace period)
GRACE_PERIOD_VALUES = ['GRACE PERIOD']

# Privileged roles that have full access to the platform
# Only these roles can see app content; all others see a restricted view
PRIVILEGED_ROLES = ['staff', 'senior_executive', 'admin']

# Access matrix matching the User Access Matrix
# Format: app_name: {user_type: access_level}
ACCESS_MATRIX = {
    # ========================================
    # AI-Driven Reports
    # ========================================
    'lendsight': {
        'public_anonymous': 'locked',
        'public_registered': 'limited',
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
    'member': {'price': 900, 'billing': 'yearly', 'label': 'Member'},
    'member_premium': {'price_range': (500, 750), 'billing': 'yearly', 'label': 'Member Premium', 'addon': True},
    'non_member_org': {'price_range': (5000, 15000), 'billing': 'yearly', 'label': 'Institutional'},
    'staff': {'price': 0, 'billing': 'free', 'label': 'Staff', 'internal': True},
    'senior_executive': {'price': 0, 'billing': 'free', 'label': 'Senior Executive', 'internal': True},
    'admin': {'price': 0, 'billing': 'free', 'label': 'Admin', 'internal': True}
}


# ========================================
# Firestore User Management
# ========================================

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
            # For work emails, perform HubSpot membership lookup
            membership_result = None
            hubspot_data = {}

            try:
                from justdata.apps.hubspot.membership import (
                    lookup_membership_sync,
                    is_ncrc_email
                )

                if not is_ncrc_email(email):
                    print(f"[create_or_update_user_doc] Performing HubSpot lookup for {email}")
                    membership_result = lookup_membership_sync(email)

                    # Store HubSpot lookup results
                    hubspot_data = {
                        'hubspot_contact_id': membership_result.contact_id,
                        'hubspot_company_id': membership_result.company_id,
                        'hubspot_company_name': membership_result.company_name,
                        'hubspot_membership_status': membership_result.membership_status,
                        'hubspot_lookup_method': membership_result.lookup_method,
                        'email_template_sent': membership_result.email_template,
                        'registration_email_pending': True  # Flag for email trigger
                    }
                    print(f"[create_or_update_user_doc] HubSpot lookup result: is_member={membership_result.is_member}, status={membership_result.membership_status}")

            except ImportError as e:
                print(f"[create_or_update_user_doc] HubSpot module not available: {e}")
            except Exception as e:
                print(f"[create_or_update_user_doc] HubSpot lookup error: {e}")

            # Determine user type (now with membership result if available)
            user_type = determine_user_type(
                email, email_verified,
                auth_provider=auth_provider,
                membership_result=membership_result
            )

            # Auto-set organization for @ncrc.org users or from HubSpot lookup
            if email.lower().endswith('@ncrc.org'):
                final_organization = 'NCRC'
                needs_organization = False
            elif membership_result and membership_result.company_name:
                final_organization = membership_result.company_name
                needs_organization = False
            else:
                final_organization = organization
                needs_organization = not organization  # True if no organization provided

            user_data = {
                'uid': uid,
                'email': email,
                'displayName': display_name or email.split('@')[0],
                'firstName': first_name,
                'lastName': last_name,
                'photoURL': photo_url,
                'userType': user_type,
                'organization': final_organization,
                'needsOrganization': needs_organization,
                'jobTitle': None,
                'county': None,
                'emailVerified': email_verified,
                'authProvider': auth_provider,
                'createdAt': now,
                'lastLoginAt': now,
                'loginCount': 1,
                **hubspot_data  # Include HubSpot data if lookup was performed
            }
            user_ref.set(user_data)

            # Log registration activity with HubSpot info
            log_activity(uid, email, 'registration', metadata={
                'userType': user_type,
                'authProvider': auth_provider,
                'hubspot_lookup': membership_result.lookup_method if membership_result else 'none',
                'hubspot_is_member': membership_result.is_member if membership_result else None
            })

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
                         current_type: str = None, auth_provider: str = None,
                         membership_result: 'MembershipLookupResult' = None) -> UserType:
    """
    Determine user type based on email, verification status, and HubSpot membership.

    Args:
        email: User's email address
        email_verified: Whether email is verified
        current_type: Current user type (if upgrading)
        auth_provider: The authentication provider ('google.com', 'password', etc.)
        membership_result: Optional HubSpot membership lookup result

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
                                          'staff', 'senior_executive', 'admin']:
        return current_type

    # If membership result provided, use it to determine member status
    if membership_result:
        if membership_result.is_member:
            return 'member'
        # Grace period users also get member access
        if membership_result.membership_status and \
           membership_result.membership_status.upper().strip() in GRACE_PERIOD_VALUES:
            return 'member'

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
# Session and Current User
# ========================================

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
        # Validate session user has required fields
        if user and not user.get('uid') and not user.get('email'):
            print(f"[AUTH WARN] Session user missing uid and email: {list(user.keys()) if user else 'None'}")

    # Log when no user found for non-static requests (helps debug auth issues)
    if not user and request.endpoint and not request.path.startswith('/static'):
        # Only log for app routes that might need auth
        if any(app in request.path for app in ['/analyze', '/report', '/api/']):
            print(f"[AUTH DEBUG] No user found for {request.method} {request.path}")
            print(f"[AUTH DEBUG] Has Authorization header: {bool(auth_header)}")
            print(f"[AUTH DEBUG] Has firebase_user in session: {'firebase_user' in session}")

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


def is_privileged_user(user_type: Optional[UserType] = None) -> bool:
    """
    Check if user has a privileged role (staff, senior_executive, or admin).
    Only privileged users can access the full application.

    Args:
        user_type: User type to check (defaults to current session user type)

    Returns:
        True if user has a privileged role, False otherwise
    """
    if user_type is None:
        user_type = get_user_type()
    return user_type in PRIVILEGED_ROLES


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


