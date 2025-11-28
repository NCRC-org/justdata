"""
Configuration settings for JustData application.
"""

import os
from typing import Optional, List
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "JustData"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = "/api/v1"
    
    # Database
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    bigquery_dataset: Optional[str] = Field(default=None, env="BIGQUERY_DATASET")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # AI Services
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    # Check both CLAUDE_API_KEY and ANTHROPIC_API_KEY for compatibility
    claude_api_key: Optional[str] = Field(
        default=None, 
        env="CLAUDE_API_KEY"
    )
    
    # HubSpot Integration
    hubspot_access_token: Optional[str] = Field(default=None, env="HUBSPOT_ACCESS_TOKEN")
    hubspot_api_key: Optional[str] = Field(default=None, env="HUBSPOT_API_KEY")
    hubspot_portal_id: Optional[str] = Field(default=None, env="HUBSPOT_PORTAL_ID")
    hubspot_sync_enabled: bool = Field(default=True, env="HUBSPOT_SYNC_ENABLED")
    hubspot_webhook_secret: Optional[str] = Field(default=None, env="HUBSPOT_WEBHOOK_SECRET")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Fallback to ANTHROPIC_API_KEY if CLAUDE_API_KEY is not set
        if not self.claude_api_key:
            self.claude_api_key = os.getenv("ANTHROPIC_API_KEY")
    
    # BigQuery Service Account Credentials
    bq_type: Optional[str] = Field(default=None, env="BQ_TYPE")
    bq_project_id: Optional[str] = Field(default=None, env="BQ_PROJECT_ID")
    bq_private_key_id: Optional[str] = Field(default=None, env="BQ_PRIVATE_KEY_ID")
    bq_private_key: Optional[str] = Field(default=None, env="BQ_PRIVATE_KEY")
    bq_client_email: Optional[str] = Field(default=None, env="BQ_CLIENT_EMAIL")
    bq_client_id: Optional[str] = Field(default=None, env="BQ_CLIENT_ID")
    bq_auth_uri: Optional[str] = Field(default=None, env="BQ_AUTH_URI")
    bq_token_uri: Optional[str] = Field(default=None, env="BQ_TOKEN_URI")
    bq_auth_provider_x509_cert_url: Optional[str] = Field(default=None, env="BQ_AUTH_PROVIDER_X509_CERT_URL")
    bq_client_x509_cert_url: Optional[str] = Field(default=None, env="BQ_CLIENT_X509_CERT_URL")
    
    # Security
    secret_key: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXIRE_MINUTES")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )
    
    # Data Sources
    fdic_data_url: str = Field(
        default="https://banks.data.fdic.gov/api",
        env="FDIC_DATA_URL"
    )
    hmda_data_url: str = Field(
        default="https://ffiec.cfpb.gov/api",
        env="HMDA_DATA_URL"
    )
    sba_data_url: str = Field(
        default="https://api.sba.gov",
        env="SBA_DATA_URL"
    )
    
    # Reporting
    report_output_dir: str = Field(default="./data/reports", env="REPORT_OUTPUT_DIR")
    max_report_size_mb: int = Field(default=50, env="MAX_REPORT_SIZE_MB")
    
    # Cache
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
