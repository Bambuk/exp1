"""Pytest configuration for tracker tests."""

from datetime import datetime, timezone
from typing import Generator
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from radiator.core.database import Base
from radiator.models.tracker import TrackerSyncLog, TrackerTask, TrackerTaskHistory


@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine."""
    # Environment variables are already set by pytest-env
    from radiator.core.database import get_test_database_url_sync

    database_url = get_test_database_url_sync()
    print(f"✅ Test DB Engine using: {database_url}")
    engine = create_engine(database_url, echo=False)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup - drop all tables
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(test_db_engine):
    """Create database session for tests."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    return {
        "tracker_id": "12345",
        "key": "TEST-123",
        "summary": "Test Task",
        "description": "Test Description",
        "status": "open",
        "author": "user1",
        "assignee": "Test User",
        "business_client": "Test Client",
        "team": "frontend",
        "prodteam": "development",
        "profit_forecast": "high",
    }


@pytest.fixture
def sample_history_data():
    """Sample history data for testing."""
    return {
        "tracker_id": "12345",
        "status": "Open",
        "status_display": "Open",
        "start_date": datetime.now(timezone.utc),
        "end_date": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_sync_log_data():
    """Sample sync log data for testing."""
    return {
        "sync_started_at": datetime.now(timezone.utc),
        "status": "in_progress",
        "tasks_processed": 0,
        "tasks_created": 0,
        "tasks_updated": 0,
        "history_entries_processed": 0,
        "error_message": None,
        "sync_completed_at": None,
    }


@pytest.fixture
def mock_tracker_service():
    """Create mock TrackerAPIService."""
    from radiator.services.tracker_service import TrackerAPIService

    service = Mock(spec=TrackerAPIService)
    service.get_recent_tasks.return_value = ["12345", "67890"]
    service.get_active_tasks.return_value = ["11111", "22222"]
    service.search_tasks.return_value = ["33333"]
    service.get_task.return_value = {
        "id": "12345",
        "key": "TEST-123",
        "summary": "Test Task",
    }
    service.get_task_changelog.return_value = []
    service.get_tasks_by_filter.return_value = ["33333"]
    return service


@pytest.fixture
def mock_sync_command():
    """Create mock TrackerSyncCommand."""
    from radiator.commands.sync_tracker import TrackerSyncCommand

    command = TrackerSyncCommand()
    command.db = Mock()
    return command
