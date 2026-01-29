#!/usr/bin/env python3
"""
Configuration settings for LendSight (HMDA mortgage lending analyzer).
"""

import os

# Base directories (project root - 2 levels up from config.py: lendsight -> apps -> root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
# Use LendSight-specific templates directory
LENDSIGHT_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')
# Fallback to shared templates if LendSight-specific doesn't exist
SHARED_TEMPLATES_DIR = os.path.join(BASE_DIR, 'shared', 'web', 'templates')
# Use LendSight templates if they exist, otherwise use shared
import os.path
if os.path.exists(LENDSIGHT_TEMPLATES_DIR):
    TEMPLATES_DIR = LENDSIGHT_TEMPLATES_DIR
else:
    TEMPLATES_DIR = SHARED_TEMPLATES_DIR
# Use LendSight-specific static directory (like bizsight)
LENDSIGHT_STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
# Fallback to shared static if LendSight-specific doesn't exist
SHARED_STATIC_DIR = os.path.join(BASE_DIR, 'shared', 'web', 'static')
if os.path.exists(LENDSIGHT_STATIC_DIR):
    STATIC_DIR = LENDSIGHT_STATIC_DIR
else:
    STATIC_DIR = SHARED_STATIC_DIR

# Ensure output directory exists
OUTPUT_DIR = os.path.join(DATA_DIR, 'reports', 'lendsight')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# AI Configuration
AI_PROVIDER = os.getenv("AI_PROVIDER", "claude")  # Options: "gpt-4", "claude"
CLAUDE_MODEL = "claude-sonnet-4-20250514"
GPT_MODEL = "gpt-4"

# BigQuery Configuration
# Use environment variable for flexible project switching during migration
# Set JUSTDATA_PROJECT_ID=justdata to use new optimized project
# Default to old project for backward compatibility
PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'justdata-ncrc')
SUMMARY_PROJECT_ID = os.getenv('JUSTDATA_PROJECT_ID', 'justdata-ncrc')  # New optimized project
USE_SUMMARY_TABLES = os.getenv('USE_SUMMARY_TABLES', 'false').lower() == 'true'
DATASET_ID = "hmda"
TABLE_ID = "hmda"

# Report Configuration
DEFAULT_YEARS = list(range(2020, 2025))  # 2020-2024 (HMDA data)
MAX_LENDERS_DISPLAY = 10

# API Keys
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
    # Reload after loading .env
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
except ImportError:
    pass

