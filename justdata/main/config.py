"""
Configuration for main JustData application.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent.parent
TEMPLATES_DIR = BASE_DIR / 'justdata' / 'shared' / 'web' / 'templates'
STATIC_DIR = BASE_DIR / 'justdata' / 'shared' / 'web' / 'static'


class MainConfig:
    """Main application configuration."""
    
    APP_NAME = "JustData"
    APP_VERSION = "1.0.0"
    
    TEMPLATES_DIR = str(TEMPLATES_DIR)
    STATIC_DIR = str(STATIC_DIR)
    
    SECRET_KEY = os.getenv('SECRET_KEY', 'justdata-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    PORT = int(os.getenv('PORT', 8000))
    HOST = os.getenv('HOST', '0.0.0.0')

