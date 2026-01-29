#!/usr/bin/env python3
"""
BizSight Application Configuration
Self-contained configuration for BizSight application.
"""

import os
from pathlib import Path

# Get the base directory (this file's parent directory)
BASE_DIR = Path(__file__).parent.parent.absolute()
BIZSIGHT_DIR = Path(__file__).parent.absolute()

# Data directories
DATA_DIR = BASE_DIR / 'data'
REPORTS_DIR = DATA_DIR / 'reports'
CREDENTIALS_DIR = BASE_DIR / 'credentials'

# Template and static directories
TEMPLATES_DIR = BIZSIGHT_DIR / 'templates'
STATIC_DIR = BIZSIGHT_DIR / 'static'

# String versions for Flask
TEMPLATES_DIR_STR = str(TEMPLATES_DIR)
STATIC_DIR_STR = str(STATIC_DIR)

# Ensure directories exist (use try/except for read-only file systems like Cloud Run)
try:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    # Use /tmp for Cloud Run
    REPORTS_DIR = Path('/tmp/bizsight/reports')
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

try:
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    # Use /tmp for Cloud Run
    CREDENTIALS_DIR = Path('/tmp/bizsight/credentials')
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

try:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    # Static dir should already exist, ignore
    pass

class BizSightConfig:
    """Configuration for BizSight application."""
    
    # Application Info
    APP_NAME = "BizSight"
    # Import version from version.py for consistency
    try:
        from apps.bizsight.version import __version__ as VERSION
        APP_VERSION = VERSION
    except ImportError:
        APP_VERSION = "0.9.0"  # Fallback
    
    # Base directories (keep as Path objects for path operations)
    BASE_DIR_STR = str(BASE_DIR)
    DATA_DIR_STR = str(DATA_DIR)
    REPORTS_DIR_STR = str(REPORTS_DIR)
    CREDENTIALS_DIR_STR = str(CREDENTIALS_DIR)
    
    # For backward compatibility, also provide string versions
    BASE_DIR = BASE_DIR_STR
    DATA_DIR = DATA_DIR_STR
    REPORTS_DIR = REPORTS_DIR_STR
    CREDENTIALS_DIR = CREDENTIALS_DIR_STR
    
    # BigQuery Configuration
    GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'justdata-ncrc')
    DATASET_ID = 'sb'  # Small Business dataset
    AGGREGATE_TABLE = 'aggregate'  # Tract-level data
    DISCLOSURE_TABLE = 'disclosure'  # Lender-level data (county level)
    LENDERS_TABLE = 'lenders'  # Lender information
    GEO_TABLE = 'geo.cbsa_to_county'  # Geographic mapping
    
    # BigQuery Credentials (use os.path.join for compatibility)
    _default_credentials = os.path.join(CREDENTIALS_DIR_STR, 'bigquery_service_account.json')
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
        'GOOGLE_APPLICATION_CREDENTIALS',
        _default_credentials
    )
    
    # AI Configuration
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'claude')
    # Try multiple environment variable names for Claude API key
    CLAUDE_API_KEY = (
        os.getenv('CLAUDE_API_KEY') or 
        os.getenv('ANTHROPIC_API_KEY') or
        os.getenv('CLAUDE_AI_API_KEY')
    )
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')
    GPT_MODEL = os.getenv('GPT_MODEL', 'gpt-4')
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'bizsight-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    PORT = int(os.getenv('PORT', 8081))
    HOST = os.getenv('HOST', '0.0.0.0')
    
    # Analysis Configuration
    DEFAULT_YEARS = list(range(2019, 2024))  # 2019-2023 (typical SB data range)
    MAX_COUNTIES = 3
    MIN_YEARS = 3
    
    # Output Configuration
    OUTPUT_DIR = REPORTS_DIR
    
    @classmethod
    def validate(cls):
        """Validate configuration."""
        errors = []
        
        # Check for Claude API key (only if using Claude)
        if cls.AI_PROVIDER == 'claude' and not cls.CLAUDE_API_KEY:
            errors.append("CLAUDE_API_KEY not set (check root .env file or set environment variable)")
        
        # Check for OpenAI API key (only if using OpenAI)
        if cls.AI_PROVIDER == 'openai' and not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY not set (check root .env file or set environment variable)")
        
        # Check if credentials file exists (only if not set via env var)
        # Allow missing credentials if GOOGLE_APPLICATION_CREDENTIALS is set via env var
        if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            if not os.path.exists(cls.GOOGLE_APPLICATION_CREDENTIALS):
                errors.append(f"BigQuery credentials not found: {cls.GOOGLE_APPLICATION_CREDENTIALS}")
                errors.append("  (You can set GOOGLE_APPLICATION_CREDENTIALS environment variable to point to your credentials file)")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
        
        return True

