#!/usr/bin/env python3
"""
Configuration settings for BranchMapper (Interactive bank branch location map).
"""

import os

# Base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'shared', 'web', 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'shared', 'web', 'static')

# Ensure output directory exists
OUTPUT_DIR = os.path.join(DATA_DIR, 'reports')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# BigQuery Configuration
PROJECT_ID = "hdma1-242116"
DATASET_ID = "branches"
TABLE_ID = "sod"

# Census API Configuration
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
    # Reload after loading .env
    CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")
except ImportError:
    pass

