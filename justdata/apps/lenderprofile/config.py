#!/usr/bin/env python3
"""
Configuration settings for LenderProfile
Comprehensive lender intelligence reporting platform.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent.parent.absolute()
DATA_DIR = BASE_DIR / 'data'
TEMPLATES_DIR = Path(__file__).parent / 'templates'
STATIC_DIR = Path(__file__).parent / 'static'

# Ensure output directory exists
OUTPUT_DIR = DATA_DIR / 'reports' / 'lenderprofile'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Application Configuration
APP_NAME = "LenderProfile"
APP_PORT = int(os.getenv('PORT', 8086))

# BigQuery Configuration (if needed)
PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'hdma1-242116')

# Cache Configuration
CACHE_ENABLED = True
CACHE_TTL_DEFAULT = 3600  # 1 hour in seconds

# Cache TTLs (in seconds)
CACHE_TTL_GLEIF = 7 * 24 * 3600  # 7 days
CACHE_TTL_FINANCIAL = 24 * 3600  # 24 hours
CACHE_TTL_BRANCH = 90 * 24 * 3600  # 90 days
CACHE_TTL_CRA = 30 * 24 * 3600  # 30 days
CACHE_TTL_COURT_SEARCH = 7 * 24 * 3600  # 7 days
CACHE_TTL_COURT_DETAILS = 30 * 24 * 3600  # 30 days
CACHE_TTL_NEWS = 24 * 3600  # 24 hours
CACHE_TTL_ORG_CHART = 7 * 24 * 3600  # 7 days
CACHE_TTL_SEC = 30 * 24 * 3600  # 30 days
CACHE_TTL_ENFORCEMENT = 24 * 3600  # 24 hours

# API Rate Limits
NEWSAPI_RATE_LIMIT = 100  # requests per day
NEWSAPI_CACHE_AGGRESSIVE = True  # Use 24-hour caching

# Logging Configuration
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Flask Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'lenderprofile-secret-key-change-in-production')

