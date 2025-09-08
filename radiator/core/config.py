"""Application configuration settings."""

import os
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = Field(default="Radiator API", env="APP_NAME")
    APP_VERSION: str = Field(default="0.1.0", env="APP_VERSION")
    DEBUG: bool = Field(default=True, env="DEBUG")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

    # Server
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    RELOAD: bool = Field(default=True, env="RELOAD")

    # API
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:12345@localhost:5432/radiator",
        env="DATABASE_URL",
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql://postgres:12345@localhost:5432/radiator",
        env="DATABASE_URL_SYNC",
    )
    DATABASE_POOL_SIZE: int = Field(default=20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")

    # Security
    SECRET_KEY: str = Field(
        default="your-super-secret-key-change-in-production",
        env="SECRET_KEY",
    )
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, env="REFRESH_TOKEN_EXPIRE_DAYS"
    )

    # CORS
    ALLOWED_HOSTS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_HOSTS",
    )
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_ORIGINS",
    )

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0", env="REDIS_URL"
    )

    # Email
    SMTP_HOST: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: str = Field(default="", env="SMTP_USER")
    SMTP_PASSWORD: str = Field(default="", env="SMTP_PASSWORD")

    # External APIs
    EXTERNAL_API_KEY: str = Field(default="", env="EXTERNAL_API_KEY")
    EXTERNAL_API_URL: str = Field(default="", env="EXTERNAL_API_URL")

    # Yandex Tracker API
    TRACKER_API_TOKEN: str = Field(default="", env="TRACKER_API_TOKEN")
    TRACKER_ORG_ID: str = Field(default="", env="TRACKER_ORG_ID")
    TRACKER_BASE_URL: str = Field(default="https://api.tracker.yandex.net/v2/", env="TRACKER_BASE_URL")
    TRACKER_MAX_WORKERS: int = Field(default=10, env="TRACKER_MAX_WORKERS")
    TRACKER_REQUEST_DELAY: float = Field(default=0.1, env="TRACKER_REQUEST_DELAY")
    TRACKER_SYNC_BATCH_SIZE: int = Field(default=100, env="TRACKER_SYNC_BATCH_SIZE")
    
    # Task limits - unified constants for all components
    DEFAULT_SYNC_LIMIT: int = Field(default=1000, env="DEFAULT_SYNC_LIMIT")
    DEFAULT_SEARCH_LIMIT: int = Field(default=100, env="DEFAULT_SEARCH_LIMIT")
    DEFAULT_HISTORY_LIMIT: int = Field(default=1000, env="DEFAULT_HISTORY_LIMIT")
    MAX_UNLIMITED_LIMIT: int = Field(default=10000, env="MAX_UNLIMITED_LIMIT")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"  # Ignore extra fields from .env
    }

    @property
    def is_test_environment(self) -> bool:
        """Check if running in test environment."""
        return self.ENVIRONMENT.lower() == "test"


def get_settings() -> Settings:
    """Get settings instance with proper environment file loading."""
    # Determine which environment file to load
    env = os.getenv("ENVIRONMENT", "development")
    
    if env.lower() == "test":
        # Load test environment file
        env_file = ".env.test"
        if os.path.exists(env_file):
            return Settings(_env_file=env_file)
        else:
            # Fallback to default .env if .env.test doesn't exist
            return Settings()
    else:
        # Load default environment file
        return Settings()


# Global settings instance
settings = get_settings()
