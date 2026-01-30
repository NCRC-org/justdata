#!/usr/bin/env python3
"""
Migrate Firestore 'users' collection from justdata-f7da7 to justdata-ncrc.

This script:
1. Connects to both Firebase projects
2. Reads all documents from the old 'users' collection
3. Writes them to the new 'users' collection (merge mode - won't overwrite existing)

Prerequisites:
- Service account JSON files for both projects with Firestore access
- pip install firebase-admin

Usage:
    python 25_migrate_firestore_users.py --old-creds /path/to/f7da7-creds.json --new-creds /path/to/ncrc-creds.json
    
Or using environment variables:
    export OLD_FIREBASE_CREDENTIALS_JSON='{"type": "service_account", ...}'
    export FIREBASE_CREDENTIALS_JSON='{"type": "service_account", ...}'  # for justdata-ncrc
    python 25_migrate_firestore_users.py
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Load .env file if it exists
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    print(f"Loading environment from {env_path}")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                # Remove quotes if present
                value = value.strip().strip('"').strip("'")
                if key and value:
                    os.environ.setdefault(key, value)

import firebase_admin
from firebase_admin import credentials, firestore


def get_credentials_from_env_or_file(env_var: str, file_path: str = None) -> dict:
    """Get Firebase credentials from environment variable or file."""
    # Try environment variable first (as JSON string)
    env_value = os.environ.get(env_var)
    if env_value:
        try:
            return json.loads(env_value)
        except json.JSONDecodeError:
            # Maybe it's a file path
            if os.path.exists(env_value):
                with open(env_value, 'r') as f:
                    return json.load(f)
    
    # Try file path
    if file_path and os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    
    return None


def migrate_users(old_creds_path: str = None, new_creds_path: str = None, dry_run: bool = False):
    """
    Migrate users collection from old Firebase project to new one.
    
    Args:
        old_creds_path: Path to service account JSON for justdata-f7da7
        new_creds_path: Path to service account JSON for justdata-ncrc
        dry_run: If True, only show what would be migrated without writing
    """
    
    # Get credentials for old project (justdata-f7da7)
    old_creds_dict = get_credentials_from_env_or_file('OLD_FIREBASE_CREDENTIALS_JSON', old_creds_path)
    if not old_creds_dict:
        print("ERROR: Could not find credentials for old Firebase project (justdata-f7da7)")
        print("  Set OLD_FIREBASE_CREDENTIALS_JSON env var or pass --old-creds /path/to/file.json")
        sys.exit(1)
    
    # Get credentials for new project (justdata-ncrc)
    new_creds_dict = get_credentials_from_env_or_file('FIREBASE_CREDENTIALS_JSON', new_creds_path)
    if not new_creds_dict:
        print("ERROR: Could not find credentials for new Firebase project (justdata-ncrc)")
        print("  Set FIREBASE_CREDENTIALS_JSON env var or pass --new-creds /path/to/file.json")
        sys.exit(1)
    
    old_project = old_creds_dict.get('project_id', 'unknown')
    new_project = new_creds_dict.get('project_id', 'unknown')
    
    print(f"=" * 60)
    print(f"Firestore Users Migration")
    print(f"=" * 60)
    print(f"Source:      {old_project}")
    print(f"Destination: {new_project}")
    print(f"Dry run:     {dry_run}")
    print(f"=" * 60)
    
    # Initialize old Firebase app
    old_cred = credentials.Certificate(old_creds_dict)
    old_app = firebase_admin.initialize_app(old_cred, name='old_project')
    old_db = firestore.client(app=old_app)
    
    # Initialize new Firebase app
    new_cred = credentials.Certificate(new_creds_dict)
    new_app = firebase_admin.initialize_app(new_cred, name='new_project')
    new_db = firestore.client(app=new_app)
    
    # Read all users from old project
    print(f"\nReading users from {old_project}...")
    old_users_ref = old_db.collection('users')
    old_users = list(old_users_ref.stream())
    print(f"Found {len(old_users)} users in source project")
    
    if not old_users:
        print("No users to migrate. Exiting.")
        return
    
    # Check existing users in new project
    print(f"\nChecking existing users in {new_project}...")
    new_users_ref = new_db.collection('users')
    existing_ids = set()
    for doc in new_users_ref.stream():
        existing_ids.add(doc.id)
    print(f"Found {len(existing_ids)} existing users in destination project")
    
    # Migrate users
    migrated = 0
    skipped = 0
    errors = 0
    
    print(f"\n{'DRY RUN - ' if dry_run else ''}Migrating users...")
    print("-" * 60)
    
    for user_doc in old_users:
        user_id = user_doc.id
        user_data = user_doc.to_dict()
        
        # Add migration metadata
        user_data['_migrated_from'] = old_project
        user_data['_migrated_at'] = datetime.now(timezone.utc).isoformat()
        
        email = user_data.get('email', 'no-email')
        user_type = user_data.get('userType', 'unknown')
        
        if user_id in existing_ids:
            print(f"  SKIP (exists): {user_id[:20]}... | {email}")
            skipped += 1
            continue
        
        try:
            if not dry_run:
                # Use set with merge=True to avoid overwriting if doc was created between check and write
                new_users_ref.document(user_id).set(user_data, merge=True)
            print(f"  {'WOULD MIGRATE' if dry_run else 'MIGRATED'}: {user_id[:20]}... | {email} | {user_type}")
            migrated += 1
        except Exception as e:
            print(f"  ERROR: {user_id[:20]}... | {e}")
            errors += 1
    
    # Summary
    print("-" * 60)
    print(f"\nMigration Summary:")
    print(f"  Total in source:    {len(old_users)}")
    print(f"  Already existed:    {skipped}")
    print(f"  {'Would migrate' if dry_run else 'Migrated'}:       {migrated}")
    print(f"  Errors:             {errors}")
    
    if dry_run:
        print(f"\nThis was a DRY RUN. Run without --dry-run to actually migrate.")
    else:
        print(f"\nMigration complete!")
    
    # Cleanup
    firebase_admin.delete_app(old_app)
    firebase_admin.delete_app(new_app)


def main():
    parser = argparse.ArgumentParser(
        description='Migrate Firestore users collection from justdata-f7da7 to justdata-ncrc'
    )
    parser.add_argument(
        '--old-creds',
        help='Path to service account JSON for old project (justdata-f7da7)'
    )
    parser.add_argument(
        '--new-creds', 
        help='Path to service account JSON for new project (justdata-ncrc)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be migrated without actually writing'
    )
    
    args = parser.parse_args()
    
    migrate_users(
        old_creds_path=args.old_creds,
        new_creds_path=args.new_creds,
        dry_run=args.dry_run
    )


if __name__ == '__main__':
    main()
