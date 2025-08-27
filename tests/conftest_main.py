"""Pytest configuration and fixtures."""

import os
import pytest
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

# Set environment to test to disable TrustedHostMiddleware
os.environ["ENVIRONMENT"] = "test"

# Import and create app after setting environment
from radiator.main import create_application

app = create_application()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get mock database session for testing."""
    # Create a mock session
    mock_session = AsyncMock(spec=AsyncSession)
    yield mock_session


@pytest.fixture
def client() -> Generator:
    """Get test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_user():
    """Mock user for testing."""
    return {
        "id": 1,
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
    }


@pytest.fixture
def mock_item():
    """Mock item for testing."""
    return {
        "id": 1,
        "title": "Test Item",
        "description": "Test Description",
        "price": 1000,
        "owner_id": 1,
        "is_available": True,
    }
