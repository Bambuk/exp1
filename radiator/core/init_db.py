"""Database initialization script."""

import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from radiator.core.database import get_async_session, init_db
from radiator.core.security import get_password_hash
from radiator.crud.user import user
from radiator.models.user import User
from radiator.schemas.user import UserCreate

logger = logging.getLogger(__name__)


async def create_superuser(db: AsyncSession) -> None:
    """Create a superuser account."""
    # Check if superuser already exists
    existing_superuser = await user.get_by_email(db, email="admin@example.com")
    if existing_superuser:
        logger.info("Superuser already exists")
        return
    
    # Create superuser
    superuser_data = UserCreate(
        email="admin@example.com",
        username="admin",
        full_name="Administrator",
        password="admin123",  # Change this in production!
        is_active=True,
    )
    
    superuser = await user.create(db, obj_in=superuser_data)
    
    # Set as superuser
    superuser.is_superuser = True
    db.add(superuser)
    await db.commit()
    
    logger.info(f"Superuser created: {superuser.email}")


async def create_test_user(db: AsyncSession) -> None:
    """Create a test user account."""
    # Check if test user already exists
    existing_user = await user.get_by_email(db, email="test@example.com")
    if existing_user:
        logger.info("Test user already exists")
        return
    
    # Create test user
    test_user_data = UserCreate(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        password="test123",  # Change this in production!
        is_active=True,
    )
    
    test_user = await user.create(db, obj_in=test_user_data)
    logger.info(f"Test user created: {test_user.email}")


async def init_database() -> None:
    """Initialize database with tables and initial data."""
    logger.info("Initializing database...")
    
    # Create tables
    await init_db()
    logger.info("Database tables created")
    
    # Get database session
    async for db in get_async_session():
        try:
            # Create superuser
            await create_superuser(db)
            
            # Create test user
            await create_test_user(db)
            
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
