#!/usr/bin/env python3
"""
Configuration settings for ElectWatch
Monitor elected officials' financial relationships with the financial industry.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent.parent.absolute()
APP_DIR = Path(__file__).parent.absolute()
DATA_DIR = BASE_DIR / 'data'
TEMPLATES_DIR = APP_DIR / 'templates'
STATIC_DIR = APP_DIR / 'static'

# Ensure output directory exists
OUTPUT_DIR = DATA_DIR / 'reports' / 'electwatch'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# String paths for Flask
TEMPLATES_DIR_STR = str(TEMPLATES_DIR)
STATIC_DIR_STR = str(STATIC_DIR)


class ElectWatchConfig:
    """Configuration for ElectWatch application."""

    APP_NAME = "ElectWatch"
    APP_VERSION = "0.9.0"
    APP_PORT = int(os.getenv('PORT', 8083))

    # Base directories
    BASE_DIR_STR = str(BASE_DIR)
    DATA_DIR_STR = str(DATA_DIR)
    OUTPUT_DIR_STR = str(OUTPUT_DIR)

    # BigQuery Configuration
    GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'justdata-ncrc')
    DATASET_ID = 'elected_officials'

    # FEC API Configuration
    FEC_API_KEY = os.getenv('FEC_API_KEY')
    FEC_API_BASE = 'https://api.open.fec.gov/v1'

    # Quiver API (Congressional Trading)
    QUIVER_API_KEY = os.getenv('QUIVER_API_KEY')
    QUIVER_API_BASE = 'https://api.quiverquant.com/beta'

    # Congress.gov API (Bills & Votes)
    CONGRESS_GOV_API_KEY = os.getenv('CONGRESS_GOV_API_KEY')
    CONGRESS_API_BASE = 'https://api.congress.gov/v3'

    # AI Configuration
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'claude')
    CLAUDE_API_KEY = (
        os.getenv('CLAUDE_API_KEY') or
        os.getenv('ANTHROPIC_API_KEY') or
        os.getenv('CLAUDE_AI_API_KEY')
    )
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')

    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'electwatch-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    HOST = os.getenv('HOST', '0.0.0.0')

    # Cache Configuration
    CACHE_ENABLED = True
    CACHE_TTL_CONTRIBUTIONS = 6 * 3600  # 6 hours
    CACHE_TTL_STOCK_TRADES = 12 * 3600  # 12 hours
    CACHE_TTL_COMMITTEES = 7 * 24 * 3600  # 7 days
    CACHE_TTL_FIRM_MAPPING = 30 * 24 * 3600  # 30 days

    # Data Window
    DATA_START_DATE = '2025-01-01'  # Track from Jan 1, 2025

    # House Committee PDF Path
    HOUSE_COMMITTEE_PDF = str(Path('C:/Code/House Committee Member Assignments.pdf'))

    @classmethod
    def validate(cls):
        """Validate configuration."""
        errors = []
        warnings = []

        if not cls.FEC_API_KEY:
            errors.append("FEC_API_KEY not set - cannot fetch contribution data")

        if not cls.QUIVER_API_KEY:
            warnings.append("QUIVER_API_KEY not set - stock trading data unavailable")

        if cls.AI_PROVIDER == 'claude' and not cls.CLAUDE_API_KEY:
            warnings.append("CLAUDE_API_KEY not set - AI insights unavailable")

        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

        for w in warnings:
            print(f"[CONFIG WARNING] {w}")

        return True

    @classmethod
    def get_fec_headers(cls):
        """Get headers for FEC API requests."""
        return {
            'Accept': 'application/json',
            'User-Agent': 'NCRC-ElectWatch/0.9.0'
        }

    @classmethod
    def get_fec_params(cls, **kwargs):
        """Get params for FEC API requests with API key."""
        params = {'api_key': cls.FEC_API_KEY}
        params.update(kwargs)
        return params
