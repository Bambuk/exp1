"""Pytest configuration for tracker tests."""

import pytest
from unittest.mock import Mock
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# Create test database
TestBase = declarative_base()

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

# Test session factory
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)


@pytest.fixture(scope="session")
def test_db_setup():
    """Set up test database."""
    # Import tracker models here to avoid circular imports
    from radiator.models.tracker import TrackerTask, TrackerTaskHistory, TrackerSyncLog
    
    # Create tables
    TestBase.metadata.create_all(bind=test_engine)
    yield
    # Clean up
    TestBase.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(test_db_setup) -> Generator[Session, None, None]:
    """Get test database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return Mock(spec=Session)


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
        "old_status": "Open",
        "new_status": "In Progress",
        "start_date": datetime.utcnow(),
        "end_date": datetime.utcnow(),
        "duration_minutes": 120,
        "changed_by": "user1",
        "change_reason": "Work started"
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
        "history_entries_created": 0,
        "error_details": None,
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
    return service


@pytest.fixture
def mock_sync_command():
    """Create mock TrackerSyncCommand."""
    from radiator.commands.sync_tracker import TrackerSyncCommand
    
    with pytest.MonkeyPatch.context() as m:
        m.setattr('radiator.commands.sync_tracker.logger', Mock())
        m.setattr('radiator.commands.sync_tracker.get_db_session', Mock())
        
        command = TrackerSyncCommand()
        command.db = Mock()
        return command
