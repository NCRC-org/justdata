#!/usr/bin/env python3
"""
Configuration settings for DataExplorer dashboard.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent.parent.absolute()
DATA_DIR = BASE_DIR / 'data'
REPORTS_DIR = DATA_DIR / 'reports' / 'dataexplorer'
CREDENTIALS_DIR = BASE_DIR / 'credentials'

# Template and static directories
TEMPLATES_DIR = BASE_DIR / 'apps' / 'dataexplorer' / 'templates'
STATIC_DIR = BASE_DIR / 'apps' / 'dataexplorer' / 'static'

# String versions for Flask
TEMPLATES_DIR_STR = str(TEMPLATES_DIR)
STATIC_DIR_STR = str(STATIC_DIR)

# Ensure directories exist
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

class DataExplorerConfig:
    """Configuration for DataExplorer application."""
    
    # Application Info
    APP_NAME = "DataExplorer"
    APP_VERSION = "1.0.0"
    
    # Base directories
    BASE_DIR_STR = str(BASE_DIR)
    DATA_DIR_STR = str(DATA_DIR)
    REPORTS_DIR_STR = str(REPORTS_DIR)
    CREDENTIALS_DIR_STR = str(CREDENTIALS_DIR)
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dataexplorer-secret-key-change-this')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    PORT = int(os.getenv('PORT', '8085'))
    
    # BigQuery Configuration
    GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'hdma1-242116')
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    # Data Source Configuration
    HMDA_DATASET = 'hmda'
    HMDA_TABLE = 'hmda'
    SB_DATASET = 'sb'
    SB_DISCLOSURE_TABLE = 'disclosure'
    SB_AGGREGATE_TABLE = 'aggregate'
    SB_LENDERS_TABLE = 'lenders'
    BRANCHES_DATASET = 'branches'
    BRANCHES_TABLE = 'sod25'  # Latest SOD table
    GEO_DATASET = 'geo'
    GEO_CBSA_TABLE = 'cbsa_to_county'
    GEO_CENSUS_TABLE = 'census'
    
    # Available Years
    HMDA_YEARS = list(range(2018, 2025))  # 2018-2024
    SB_YEARS = list(range(2018, 2025))  # 2018-2024
    BRANCH_YEARS = list(range(2017, 2026))  # 2017-2025
    
    # Peer Comparison Configuration
    PEER_VOLUME_MIN = 0.5  # 50% of subject volume
    PEER_VOLUME_MAX = 2.0  # 200% of subject volume
    
    # Default Filters
    DEFAULT_HMDA_LOAN_PURPOSE = ['1']  # Home purchase
    DEFAULT_HMDA_ACTION_TAKEN = ['1']  # Originations only
    DEFAULT_HMDA_OCCUPANCY = ['1']  # Owner-occupied
    DEFAULT_HMDA_UNITS = ['1', '2', '3', '4']  # 1-4 units
    DEFAULT_HMDA_CONSTRUCTION = ['1']  # Site-built
    DEFAULT_HMDA_EXCLUDE_REVERSE = True  # Exclude reverse mortgages (match Tableau)
    
    # Load environment variables from .env if available
    # Check both current directory and parent DREAM Analysis directory
    try:
        from dotenv import load_dotenv
        # Try loading from current directory first
        load_dotenv()
        # Also try loading from parent DREAM Analysis directory (absolute path)
        dream_analysis_env = Path(r"C:\Users\edite\OneDrive - Nat'l Community Reinvestment Coaltn\Desktop\DREAM Analysis\.env")
        if dream_analysis_env.exists():
            load_dotenv(dream_analysis_env, override=False)  # Don't override if already set
        # Reload after loading .env
        SECRET_KEY = os.getenv('SECRET_KEY', SECRET_KEY)
        GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', GCP_PROJECT_ID)
        GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    except ImportError:
        pass

