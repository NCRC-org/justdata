"""
Database connection management for JustData.
"""

from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from google.cloud import bigquery
from core.config.settings import get_settings
import structlog

logger = structlog.get_logger()

# SQLAlchemy base class
Base = declarative_base()

# Database engines
postgres_engine: Optional[Session] = None
bigquery_client: Optional[bigquery.Client] = None


def get_postgres_engine():
    """Get PostgreSQL engine."""
    global postgres_engine
    if postgres_engine is None:
        settings = get_settings()
        if settings.database_url:
            try:
                postgres_engine = create_engine(
                    settings.database_url,
                    pool_pre_ping=True,
                    pool_recycle=300
                )
                logger.info("PostgreSQL engine created successfully")
            except Exception as e:
                logger.error("Failed to create PostgreSQL engine", error=str(e))
                return None
        else:
            logger.warning("No PostgreSQL database URL configured")
            return None
    
    return postgres_engine


def get_bigquery_client():
    """Get BigQuery client."""
    global bigquery_client
    if bigquery_client is None:
        settings = get_settings()
        if settings.bq_project_id:
            try:
                # Create BigQuery client with service account credentials
                from google.oauth2 import service_account
                
                credentials = service_account.Credentials.from_service_account_info({
                    "type": settings.bq_type,
                    "project_id": settings.bq_project_id,
                    "private_key_id": settings.bq_private_key_id,
                    "private_key": settings.bq_private_key.replace('\\n', '\n') if settings.bq_private_key else None,
                    "client_email": settings.bq_client_email,
                    "client_id": settings.bq_client_id,
                    "auth_uri": settings.bq_auth_uri,
                    "token_uri": settings.bq_token_uri,
                    "auth_provider_x509_cert_url": settings.bq_auth_provider_x509_cert_url,
                    "client_x509_cert_url": settings.bq_client_x509_cert_url,
                })
                
                bigquery_client = bigquery.Client(
                    project=settings.bq_project_id,
                    credentials=credentials
                )
                logger.info("BigQuery client created successfully with service account")
            except Exception as e:
                logger.error("Failed to create BigQuery client", error=str(e))
                return None
        else:
            logger.warning("No BigQuery project ID configured")
            return None
    
    return bigquery_client


def get_postgres_session() -> Optional[Session]:
    """Get PostgreSQL session."""
    engine = get_postgres_engine()
    if engine:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    return None


def close_postgres_session(session: Session):
    """Close PostgreSQL session."""
    if session:
        session.close()


def test_connections():
    """Test database connections."""
    logger.info("Testing database connections...")
    
    # Test PostgreSQL
    try:
        session = get_postgres_session()
        if session:
            session.execute("SELECT 1")
            logger.info("PostgreSQL connection successful")
            session.close()
        else:
            logger.warning("PostgreSQL connection not available")
    except Exception as e:
        logger.error("PostgreSQL connection failed", error=str(e))
    
    # Test BigQuery
    try:
        client = get_bigquery_client()
        if client:
            # Test with a simple query
            query = "SELECT 1 as test"
            query_job = client.query(query)
            results = query_job.result()
            logger.info("BigQuery connection successful")
        else:
            logger.warning("BigQuery connection not available")
    except Exception as e:
        logger.error("BigQuery connection failed", error=str(e))


def init_database():
    """Initialize database tables."""
    engine = get_postgres_engine()
    if engine:
        try:
            # Import all models here to ensure they're registered
            # from apps.branchseeker.models import *
            # from apps.lendsight.models import *
            # from apps.bizsight.models import *
            
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error("Failed to create database tables", error=str(e))
    else:
        logger.warning("Cannot initialize database - no engine available")
