"""
Configuration for MemberView app.
"""

from pathlib import Path

# App directories
APP_DIR = Path(__file__).parent
TEMPLATES_DIR = APP_DIR / 'templates'
STATIC_DIR = APP_DIR / 'static'

# Ensure directories exist
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
