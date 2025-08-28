"""Application configuration settings."""

import os
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Application
    APP_NAME: str = Field(default="Radiator API", json_schema_extra={"env": "APP_NAME"})
    APP_VERSION: str = Field(default="0.1.0", json_schema_extra={"env": "APP_VERSION"})
    DEBUG: bool = Field(default=True, json_schema_extra={"env": "DEBUG"})
    ENVIRONMENT: str = Field(default="development", json_schema_extra={"env": "ENVIRONMENT"})

    # Server
    HOST: str = Field(default="0.0.0.0", json_schema_extra={"env": "HOST"})
    PORT: int = Field(default=8000, json_schema_extra={"env": "PORT"})
    RELOAD: bool = Field(default=True, json_schema_extra={"env": "RELOAD"})

    # API
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:12345@localhost:5432/radiator",
        json_schema_extra={"env": "DATABASE_URL"},
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql://postgres:12345@localhost:5432/radiator",
        json_schema_extra={"env": "DATABASE_URL_SYNC"},
    )
    DATABASE_POOL_SIZE: int = Field(default=20, json_schema_extra={"env": "DATABASE_POOL_SIZE"})
    DATABASE_MAX_OVERFLOW: int = Field(default=30, json_schema_extra={"env": "DATABASE_MAX_OVERFLOW"})

    # Security
    SECRET_KEY: str = Field(
        default="your-super-secret-key-change-in-production",
        json_schema_extra={"env": "SECRET_KEY"},
    )
    ALGORITHM: str = Field(default="HS256", json_schema_extra={"env": "ALGORITHM"})
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, json_schema_extra={"env": "ACCESS_TOKEN_EXPIRE_MINUTES"}
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, json_schema_extra={"env": "REFRESH_TOKEN_EXPIRE_DAYS"}
    )

    # CORS
    ALLOWED_HOSTS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        json_schema_extra={"env": "ALLOWED_HOSTS"},
    )
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        json_schema_extra={"env": "ALLOWED_ORIGINS"},
    )

    # Logging
    LOG_LEVEL: str = Field(default="INFO", json_schema_extra={"env": "LOG_LEVEL"})
    LOG_FORMAT: str = Field(default="json", json_schema_extra={"env": "LOG_FORMAT"})

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0", json_schema_extra={"env": "REDIS_URL"}
    )

    # Email
    SMTP_HOST: str = Field(default="smtp.gmail.com", json_schema_extra={"env": "SMTP_HOST"})
    SMTP_PORT: int = Field(default=587, json_schema_extra={"env": "SMTP_PORT"})
    SMTP_USER: str = Field(default="", json_schema_extra={"env": "SMTP_USER"})
    SMTP_PASSWORD: str = Field(default="", json_schema_extra={"env": "SMTP_PASSWORD"})

    # External APIs
    EXTERNAL_API_KEY: str = Field(default="", json_schema_extra={"env": "EXTERNAL_API_KEY"})
    EXTERNAL_API_URL: str = Field(default="", json_schema_extra={"env": "EXTERNAL_API_URL"})

    # Yandex Tracker API
    TRACKER_API_TOKEN: str = Field(default="", json_schema_extra={"env": "TRACKER_API_TOKEN"})
    TRACKER_ORG_ID: str = Field(default="", json_schema_extra={"env": "TRACKER_ORG_ID"})
    TRACKER_BASE_URL: str = Field(default="https://api.tracker.yandex.net/v2/", json_schema_extra={"env": "TRACKER_BASE_URL"})
    TRACKER_MAX_WORKERS: int = Field(default=10, json_schema_extra={"env": "TRACKER_MAX_WORKERS"})
    TRACKER_REQUEST_DELAY: float = Field(default=0.1, json_schema_extra={"env": "TRACKER_REQUEST_DELAY"})
    TRACKER_SYNC_BATCH_SIZE: int = Field(default=100, json_schema_extra={"env": "TRACKER_SYNC_BATCH_SIZE"})

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True
    }


# Global settings instance
settings = Settings()
