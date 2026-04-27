"""
Auth sync routes.

Routes:
- POST /resync   — Resync the current user's Firestore document
- POST /sync-all — Admin: sync all Firebase Auth users to Firestore + prune orphans
"""

from datetime import datetime
from flask import Blueprint, jsonify

from firebase_admin import auth as firebase_auth

from justdata.main.auth.services.firebase_client import (
    get_firebase_app,
    get_firestore_client,
)
from justdata.main.auth import (
    login_required,
    admin_required,
    get_current_user,
    set_user_type,
    create_or_update_user_doc,
    determine_user_type,
    get_user_permissions,
)

sync_bp = Blueprint("auth_sync", __name__)


@sync_bp.route('/resync', methods=['POST'])
@login_required
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


@sync_bp.route('/sync-all', methods=['POST'])
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

        # Phase 2: Prune orphaned Firestore docs (no matching Firebase Auth account)
        # Build set of all Firebase Auth UIDs
        auth_uids = set()
        try:
            page = firebase_auth.list_users()
            while page:
                for auth_user in page.users:
                    auth_uids.add(auth_user.uid)
                page = page.get_next_page()
        except Exception as e:
            print(f"Error building Auth UID set for pruning: {e}")

        results['pruned'] = []
        if auth_uids:  # Only prune if we successfully fetched Auth users
            for doc in db.collection('users').stream():
                uid = doc.id
                if uid not in auth_uids:
                    try:
                        user_data = doc.to_dict()
                        email = user_data.get('email', 'unknown')
                        user_type = user_data.get('userType', 'unknown')
                        # Safety: skip admin users even if orphaned
                        if user_type == 'admin':
                            print(f"Skipping orphaned admin user: {email} ({uid})")
                            continue
                        db.collection('users').document(uid).delete()
                        results['pruned'].append({
                            'email': email,
                            'uid': uid,
                            'userType': user_type
                        })
                        print(f"Pruned orphaned Firestore doc: {email} ({uid})")
                    except Exception as e:
                        results['errors'].append({
                            'email': email,
                            'error': f'Prune failed: {str(e)}'
                        })

        return jsonify({
            'success': True,
            'results': results,
            'summary': {
                'created': len(results['created']),
                'updated': len(results['updated']),
                'unchanged': len(results['unchanged']),
                'pruned': len(results.get('pruned', [])),
                'errors': len(results['errors'])
            },
            'message': f"Synced {len(results['created'])} new users, pruned {len(results.get('pruned', []))} orphaned records."
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
