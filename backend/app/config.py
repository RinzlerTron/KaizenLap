"""
Configuration management for KaizenLap application.

Handles environment variables and application settings.
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "KaizenLap"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    USE_LOCAL_FILES: bool = os.getenv("USE_LOCAL_FILES", "false").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/kaizenlap"
    )

    # Cloud Storage
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "")
    GCS_TELEMETRY_PREFIX: str = "telemetry"
    GCS_MAPS_PREFIX: str = "maps"
    
    # ML/Gemma Configuration
    GEMMA_MODEL_NAME: str = os.getenv("GEMMA_MODEL_NAME", "gemma-2b")
    GEMMA_API_KEY: str = os.getenv("GEMMA_API_KEY", "")
    GEMMA_ENDPOINT: str = os.getenv(
        "GEMMA_ENDPOINT",
        "https://generativelanguage.googleapis.com/v1beta/models"
    )
    USE_GPU: bool = os.getenv("USE_GPU", "true").lower() == "true"
    
    # Cloud Run
    CLOUD_RUN_REGION: str = os.getenv("CLOUD_RUN_REGION", "europe-west1")
    PROJECT_ID: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    
    # CORS (allow localhost for development, * for bundled deployment)
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",
        "*"  # Allow all origins for bundled deployment (same-origin anyway)
    ]
    
    # Data Processing
    MAX_TELEMETRY_FILE_SIZE_MB: int = 3500
    BATCH_SIZE: int = 1000
    
    # ML Processing Configuration
    REQUIRED_TELEMETRY_CHANNELS: List[str] = [
        'Laptrigger_lapdist_dls', 'Speed', 'Gear', 'nmot', 
        'ath', 'aps', 'pbrake_f', 'pbrake_r', 'accx_can', 
        'accy_can', 'Steering_Angle'
    ]
    DISTANCE_INTERVAL: float = 1.0  # meters
    
    # LLM Service (for vLLM deployment)
    LLM_SERVICE_URL: str = os.getenv("LLM_SERVICE_URL", "http://localhost:8001/generate")
    
    # Processed Data
    PROCESSED_DATA_GCS_PATH: str = "processed"
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"  # Ignore extra environment variables
    }


settings = Settings()

