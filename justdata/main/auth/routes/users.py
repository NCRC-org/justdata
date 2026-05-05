"""
Auth user-management routes.

Routes:
- POST /set-user-type             — Admin: change user type (own session or another user)
- GET  /users                     — Admin: list all users
- POST /users                     — Admin: create a pending user (Firestore only)
- PUT  /users/<uid>               — Admin: update user fields
- POST /users/delete              — Admin: bulk delete users (Auth + Firestore)
- PUT  /users/<uid>/reset-password — Admin: reset a user's password
"""

import hashlib
from datetime import datetime
from flask import Blueprint, request, jsonify

from firebase_admin import auth as firebase_auth

from justdata.main.auth.services.firebase_client import (
    get_firebase_app,
    get_firestore_client,
)
from justdata.main.auth import (
    admin_required,
    get_user_type,
    set_user_type,
    update_user_type,
    get_user_permissions,
    get_visible_apps,
    get_current_user,
    log_activity,
    VALID_USER_TYPES,
)

users_bp = Blueprint("auth_users", __name__)


@users_bp.route('/set-user-type', methods=['POST'])
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


@users_bp.route('/users', methods=['GET'])
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


@users_bp.route('/users', methods=['POST'])
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


@users_bp.route('/users/<uid>', methods=['PUT'])
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


@users_bp.route('/users/delete', methods=['POST'])
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


@users_bp.route('/users/<uid>/reset-password', methods=['PUT'])
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
