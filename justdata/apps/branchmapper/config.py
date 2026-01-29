#!/usr/bin/env python3
"""
Configuration settings for BranchMapper (Interactive bank branch map).
"""

import os

# Base directories (project root - 2 levels up from config.py: branchmapper -> apps -> root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
# Use BranchMapper-specific templates directory
BRANCHMAPPER_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')
# Fallback to shared templates if BranchMapper-specific doesn't exist
SHARED_TEMPLATES_DIR = os.path.join(BASE_DIR, 'shared', 'web', 'templates')
# Use BranchMapper templates if they exist, otherwise use shared
if os.path.exists(BRANCHMAPPER_TEMPLATES_DIR):
    TEMPLATES_DIR = BRANCHMAPPER_TEMPLATES_DIR
else:
    TEMPLATES_DIR = SHARED_TEMPLATES_DIR
STATIC_DIR = os.path.join(BASE_DIR, 'shared', 'web', 'static')

# Ensure output directory exists
OUTPUT_DIR = os.path.join(DATA_DIR, 'reports', 'branchmapper')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# BigQuery Configuration
PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'justdata-ncrc')
DATASET_ID = "branches"
TABLE_ID = "sod"

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

