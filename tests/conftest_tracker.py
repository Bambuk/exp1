"""Pytest configuration for tracker tests."""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import Generator

from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def db_session() -> AsyncSession:
    """Get mock async database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return Mock(spec=AsyncSession)


@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    from datetime import datetime
    return {
        "tracker_id": "TEST-1",
        "key": "TEST-123",
        "summary": "Test Task",
        "description": "Test Description",
        "status": "open",
        "author": "user1",
        "assignee": "Test User",
        "business_client": "Test Client",
        "team": "frontend",
        "prodteam": "development",
        "profit_forecast": "high"
    }


@pytest.fixture
def sample_history_data():
    """Sample history data for testing."""
    from datetime import datetime
    return {
        "tracker_id": "TEST-1",
        "status": "Open",
        "status_display": "Open",
        "start_date": datetime.utcnow(),
        "end_date": datetime.utcnow()
    }


@pytest.fixture
def sample_sync_log_data():
    """Sample sync log data for testing."""
    from datetime import datetime
    return {
        "sync_started_at": datetime.utcnow(),
        "status": "in_progress",
        "tasks_processed": 0,
        "tasks_created": 0,
        "tasks_updated": 0,
        "history_entries_processed": 0,
        "error_message": None,
        "sync_completed_at": None
    }


@pytest.fixture
def mock_tracker_service():
    """Create mock TrackerAPIService."""
    from radiator.services.tracker_service import TrackerAPIService
    
    service = Mock(spec=TrackerAPIService)
    service.get_recent_tasks.return_value = ["TEST-1", "TEST-2"]
    service.get_active_tasks.return_value = ["TEST-3", "TEST-4"]
    service.search_tasks.return_value = ["TEST-5"]
    service.get_task.return_value = {
        "tracker_id": "TEST-1",
        "key": "TEST-1",
        "summary": "Test Task"
    }
    service.get_task_changelog.return_value = []
    service.get_tasks_by_filter.return_value = ["TEST-5"]
    return service


@pytest.fixture
def mock_sync_command():
    """Create mock TrackerSyncCommand."""
    from radiator.commands.sync_tracker import TrackerSyncCommand
    
    command = TrackerSyncCommand()
    command.db = Mock()
    return command
