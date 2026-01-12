#!/usr/bin/env python3
"""
Version Management Utility for JustData Applications

This module provides automatic version management for pre-production applications.
Uses semantic versioning: 0.9.x where x increments with each deployment/change.

For pre-production (current state):
- Major: 0 (pre-production)
- Minor: 9 (beta/pre-release)
- Patch: Auto-incremented based on git commits or manual updates

When ready for production, version will be set to 1.0.0.
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime


def get_git_commit_count(repo_path=None):
    """
    Get the number of git commits for versioning.
    Falls back to date-based versioning if git is not available.
    """
    if repo_path is None:
        repo_path = Path(__file__).parent.parent.parent
    
    try:
        result = subprocess.run(
            ['git', 'rev-list', '--count', 'HEAD'],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    
    # Fallback: use date-based versioning (days since epoch)
    # This gives a unique number that increments daily
    days_since_epoch = (datetime.now() - datetime(2025, 1, 1)).days
    return days_since_epoch


def get_version(app_name, base_version="0.9"):
    """
    Get version string for an application.
    
    Args:
        app_name: Name of the application
        base_version: Base version (default "0.9" for pre-production)
    
    Returns:
        Version string in format "0.9.x"
    """
    repo_path = Path(__file__).parent.parent.parent
    commit_count = get_git_commit_count(repo_path)
    
    # Use commit count as patch version (modulo 1000 to keep it reasonable)
    patch = commit_count % 1000
    
    return f"{base_version}.{patch}"


def get_app_version(app_name):
    """
    Get version for a specific app, with app-specific offset if needed.
    This allows different apps to have slightly different versions
    if they were developed independently.
    """
    base_version = "0.9"
    repo_path = Path(__file__).parent.parent.parent
    
    # App-specific offsets (can be adjusted if needed)
    app_offsets = {
        'branchseeker': 0,
        'lendsight': 0,
        'bizsight': 0,
        'branchmapper': 0,
        'mergermeter': 0,
        'lenderprofile': 0,
    }
    
    offset = app_offsets.get(app_name.lower(), 0)
    commit_count = get_git_commit_count(repo_path)
    patch = (commit_count + offset) % 1000
    
    return f"{base_version}.{patch}"

