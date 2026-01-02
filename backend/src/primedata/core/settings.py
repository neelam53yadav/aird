"""
Application settings and configuration.
"""

import json
import os
from typing import List, Optional, Union

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for pydantic v1
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    ENV: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://primedata:primedata123@localhost:5433/primedata"

    # CORS - can be set via environment variable as JSON array or comma-separated string
    # Example: CORS_ORIGINS='["http://localhost:3000","https://airdops.com"]'
    # Or: CORS_ORIGINS=http://localhost:3000,https://airdops.com
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000", "https://airdops.com", "https://www.airdops.com"]

    # Authentication
    NEXTAUTH_SECRET: str = "REPLACE_WITH_64_CHAR_RANDOM_STRING_FOR_PRODUCTION_USE_ONLY"
    JWT_ISSUER: str = "https://api.local/auth"
    JWT_AUDIENCE: str = "primedata-api"
    API_SESSION_EXCHANGE_ALLOWED_ISS: str = "https://nextauth.local"

    # MLflow Configuration
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_BACKEND_STORE_URI: str = "postgresql://primedata:primedata123@localhost:5433/primedata"
    MLFLOW_DEFAULT_ARTIFACT_ROOT: str = "s3://mlflow-artifacts"

    # Storage Configuration
    USE_GCS: bool = False  # Set to True to use GCS instead of MinIO

    # MinIO Configuration (for local development)
    MINIO_HOST: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_SECURE: bool = False

    # GCS Configuration (for production, uses Application Default Credentials)
    GCS_PROJECT_ID: Optional[str] = None  # GCP Project ID (optional, for reference)

    # Qdrant Configuration
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334

    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = None  # OpenAI API key for embedding models

    # AIRD Configuration (M0)
    AIRD_PLAYBOOK_DIR: str = ""  # Path to playbook directory (empty = auto-detect)
    AIRD_SCORING_WEIGHTS_PATH: str = ""  # Path to scoring weights JSON (empty = auto-detect)
    AIRD_DEFAULT_PLAYBOOK: str = "TECH"  # Default playbook ID
    AIRD_DEFAULT_SCORING_THRESHOLD: float = 70.0  # Default AI Trust Score threshold
    AIRD_POLICY_MIN_TRUST_SCORE: float = 50.0  # Minimum trust score for policy
    AIRD_POLICY_MIN_SECURE: float = 90.0  # Minimum secure score for policy
    AIRD_POLICY_MIN_METADATA_PRESENCE: float = 80.0  # Minimum metadata presence for policy
    AIRD_POLICY_MIN_KB_READY: float = 50.0  # Minimum KB readiness for policy
    AIRD_ENABLE_DEDUPLICATION: bool = False  # Enable MinHash deduplication
    AIRD_ENABLE_VALIDATION: bool = True  # Enable validation summary generation
    AIRD_ENABLE_PDF_REPORTS: bool = True  # Enable PDF report generation

    # Email Configuration (SMTP)
    SMTP_ENABLED: bool = False  # Set to True to enable email sending
    SMTP_HOST: str = "smtp.gmail.com"  # SMTP server hostname
    SMTP_PORT: int = 587  # SMTP server port (587 for TLS, 465 for SSL, 25 for plain)
    SMTP_USE_TLS: bool = True  # Use TLS encryption
    SMTP_USE_SSL: bool = False  # Use SSL encryption (alternative to TLS)
    SMTP_USERNAME: Optional[str] = None  # SMTP username (usually your email)
    SMTP_PASSWORD: Optional[str] = None  # SMTP password or app-specific password
    SMTP_FROM_EMAIL: str = "noreply@primedata.com"  # From email address
    FRONTEND_URL: str = "https://airdops.com"  # Frontend URL for email links

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env (for backward compatibility during migration)


# Global settings instance
_settings: Settings = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings()
        # Parse CORS_ORIGINS from environment if it's a string
        cors_origins_env = os.getenv("CORS_ORIGINS")
        if cors_origins_env:
            try:
                # Try parsing as JSON array first
                parsed = json.loads(cors_origins_env)
                if isinstance(parsed, list):
                    _settings.CORS_ORIGINS = parsed
                else:
                    # If JSON but not a list, treat as single value
                    _settings.CORS_ORIGINS = [str(parsed)]
            except (json.JSONDecodeError, ValueError):
                # If not JSON, treat as comma-separated string
                origins_list = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
                if origins_list:
                    _settings.CORS_ORIGINS = origins_list
                else:
                    # Single value
                    _settings.CORS_ORIGINS = [cors_origins_env.strip()]
        # Ensure CORS_ORIGINS is always a list
        if isinstance(_settings.CORS_ORIGINS, str):
            _settings.CORS_ORIGINS = [_settings.CORS_ORIGINS]

        # Debug logging (remove in production if needed)
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"CORS_ORIGINS configured: {_settings.CORS_ORIGINS}")
    return _settings
