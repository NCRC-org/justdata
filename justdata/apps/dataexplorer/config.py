#!/usr/bin/env python3
"""
Configuration settings for DataExplorer 2.0
Interactive dashboard for HMDA, Small Business, and Branch data analysis.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent.parent.absolute()
DATA_DIR = BASE_DIR / 'data'
TEMPLATES_DIR = Path(__file__).parent / 'templates'
STATIC_DIR = Path(__file__).parent / 'static'

# Ensure output directory exists
OUTPUT_DIR = DATA_DIR / 'reports' / 'dataexplorer'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# BigQuery Configuration
PROJECT_ID = "hdma1-242116"
HMDA_DATASET = "hmda"
HMDA_TABLE = "hmda"
SB_DATASET = "sb"
SB_DISCLOSURE_TABLE = "disclosure"
SB_AGGREGATE_TABLE = "aggregate"
BRANCHES_DATASET = "branches"
BRANCHES_TABLE = "sod25"

# Data Type Configuration
HMDA_YEARS = list(range(2018, 2025))  # 2018-2024 (most recent is 2024)
SB_YEARS = list(range(2019, 2024))  # 2019-2023
BRANCH_YEARS = list(range(2017, 2026))  # 2017-2025

# Input Validation Limits (CRITICAL - prevents resource exhaustion)
MAX_YEARS = 10  # Maximum years per query
MAX_GEOIDS = 100  # Maximum counties/tracts per query
MAX_LENDERS = 50  # Maximum lenders for peer comparison

# Default Filters
DEFAULT_ACTION_TAKEN = ['1']  # Only originations (FIXED from v1)
DEFAULT_EXCLUDE_REVERSE_MORTGAGES = True  # Exclude reverse mortgages
DEFAULT_EXCLUDE_REVERSE_MORTGAGE_CODES = ['1', '1111']  # Both codes (FIXED from v1)

# Loan Purpose Codes
LOAN_PURPOSE_PURCHASE = '1'
LOAN_PURPOSE_REFINANCE = '2'
LOAN_PURPOSE_HOME_IMPROVEMENT = '3'

# Action Taken Codes
ACTION_TAKEN_ORIGINATED = '1'
ACTION_TAKEN_APPROVED_NOT_ACCEPTED = '2'
ACTION_TAKEN_DENIED = '3'
ACTION_TAKEN_WITHDRAWN = '4'
ACTION_TAKEN_FILE_CLOSED = '5'
ACTION_TAKEN_PURCHASED = '6'
ACTION_TAKEN_PREAPPROVED_DENIED = '7'
ACTION_TAKEN_PREAPPROVED_APPROVED_NOT_ACCEPTED = '8'

# Occupancy Codes
OCCUPANCY_PRINCIPAL_RESIDENCE = '1'
OCCUPANCY_SECOND_RESIDENCE = '2'
OCCUPANCY_INVESTMENT = '3'

# Property Type Codes
PROPERTY_TYPE_ONE_TO_FOUR_FAMILY = '1'
PROPERTY_TYPE_MANUFACTURED_HOME = '2'
PROPERTY_TYPE_MULTIFAMILY = '3'

# Peer Comparison Configuration
PEER_VOLUME_MIN_PERCENT = 0.5  # 50% of subject lender volume
PEER_VOLUME_MAX_PERCENT = 2.0  # 200% of subject lender volume
DEFAULT_PEER_COUNT = 10  # Default number of peers

# Export Configuration
EXCEL_MAX_ROWS = 1000000  # Maximum rows for Excel export
PDF_MAX_PAGES = 1000  # Maximum pages for PDF export

# Logging Configuration
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
LOG_QUERIES = os.getenv('LOG_QUERIES', 'false').lower() == 'true'
QUERY_LOG_FILE = BASE_DIR / 'dataexplorer_query_log.sql'

# Cache Configuration
CACHE_ENABLED = True
CACHE_TTL = 3600  # 1 hour in seconds
