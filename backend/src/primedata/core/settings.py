"""
Application settings and configuration.
"""

import os
from typing import List, Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for pydantic v1
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    ENV: str = "development"
    DISABLE_AUTH: bool = True  # Set to True to disable authentication in development
    TESTING_MODE: bool = False  # Set to True for testing mode
    USE_DEV_USER: bool = True  # Set to True to use default dev user ID instead of authenticated user
    DEV_USER_ID: str = "550e8400-e29b-41d4-a716-446655440000"  # Default user ID for development

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://primedata:primedata123@localhost:5433/primedata"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

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

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
_settings: Settings = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
