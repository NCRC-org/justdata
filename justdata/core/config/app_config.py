#!/usr/bin/env python3
"""
Unified configuration system for all JustData applications.
Supports BranchSight, BizSight, and LendSight with consistent routing patterns.
"""

import os
from typing import Dict, Any

# Base configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')

# Ensure data directories exist
os.makedirs(os.path.join(DATA_DIR, 'reports'), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, 'logs'), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, 'processed'), exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, 'raw'), exist_ok=True)

# AI Configuration
AI_PROVIDER = os.getenv("AI_PROVIDER", "claude")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# BigQuery Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "hdma1-242116")

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
    # Reload environment variables
    AI_PROVIDER = os.getenv("AI_PROVIDER", AI_PROVIDER)
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", CLAUDE_MODEL)
    GPT_MODEL = os.getenv("GPT_MODEL", GPT_MODEL)
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    PROJECT_ID = os.getenv("GCP_PROJECT_ID", PROJECT_ID)
except ImportError:
    pass


class AppConfig:
    """Base configuration class for all applications."""
    
    # Shared settings
    BASE_DIR = BASE_DIR
    DATA_DIR = DATA_DIR
    AI_PROVIDER = AI_PROVIDER
    CLAUDE_MODEL = CLAUDE_MODEL
    GPT_MODEL = GPT_MODEL
    CLAUDE_API_KEY = CLAUDE_API_KEY
    OPENAI_API_KEY = OPENAI_API_KEY
    PROJECT_ID = PROJECT_ID
    
    # Default years range
    DEFAULT_YEARS = list(range(2017, 2025))
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'justdata-secret-key-change-this')
    
    @classmethod
    def get_config(cls, app_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific app.
        
        Args:
            app_name: Name of the app ('branchsight', 'bizsight', 'lendsight')
        
        Returns:
            Dictionary of configuration values
        """
        configs = {
            'branchsight': BranchSightConfig,
            'bizsight': BizSightConfig,
            'lendsight': LendSightConfig
        }
        
        config_class = configs.get(app_name.lower(), cls)
        return {
            'BASE_DIR': config_class.BASE_DIR,
            'DATA_DIR': config_class.DATA_DIR,
            'OUTPUT_DIR': config_class.OUTPUT_DIR,
            'AI_PROVIDER': config_class.AI_PROVIDER,
            'PROJECT_ID': config_class.PROJECT_ID,
            'DATASET_ID': config_class.DATASET_ID
        }


class BranchSightConfig(AppConfig):
    """Configuration specific to BranchSight (FDIC bank branch analyzer)."""
    
    APP_NAME = "BranchSight"
    DATASET_ID = "branches"
    TABLE_ID = "sod"
    OUTPUT_DIR = os.path.join(AppConfig.DATA_DIR, 'reports', 'branchsight')
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)


class BizSightConfig(AppConfig):
    """Configuration specific to BizSight (Business data analyzer)."""
    
    APP_NAME = "BizSight"
    DATASET_ID = "business"  # To be configured
    TABLE_ID = "businesses"
    OUTPUT_DIR = os.path.join(AppConfig.DATA_DIR, 'reports', 'bizsight')
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)


class LendSightConfig(AppConfig):
    """Configuration specific to LendSight (Lending data analyzer)."""
    
    APP_NAME = "LendSight"
    DATASET_ID = "hmda"  # HMDA lending data
    TABLE_ID = "loans"
    OUTPUT_DIR = os.path.join(AppConfig.DATA_DIR, 'reports', 'lendsight')
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

