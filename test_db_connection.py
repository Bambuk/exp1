#!/usr/bin/env python3
"""Test database connection."""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_sync_connection():
    """Test synchronous database connection."""
    try:
        import psycopg2
        
        # Use DATABASE_URL_SYNC for psycopg2 (synchronous connection)
        database_url = os.getenv('DATABASE_URL_SYNC')
        if not database_url:
            raise EnvironmentError("Переменная окружения DATABASE_URL_SYNC не установлена")
        
        print(f"Testing connection with: {database_url}")
        
        conn = psycopg2.connect(database_url)
        print("✅ Synchronous connection successful!")
        conn.close()
        return True
        
    except ImportError:
        print("❌ psycopg2 not installed")
        return False
    except Exception as e:
        print(f"❌ Synchronous connection failed: {e}")
        return False

def test_async_connection():
    """Test asynchronous database connection."""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        import asyncio
        
        # Use DATABASE_URL for SQLAlchemy async (asyncpg driver)
        database_url = os.environ.get('DATABASE_URL', 'postgresql+asyncpg://postgres:12345@localhost:5432/radiator')
        
        print(f"Testing async connection with: {database_url}")
        
        async def test_async():
            engine = create_async_engine(database_url)
            async with engine.begin() as conn:
                result = await conn.execute("SELECT 1")
                print("✅ Asynchronous connection successful!")
            await engine.dispose()
        
        asyncio.run(test_async())
        return True
        
    except ImportError:
        print("❌ SQLAlchemy async not available")
        return False
    except Exception as e:
        print(f"❌ Asynchronous connection failed: {e}")
        return False

def test_config():
    """Test configuration loading."""
    try:
        from radiator.core.config import settings
        
        print(f"📋 Configuration loaded:")
        print(f"  DATABASE_URL: {settings.DATABASE_URL}")
        print(f"  DATABASE_URL_SYNC: {settings.DATABASE_URL_SYNC}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing database connections...\n")
    
    # Test configuration
    test_config()
    print()
    
    # Test sync connection
    test_sync_connection()
    print()
    
    # Test async connection
    test_async_connection()
    print()
    
    print("🏁 Testing completed!")
