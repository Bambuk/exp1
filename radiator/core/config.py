"""Application configuration settings."""

import os
from functools import wraps
from typing import Any, Callable, List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = Field(default="Radiator CLI", env="APP_NAME")
    APP_VERSION: str = Field(default="0.1.0", env="APP_VERSION")
    DEBUG: bool = Field(default=True, env="DEBUG")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")

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

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

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
    TRACKER_BASE_URL: str = Field(
        default="https://api.tracker.yandex.net/v2/", env="TRACKER_BASE_URL"
    )
    TRACKER_MAX_WORKERS: int = Field(default=50, env="TRACKER_MAX_WORKERS")
    TRACKER_REQUEST_DELAY: float = Field(default=0.1, env="TRACKER_REQUEST_DELAY")
    TRACKER_SYNC_BATCH_SIZE: int = Field(default=100, env="TRACKER_SYNC_BATCH_SIZE")

    # Task limits - unified constants for all components
    DEFAULT_LARGE_LIMIT: int = Field(default=1000, env="DEFAULT_LARGE_LIMIT")
    DEFAULT_SEARCH_LIMIT: int = Field(default=100, env="DEFAULT_SEARCH_LIMIT")
    MAX_UNLIMITED_LIMIT: int = Field(default=10000, env="MAX_UNLIMITED_LIMIT")
    API_PAGE_SIZE: int = Field(default=50, env="API_PAGE_SIZE")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",  # Ignore extra fields from .env
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


def with_default_limit(default_limit: int):
    """
    Decorator to automatically set default limit if None is provided.

    Args:
        default_limit: Default limit value to use when limit is None
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if 'limit' is in kwargs and is None
            if "limit" in kwargs and kwargs["limit"] is None:
                kwargs["limit"] = default_limit
            return func(*args, **kwargs)

        return wrapper

    return decorator


def with_default_limit_method(default_limit: int):
    """
    Decorator for class methods to automatically set default limit if None is provided.

    Args:
        default_limit: Default limit value to use when limit is None
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Check if 'limit' is in kwargs and is None
            if "limit" in kwargs and kwargs["limit"] is None:
                kwargs["limit"] = default_limit
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def log_limit_info(operation: str, limit: int) -> None:
    """
    Unified logging for limit information.

    Args:
        operation: Description of the operation
        limit: Limit value to log
    """
    from radiator.core.logging import logger

    logger.info(f"🔍 {operation}")
    logger.info(f"   Лимит: {limit} задач")
