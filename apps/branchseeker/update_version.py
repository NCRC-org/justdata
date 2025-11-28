#!/usr/bin/env python3
"""
Automated version updater for BranchSeeker.
Checks CHANGELOG.json for updates and automatically updates version.py.

This script:
1. Reads the latest version from CHANGELOG.json
2. Compares it with the current version in version.py
3. Updates version.py if the changelog has a newer version
4. Can be run manually or scheduled (e.g., every 12 hours)

Usage:
    python update_version.py [--check-only] [--force]
    
    --check-only: Only check if update is needed, don't update
    --force: Force update even if changelog hasn't changed recently
"""

import json
import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent
CHANGELOG_PATH = SCRIPT_DIR / 'CHANGELOG.json'
VERSION_PY_PATH = SCRIPT_DIR / 'version.py'


def load_changelog():
    """Load the changelog JSON file."""
    try:
        with open(CHANGELOG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {CHANGELOG_PATH} not found!")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {CHANGELOG_PATH}: {e}")
        sys.exit(1)


def get_latest_version_from_changelog():
    """Get the latest version from the changelog."""
    changelog = load_changelog()
    if not changelog.get('versions') or len(changelog['versions']) == 0:
        print("Error: No versions found in changelog!")
        sys.exit(1)
    
    # Versions should be ordered with latest first
    latest = changelog['versions'][0]
    return latest['version'], latest.get('date', '')


def get_current_version_from_file():
    """Get the current version from version.py."""
    try:
        with open(VERSION_PY_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract version from __version__ = "x.x.x"
            for line in content.split('\n'):
                if line.strip().startswith('__version__'):
                    # Extract version string
                    version = line.split('=')[1].strip().strip('"').strip("'")
                    return version
        return None
    except FileNotFoundError:
        print(f"Error: {VERSION_PY_PATH} not found!")
        sys.exit(1)


def check_changelog_modified_recently(hours=12):
    """Check if changelog was modified in the last N hours."""
    if not CHANGELOG_PATH.exists():
        return False
    
    mtime = datetime.fromtimestamp(CHANGELOG_PATH.stat().st_mtime)
    now = datetime.now()
    time_diff = now - mtime
    
    return time_diff <= timedelta(hours=hours)


def update_version_file(new_version, changelog_date):
    """Update version.py with the new version."""
    try:
        with open(VERSION_PY_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace the version line
        lines = content.split('\n')
        updated_lines = []
        version_updated = False
        
        for line in lines:
            if line.strip().startswith('__version__') and not version_updated:
                updated_lines.append(f'__version__ = "{new_version}"')
                version_updated = True
            else:
                updated_lines.append(line)
        
        if not version_updated:
            print("Warning: Could not find __version__ line in version.py")
            return False
        
        # Write updated content
        with open(VERSION_PY_PATH, 'w', encoding='utf-8') as f:
            f.write('\n'.join(updated_lines))
        
        return True
    except Exception as e:
        print(f"Error updating version.py: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Update version from changelog')
    parser.add_argument('--check-only', action='store_true',
                       help='Only check if update is needed, do not update')
    parser.add_argument('--force', action='store_true',
                       help='Force update even if changelog has not changed recently')
    parser.add_argument('--hours', type=int, default=12,
                       help='Hours to check back for changelog modifications (default: 12)')
    
    args = parser.parse_args()
    
    # Get versions
    changelog_version, changelog_date = get_latest_version_from_changelog()
    current_version = get_current_version_from_file()
    
    print(f"Current version in version.py: {current_version}")
    print(f"Latest version in changelog: {changelog_version} (date: {changelog_date})")
    
    # Check if versions differ
    if changelog_version == current_version:
        print("[OK] Versions match. No update needed.")
        return 0
    
    # Check if changelog was modified recently (unless forced)
    if not args.force:
        if not check_changelog_modified_recently(hours=args.hours):
            print(f"[WARNING] Changelog has not been modified in the last {args.hours} hours.")
            print("  Use --force to update anyway, or wait for changelog to be updated.")
            return 1
    
    # Check only mode
    if args.check_only:
        print(f"[INFO] Update needed: {current_version} -> {changelog_version}")
        print("  Run without --check-only to update.")
        return 1
    
    # Update version
    print(f"Updating version from {current_version} to {changelog_version}...")
    if update_version_file(changelog_version, changelog_date):
        print(f"[SUCCESS] Successfully updated version.py to {changelog_version}")
        return 0
    else:
        print("[ERROR] Failed to update version.py")
        return 1


if __name__ == '__main__':
    sys.exit(main())

