"""Pytest configuration and fixtures."""

import os
import pytest
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

# Set environment to test to disable TrustedHostMiddleware
os.environ["ENVIRONMENT"] = "test"

from radiator.main import create_application # Import and create app after setting environment
app = create_application()


@pytest.fixture
def client() -> TestClient:
    """Get test client."""
    return TestClient(app)


@pytest.fixture
def db_session() -> AsyncSession:
    """Get mock async database session."""
    return AsyncMock(spec=AsyncSession)


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
