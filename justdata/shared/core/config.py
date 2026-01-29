"""
Base configuration for all JustData applications.
Uses Pydantic for validation and environment variable loading.
"""

import os
from typing import Optional, List
from pathlib import Path

try:
    from pydantic import BaseSettings, Field
except ImportError:
    # Fallback for older pydantic versions
    from pydantic.v1 import BaseSettings, Field


class BaseAppConfig(BaseSettings):
    """Base configuration for all JustData apps."""

    # Application
    app_name: str = "justdata"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # BigQuery
    gcp_project_id: str = Field(default="justdata-ncrc", env="GCP_PROJECT_ID")
    google_credentials_json: Optional[str] = Field(default=None, env="GOOGLE_APPLICATION_CREDENTIALS_JSON")

    # AI Services
    ai_provider: str = Field(default="claude", env="AI_PROVIDER")
    claude_api_key: Optional[str] = Field(default=None, env="CLAUDE_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    claude_model: str = Field(default="claude-sonnet-4-20250514", env="CLAUDE_MODEL")
    gpt_model: str = Field(default="gpt-4", env="GPT_MODEL")

    # Census API
    census_api_key: Optional[str] = Field(default=None, env="CENSUS_API_KEY")

    # Flask
    secret_key: str = Field(default="change-in-production", env="SECRET_KEY")
    flask_debug: bool = Field(default=False, env="FLASK_DEBUG")

    # Cache
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")

    # Report Output
    report_output_dir: str = Field(default="./data/reports", env="REPORT_OUTPUT_DIR")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Fallback to ANTHROPIC_API_KEY if CLAUDE_API_KEY is not set
        if not self.claude_api_key:
            self.claude_api_key = os.getenv("ANTHROPIC_API_KEY")

    @property
    def is_local(self) -> bool:
        """Check if running in local development mode."""
        return not os.getenv("RENDER") and not os.getenv("DYNO") and not os.getenv("RAILWAY_ENVIRONMENT")

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.is_local

    def validate_ai_config(self) -> List[str]:
        """Validate AI configuration and return list of errors."""
        errors = []
        if self.ai_provider == "claude" and not self.claude_api_key:
            errors.append("CLAUDE_API_KEY or ANTHROPIC_API_KEY not set")
        if self.ai_provider == "openai" and not self.openai_api_key:
            errors.append("OPENAI_API_KEY not set")
        return errors

    def validate_bigquery_config(self) -> List[str]:
        """Validate BigQuery configuration and return list of errors."""
        errors = []
        if not self.google_credentials_json:
            # Check for file-based credentials
            creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if not creds_file or not Path(creds_file).exists():
                errors.append("BigQuery credentials not configured (GOOGLE_APPLICATION_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS)")
        return errors

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance (lazy loaded)
_settings: Optional[BaseAppConfig] = None


def get_settings() -> BaseAppConfig:
    """Get application settings (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = BaseAppConfig()
    return _settings
