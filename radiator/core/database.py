"""Database configuration and session management."""

from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from radiator.core.config import settings

# Create async engine - use settings from appropriate environment file
async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
    future=True,
)

# Create sync engine for migrations - use settings from appropriate environment file
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

# Session factories
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)

# Base class for models
Base = declarative_base()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_session() -> Generator:
    """Get sync database session."""
    with SessionLocal() as session:
        try:
            yield session
        finally:
            session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        # Import all models here to ensure they are registered
        from radiator.models import tracker, user  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await async_engine.dispose()
    sync_engine.dispose()


def get_test_database_url() -> str:
    """Get test database URL for testing purposes."""
    # Force test database URL regardless of current environment
    if "radiator_test" in settings.DATABASE_URL:
        return settings.DATABASE_URL
    test_url = settings.DATABASE_URL.replace("radiator", "radiator_test")
    return test_url


def get_test_database_url_sync() -> str:
    """Get test database sync URL for testing purposes."""
    # Force test database URL regardless of current environment
    if "radiator_test" in settings.DATABASE_URL_SYNC:
        return settings.DATABASE_URL_SYNC
    test_url = settings.DATABASE_URL_SYNC.replace("radiator", "radiator_test")
    return test_url
