"""Database initialization script."""

import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from radiator.core.database import get_async_session, init_db

logger = logging.getLogger(__name__)


async def init_database() -> None:
    """Initialize database with tables and initial data."""
    logger.info("Initializing database...")

    # Create tables
    await init_db()
    logger.info("Database tables created")

    # Get database session
    async for db in get_async_session():
        try:
            logger.info("Database initialization completed successfully")
        except Exception as e:
            logger.error(f"Error during database initialization: {e}")
            raise
        finally:
            await db.close()


def main() -> None:
    """Main function to run database initialization."""
    asyncio.run(init_database())


if __name__ == "__main__":
    main()
