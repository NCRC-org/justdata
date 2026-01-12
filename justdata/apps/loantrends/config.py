#!/usr/bin/env python3
"""
Configuration settings for LoanTrends (HMDA quarterly trends analyzer).
"""

import os

# Base directories (project root - 2 levels up from config.py: loantrends -> apps -> root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')
# Use LoanTrends-specific templates directory
LOANTRENDS_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')
# Fallback to shared templates if LoanTrends-specific doesn't exist
SHARED_TEMPLATES_DIR = os.path.join(BASE_DIR, 'shared', 'web', 'templates')
# Use LoanTrends templates if they exist, otherwise use shared
import os.path
if os.path.exists(LOANTRENDS_TEMPLATES_DIR):
    TEMPLATES_DIR = LOANTRENDS_TEMPLATES_DIR
else:
    TEMPLATES_DIR = SHARED_TEMPLATES_DIR
# Use LoanTrends-specific static directory
LOANTRENDS_STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
# Fallback to shared static if LoanTrends-specific doesn't exist
SHARED_STATIC_DIR = os.path.join(BASE_DIR, 'shared', 'web', 'static')
if os.path.exists(LOANTRENDS_STATIC_DIR):
    STATIC_DIR = LOANTRENDS_STATIC_DIR
else:
    STATIC_DIR = SHARED_STATIC_DIR

# Ensure output directory exists
OUTPUT_DIR = os.path.join(DATA_DIR, 'reports', 'loantrends')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# AI Configuration
AI_PROVIDER = os.getenv("AI_PROVIDER", "claude")  # Options: "gpt-4", "claude"
CLAUDE_MODEL = "claude-sonnet-4-20250514"
GPT_MODEL = "gpt-4"

# Quarterly API Configuration
QUARTERLY_API_BASE_URL = "https://ffiec.cfpb.gov/quarterly-data/graphs"
QUARTERLY_API_TIMEOUT = 30  # seconds

# Available graph endpoints (from API documentation)
GRAPH_ENDPOINTS = {
    'Loan & Application Counts': [
        'applications',
        'loans'
    ],
    'Credit Score': [
        'credit-scores',
        'credit-scores-cc-re',
        'credit-scores-fha-re'
    ],
    'Loan-to-Value (LTV)': [
        'ltv',
        'ltv-cc-re',
        'ltv-fha-re'
    ],
    'Debt-to-Income (DTI)': [
        'dti',
        'dti-cc-re',
        'dti-fha-re'
    ],
    'Denial Rates': [
        'denials',
        'denials-cc-re',
        'denials-fha-re'
    ],
    'Interest Rates': [
        'interest-rates',
        'interest-rates-cc-re',
        'interest-rates-fha-re'
    ],
    'Total Loan Costs (TLC)': [
        'tlc',
        'tlc-cc-re',
        'tlc-fha-re'
    ]
}

# Default time period (last 12 quarters / 3 years)
DEFAULT_TIME_PERIOD = "all"  # "all" (last 12 quarters), "recent" (last 12 quarters), or "custom" (specific range)

# Report Configuration
MAX_SERIES_DISPLAY = 10  # Maximum number of series to display in tables

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




