"""Database configuration and session management."""

from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from radiator.core.config import settings

# Create async engine
async_engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
    future=True,
)

# Create sync engine for migrations
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
        from radiator.models import user, item, tracker  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await async_engine.dispose()
    sync_engine.dispose()
