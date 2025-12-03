#!/usr/bin/env python3
"""
Configuration settings for BranchSeeker (FDIC bank branch analyzer).
"""

import os

# Base directories (project root - 2 levels up from config.py: branchseeker -> apps -> root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
# Use BranchSeeker-specific templates directory (use absolute path)
BRANCHSEEKER_TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
# Fallback to shared templates if BranchSeeker-specific doesn't exist
SHARED_TEMPLATES_DIR = os.path.abspath(os.path.join(BASE_DIR, 'shared', 'web', 'templates'))
# Use BranchSeeker templates if they exist, otherwise use shared
if os.path.exists(BRANCHSEEKER_TEMPLATES_DIR):
    TEMPLATES_DIR = BRANCHSEEKER_TEMPLATES_DIR
else:
    TEMPLATES_DIR = SHARED_TEMPLATES_DIR
STATIC_DIR = os.path.join(BASE_DIR, 'shared', 'web', 'static')

# Ensure output directory exists
OUTPUT_DIR = os.path.join(DATA_DIR, 'reports')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# AI Configuration
AI_PROVIDER = os.getenv("AI_PROVIDER", "claude")  # Options: "gpt-4", "claude"
CLAUDE_MODEL = "claude-sonnet-4-20250514"
GPT_MODEL = "gpt-4"

# BigQuery Configuration
PROJECT_ID = "hdma1-242116"
DATASET_ID = "branches"
TABLE_ID = "sod"

# Report Configuration
DEFAULT_YEARS = list(range(2017, 2025))  # 2017-2024
MAX_BANKS_DISPLAY = 10

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

