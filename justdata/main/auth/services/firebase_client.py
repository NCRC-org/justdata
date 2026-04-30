"""
Firebase Admin SDK client and wrapper functions.

Pure SDK plumbing:
- init_firebase: initialize the Admin SDK from environment credentials
- get_firebase_app: get-or-init the singleton app
- get_firestore_client: get-or-init the singleton Firestore client
- verify_firebase_token: thin wrapper around firebase_auth.verify_id_token
- get_user_doc: thin Firestore-read wrapper for the users collection

Domain logic (membership lookups, user-type computation, activity logging) lives
elsewhere in justdata.main.auth and is not duplicated here.
"""

import os
import json
from typing import Optional

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth, firestore


# Module-level singletons
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
