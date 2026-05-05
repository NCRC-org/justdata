"""
Auth login / session routes.

Routes:
- GET  /status              — Current authentication status, user, permissions
- POST /login               — Store user session after Firebase frontend auth
- POST /logout              — Clear user session
- GET  /verification-status — Email-verification state for the current user
- POST /email-verified      — Called after user verifies email; updates user type
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, session

from justdata.main.auth.services.firebase_client import (
    get_firebase_app,
    get_firestore_client,
    verify_firebase_token,
    get_user_doc,
)
from justdata.main.auth import (
    get_current_user,
    set_session_user,
    clear_session_user,
    get_user_type,
    set_user_type,
    get_user_permissions,
    get_visible_apps,
    get_tier_info,
    create_or_update_user_doc,
    determine_user_type,
    log_activity,
)

login_bp = Blueprint("auth_login", __name__)


@login_bp.route('/status', methods=['GET'])
def auth_status():
    """Get current authentication status and user info."""
    user = get_current_user()
    user_type = get_user_type()
    permissions = get_user_permissions(user_type)

    # Get loginCount from Firestore for first-time user detection
    login_count = None
    if user and user.get('uid'):
        user_doc = get_user_doc(user.get('uid'))
        if user_doc:
            login_count = user_doc.get('loginCount', 0)

    return jsonify({
        'authenticated': user is not None,
        'user': user,
        'user_type': user_type,
        'permissions': permissions,
        'visible_apps': get_visible_apps(user_type),
        'tier_info': get_tier_info(user_type),
        'login_count': login_count
    })


@login_bp.route('/login', methods=['POST'])
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

    # Verify the token (requires Firebase Admin credentials in env)
    if not get_firebase_app():
        return jsonify({
            'error': 'Server configuration error: Firebase credentials not set.',
            'code': 'firebase_not_configured',
            'hint': 'Set FIREBASE_CREDENTIALS_JSON or FIREBASE_CREDENTIALS in .env (Firebase Console → Project settings → Service accounts → Generate new private key).'
        }), 503
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

    # Check if user needs to provide organization (non-NCRC users without org)
    needs_organization = firestore_user.get('needsOrganization', False)
    # Also check if organization is empty for non-NCRC users
    if not email.lower().endswith('@ncrc.org') and not firestore_user.get('organization'):
        needs_organization = True

    return jsonify({
        'success': True,
        'user': user,
        'user_type': user_type,
        'permissions': get_user_permissions(user_type),
        'needs_email_verification': needs_verification,
        'needs_organization': needs_organization,
        'organization': firestore_user.get('organization')
    })


@login_bp.route('/logout', methods=['POST'])
def auth_logout():
    """Clear user session on logout."""
    clear_session_user()
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })


@login_bp.route('/verification-status', methods=['GET'])
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


@login_bp.route('/email-verified', methods=['POST'])
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
