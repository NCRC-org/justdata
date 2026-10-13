#!/usr/bin/env python3
"""
Configuration settings for BranchSight (FDIC bank branch analyzer).
"""

import os

# Base directories (project root - 2 levels up from config.py: branchsight -> apps -> root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
# Use BranchSight-specific templates directory
BRANCHSIGHT_DIR = os.path.dirname(os.path.abspath(__file__))
BRANCHSIGHT_TEMPLATES_DIR = os.path.join(BRANCHSIGHT_DIR, 'templates')
# Fallback to shared templates if BranchSight-specific doesn't exist
SHARED_TEMPLATES_DIR = os.path.join(BASE_DIR, 'shared', 'web', 'templates')
# Use BranchSight templates if they exist, otherwise use shared
if os.path.exists(BRANCHSIGHT_TEMPLATES_DIR):
    TEMPLATES_DIR = BRANCHSIGHT_TEMPLATES_DIR
else:
    TEMPLATES_DIR = SHARED_TEMPLATES_DIR
# Use BranchSight-specific static directory (like lendsight and bizsight)
BRANCHSIGHT_STATIC_DIR = os.path.join(BRANCHSIGHT_DIR, 'static')
# Fallback to shared static if BranchSight-specific doesn't exist
SHARED_STATIC_DIR = os.path.join(BASE_DIR, 'shared', 'web', 'static')
if os.path.exists(BRANCHSIGHT_STATIC_DIR):
    STATIC_DIR = BRANCHSIGHT_STATIC_DIR
else:
    STATIC_DIR = SHARED_STATIC_DIR

# Ensure output directory exists (with fallback for read-only Cloud Run filesystem)
OUTPUT_DIR = os.path.join(DATA_DIR, 'reports')
try:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
except (PermissionError, OSError):
    OUTPUT_DIR = os.path.join('/tmp', 'branchsight_reports')
    os.makedirs(OUTPUT_DIR, exist_ok=True)

# AI Configuration
AI_PROVIDER = os.getenv("AI_PROVIDER", "claude")
CLAUDE_MODEL = "claude-sonnet-5"

# BigQuery Configuration - Use JUSTDATA_PROJECT_ID since tables are in justdata-ncrc
PROJECT_ID = os.getenv('JUSTDATA_PROJECT_ID', 'justdata-ncrc')
SUMMARY_PROJECT_ID = os.getenv('JUSTDATA_PROJECT_ID', 'justdata-ncrc')  # New optimized project
DATASET_ID = "branchsight"
TABLE_ID = "sod"

# Report Configuration
# FDIC Summary of Deposits years the analysis runs. 2025 is the latest year
# loaded (branchsight.sod); 2017 to 2024 are in branchsight.sod_legacy.
# The page, header vintage, request and cache key all read SOD_YEARS.
SOD_LATEST_YEAR = 2025
SOD_YEARS = list(range(SOD_LATEST_YEAR - 4, SOD_LATEST_YEAR + 1))
DEFAULT_YEARS = SOD_YEARS
MAX_BANKS_DISPLAY = 10

# API Keys
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
    # Reload after loading .env
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
except ImportError:
    pass

