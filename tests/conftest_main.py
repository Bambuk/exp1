"""Pytest configuration and fixtures."""

import os
import pytest
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

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


@pytest.fixture(autouse=True)
def mock_crud_operations():
    """Mock all CRUD operations to prevent database access."""
    with patch('radiator.crud.user.user.get_by_email') as mock_get_email, \
         patch('radiator.crud.user.user.get_by_username') as mock_get_username, \
         patch('radiator.crud.user.user.create') as mock_create, \
         patch('radiator.crud.user.user.authenticate') as mock_authenticate:
        
        # Create mock user objects
        def create_mock_user(email, username, full_name=None):
            mock_user = Mock()
            mock_user.id = 1
            mock_user.email = email
            mock_user.username = username
            mock_user.full_name = full_name or "Test User"
            mock_user.bio = None
            mock_user.avatar_url = None
            mock_user.is_active = True
            mock_user.is_superuser = False
            mock_user.created_at = datetime.now(timezone.utc)
            mock_user.updated_at = datetime.now(timezone.utc)
            return mock_user
        
        # Default mock behavior
        mock_get_email.return_value = None  # Email doesn't exist by default
        mock_get_username.return_value = None  # Username doesn't exist by default
        mock_create.return_value = None  # Will be set per test
        mock_authenticate.return_value = None  # Will be set per test
        
        yield {
            'get_by_email': mock_get_email,
            'get_by_username': mock_get_username,
            'create': mock_create,
            'authenticate': mock_authenticate,
            'create_mock_user': create_mock_user
        }


@pytest.fixture(scope="session")
def test_environment():
    """Ensure test environment is properly configured."""
    # Verify we're using test database
    from radiator.core.config import settings
    assert settings.is_test_environment
    assert "radiator_test" in settings.DATABASE_URL
    return True
