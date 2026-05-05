"""
Auth organization & membership routes.

Routes:
- POST /set-organization              — Set the user's organization (non-NCRC users)
- GET  /membership-status             — Current user's membership status (HubSpot-derived)
- GET  /member-request/status         — Member-request status for the prompt modal
- POST /member-request/dismiss-prompt — No-op dismiss for 'Continue as guest'
"""

from flask import Blueprint, request, jsonify

from justdata.main.auth.services.firebase_client import (
    get_firestore_client,
    get_user_doc,
)
from justdata.main.auth import (
    login_required,
    get_current_user,
)

organizations_bp = Blueprint("auth_organizations", __name__)


@organizations_bp.route('/set-organization', methods=['POST'])
@login_required
def set_user_organization():
    """
    Set the user's organization (for non-NCRC users on first login).
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    organization = data.get('organization', '').strip()
    if not organization:
        return jsonify({'error': 'Organization is required'}), 400

    uid = user.get('uid')
    email = user.get('email', '')

    # Don't allow changing organization for NCRC users
    if email.lower().endswith('@ncrc.org'):
        return jsonify({'error': 'NCRC users cannot change organization'}), 400

    db = get_firestore_client()
    if not db:
        return jsonify({'error': 'Database not available'}), 500

    try:
        db.collection('users').document(uid).update({
            'organization': organization,
            'needsOrganization': False
        })

        return jsonify({
            'success': True,
            'organization': organization,
            'message': 'Organization updated successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@organizations_bp.route('/membership-status', methods=['GET'])
@login_required
def get_membership_status():
    """
    Get the current user's membership status from HubSpot lookup.
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
                'is_member': False,
                'membership_status': None,
                'organization': None
            })

        return jsonify({
            'is_member': user_doc.get('userType') in ['member', 'member_premium', 'staff', 'senior_executive', 'admin'],
            'membership_status': user_doc.get('hubspot_membership_status'),
            'organization': user_doc.get('organization') or user_doc.get('hubspot_company_name'),
            'hubspot_contact_id': user_doc.get('hubspot_contact_id'),
            'hubspot_company_id': user_doc.get('hubspot_company_id'),
            'lookup_method': user_doc.get('hubspot_lookup_method'),
            'email_template': user_doc.get('email_template_sent')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@organizations_bp.route('/member-request/status', methods=['GET'])
@login_required
def get_member_request_status():
    """
    Return member-request status in the shape expected by member_request_modal.html.
    Prevents 404 and HTML-vs-JSON parse errors. Maps from membership-status logic.
    """
    user = get_current_user()
    if not user:
        return jsonify({
            'memberRequestStatus': 'anonymous',
            'hasSeenMemberPrompt': True,
            'membershipStatus': None
        })

    uid = user.get('uid')
    db = get_firestore_client()
    if not db:
        return jsonify({
            'memberRequestStatus': 'unknown',
            'hasSeenMemberPrompt': True,
            'membershipStatus': None
        })

    try:
        user_doc = get_user_doc(uid)
        if not user_doc:
            return jsonify({
                'memberRequestStatus': 'unknown',
                'hasSeenMemberPrompt': True,
                'membershipStatus': None
            })

        user_type = user_doc.get('userType') or ''
        member_types = ['member', 'member_premium', 'non_member_org', 'staff', 'senior_executive', 'admin']
        is_member = user_type in member_types
        hubspot_status = (user_doc.get('hubspot_membership_status') or '').strip().upper()
        has_seen = user_doc.get('hasSeenMemberPrompt', True)

        if is_member:
            member_request_status = 'member'
        elif hubspot_status == 'PENDING':
            member_request_status = 'pending'
        elif hubspot_status in ('DENIED', 'EXPIRED'):
            member_request_status = 'denied'
        else:
            member_request_status = 'unknown'

        membership_status = user_doc.get('hubspot_membership_status') or None
        if membership_status and isinstance(membership_status, str):
            membership_status = membership_status.strip() or None

        return jsonify({
            'memberRequestStatus': member_request_status,
            'hasSeenMemberPrompt': bool(has_seen),
            'membershipStatus': membership_status
        })
    except Exception as e:
        return jsonify({
            'memberRequestStatus': 'unknown',
            'hasSeenMemberPrompt': True,
            'membershipStatus': None
        })


@organizations_bp.route('/member-request/dismiss-prompt', methods=['POST'])
@login_required
def dismiss_member_prompt():
    """No-op for 'Continue as guest'; prevents 404 when modal dismisses."""
    return jsonify({'ok': True})
