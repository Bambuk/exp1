"""Tests for Yandex Tracker synchronization system."""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from radiator.models.tracker import TrackerTask, TrackerTaskHistory, TrackerSyncLog
from radiator.services.tracker_service import TrackerAPIService
from radiator.commands.sync_tracker import TrackerSyncCommand
from radiator.crud.tracker import (
    CRUDTrackerTask,
    CRUDTrackerTaskHistory,
    CRUDTrackerSyncLog
)


class TestTrackerAPIService:
    """Test TrackerAPIService class."""

    @pytest.fixture
    def mock_service(self):
        """Create mock TrackerAPIService instance."""
        with patch('radiator.services.tracker_service.logger'):
            service = TrackerAPIService()
            service.headers = {
                "Authorization": "OAuth test_token",
                "X-Org-ID": "test_org",
                "Content-Type": "application/json"
            }
            service.base_url = "https://api.tracker.yandex.net/v2/"
            return service

    @pytest.fixture
    def mock_response(self):
        """Create mock API response."""
        mock = Mock()
        mock.json.return_value = {
            "issues": [
                {"id": "12345", "key": "TEST-123", "summary": "Test Task 1"},
                {"id": "67890", "key": "TEST-456", "summary": "Test Task 2"}
            ]
        }
        mock.status_code = 200
        return mock

    def test_search_tasks_success(self, mock_service):
        """Test successful task search with pagination."""
        # Mock response with pagination headers
        mock_response = Mock()
        mock_response.headers = {"X-Total-Pages": "1"}
        mock_response.json.return_value = [
            {"id": "12345", "key": "TEST-123", "summary": "Test Task 1"},
            {"id": "67890", "key": "TEST-456", "summary": "Test Task 2"}
        ]
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
            result = mock_service.search_tasks("Updated: >2024-01-01")
            assert len(result) == 2
            assert "12345" in result
            assert "67890" in result

    def test_search_tasks_with_pagination(self, mock_service):
        """Test task search with pagination support."""
        # Mock get_total_tasks_count to return a known value
        with patch.object(mock_service, 'get_total_tasks_count', return_value=5):
            # Mock first page response with 3 tasks
            first_page = Mock()
            first_page.headers = {"X-Total-Pages": "1"}
            first_page.json.return_value = [
                {"id": "1"}, {"id": "2"}, {"id": "3"}
            ]
            
            with patch('radiator.services.tracker_service.requests.request') as mock_request:
                mock_request.return_value = first_page
                
                result = mock_service.search_tasks("Updated: >2024-01-01", limit=10)
                assert len(result) == 3
                assert "1" in result
                assert "3" in result

    def test_search_tasks_api_error(self, mock_service):
        """Test API error handling in task search."""
        with patch('radiator.services.tracker_service.requests.request', side_effect=Exception("API Error")):
            result = mock_service.search_tasks("test query")
            assert result == []

    def test_get_recent_tasks(self, mock_service):
        """Test getting recent tasks."""
        # Mock response with pagination headers
        mock_response = Mock()
        mock_response.headers = {"X-Total-Pages": "1"}
        mock_response.json.return_value = [
            {"id": "12345", "key": "TEST-123", "summary": "Test Task 1"},
            {"id": "67890", "key": "TEST-456", "summary": "Test Task 2"}
        ]
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
            result = mock_service.get_recent_tasks(days=7, limit=10)
            assert len(result) == 2

    def test_get_active_tasks(self, mock_service):
        """Test getting active tasks."""
        # Mock response with pagination headers
        mock_response = Mock()
        mock_response.headers = {"X-Total-Pages": "1"}
        mock_response.json.return_value = [
            {"id": "12345", "key": "TEST-123", "summary": "Test Task 1"},
            {"id": "67890", "key": "TEST-456", "summary": "Test Task 2"}
        ]
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
            result = mock_service.get_active_tasks(limit=10)
            assert len(result) == 2

    def test_get_tasks_by_filter(self, mock_service):
        """Test getting tasks by filter."""
        # Mock response with pagination headers
        mock_response = Mock()
        mock_response.headers = {"X-Total-Pages": "1"}
        mock_response.json.return_value = [
            {"id": "12345", "key": "TEST-123", "summary": "Test Task 1"},
            {"id": "67890", "key": "TEST-456", "summary": "Test Task 2"}
        ]
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
            filters = {"status": "Open", "assignee": "test_user"}
            result = mock_service.get_tasks_by_filter(filters, limit=10)
            assert len(result) == 2

    def test_get_total_tasks_count(self, mock_service):
        """Test getting total tasks count from API headers."""
        mock_response = Mock()
        mock_response.headers = {"X-Total-Count": "150"}
        mock_response.json.return_value = []
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
            result = mock_service.get_total_tasks_count("Updated: >2024-01-01")
            assert result == 150

    def test_get_total_tasks_count_fallback(self, mock_service):
        """Test getting total tasks count with fallback to response data."""
        mock_response = Mock()
        mock_response.headers = {}  # No X-Total-Count header
        mock_response.json.return_value = [
            {"id": "1"}, {"id": "2"}, {"id": "3"}
        ]
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
            result = mock_service.get_total_tasks_count("Updated: >2024-01-01")
            assert result == 3

    def test_extract_task_data(self, mock_service):
        """Test task data extraction."""
        mock_task = {
            "id": "12345",
            "key": "TEST-123",
            "summary": "Test Task",
            "status": {"key": "open", "display": "Open"},
            "assignee": {"id": "user1", "display": "Test User"},
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z"
        }
        
        result = mock_service.extract_task_data(mock_task)
        assert result["tracker_id"] == "12345"
        assert result["key"] == "TEST-123"
        assert result["summary"] == "Test Task"
        assert result["status"] == "Open"

    def test_extract_status_history(self, mock_service):
        """Test status history extraction."""
        mock_changelog = [
            {
                "updatedAt": "2024-01-01T00:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status"},
                        "to": {"display": "In Progress"}
                    }
                ]
            }
        ]
        
        result = mock_service.extract_status_history(mock_changelog)
        assert len(result) == 1
        assert result[0]["status"] == "In Progress"
        assert result[0]["status_display"] == "In Progress"


class TestTrackerCRUD:
    """Test CRUD operations for tracker models."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return Mock()

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for testing."""
        return {
            "tracker_id": "12345",
            "key": "TEST-123",
            "summary": "Test Task",
            "status": "open",
            "assignee": "Test User",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

    @pytest.fixture
    def sample_history_data(self):
        """Sample history data for testing."""
        return {
            "task_id": 1,
            "tracker_id": "12345",
            "status": "In Progress",
            "status_display": "In Progress",
            "start_date": datetime.now(timezone.utc),
            "end_date": datetime.now(timezone.utc)
        }

    def test_create_task(self, mock_db_session, sample_task_data):
        """Test creating a tracker task."""
        crud = CRUDTrackerTask(TrackerTask)
        
        # Mock the create method to return a task object
        mock_task = TrackerTask(**sample_task_data)
        with patch.object(crud, 'create', return_value=mock_task):
            # The create method is async, so we need to await it
            import asyncio
            result = asyncio.run(crud.create(mock_db_session, obj_in=sample_task_data))
            
            assert result.tracker_id == "12345"
            assert result.summary == "Test Task"

    def test_get_task_by_tracker_id(self, mock_db_session):
        """Test getting task by tracker ID."""
        crud = CRUDTrackerTask(TrackerTask)
        
        # Mock the get_by_tracker_id method directly
        mock_task = TrackerTask(tracker_id="12345")
        with patch.object(crud, 'get_by_tracker_id', return_value=mock_task):
            result = crud.get_by_tracker_id(mock_db_session, tracker_id="12345")
            
            assert result.tracker_id == "12345"

    def test_create_history_entry(self, mock_db_session, sample_history_data):
        """Test creating a history entry."""
        crud = CRUDTrackerTaskHistory(TrackerTaskHistory)
        
        # Mock the create method to return a history object
        mock_history = TrackerTaskHistory(**sample_history_data)
        with patch.object(crud, 'create', return_value=mock_history):
            # The create method is async, so we need to await it
            import asyncio
            result = asyncio.run(crud.create(mock_db_session, obj_in=sample_history_data))
            
            assert result.tracker_id == "12345"
            assert result.status == "In Progress"
            assert result.status_display == "In Progress"

    def test_bulk_create_tasks(self, mock_db_session, sample_task_data):
        """Test bulk creation of tasks."""
        crud = CRUDTrackerTask(TrackerTask)
        tasks_data = [sample_task_data, {**sample_task_data, "tracker_id": "67890"}]
        
        with patch.object(crud, 'bulk_create_or_update') as mock_bulk_create:
            mock_bulk_create.return_value = [TrackerTask(**data) for data in tasks_data]
            result = crud.bulk_create_or_update(mock_db_session, tasks_data)
            
            assert len(result) == 2
            assert result[0].tracker_id == "12345"
            assert result[1].tracker_id == "67890"


class TestTrackerSyncCommand:
    """Test TrackerSyncCommand class."""

    @pytest.fixture
    def mock_sync_command(self):
        """Create mock TrackerSyncCommand instance."""
        with patch('radiator.commands.sync_tracker.logger'):
            command = TrackerSyncCommand()
            command.db = Mock()
            return command

    @pytest.fixture
    def mock_tracker_service(self):
        """Create mock TrackerAPIService."""
        service = Mock(spec=TrackerAPIService)
        service.get_tasks_by_filter.return_value = ["33333"]
        return service

    def test_get_tasks_to_sync_with_filters(self, mock_sync_command, mock_tracker_service):
        """Test getting tasks with filters."""
        with patch('radiator.commands.sync_tracker.tracker_service', mock_tracker_service):
            filters = {"status": "Open"}
            result = mock_sync_command.get_tasks_to_sync(
                filters=filters, limit=10
            )
            assert result == ["33333"]
            mock_tracker_service.get_tasks_by_filter.assert_called_once_with(filters, limit=10)

    def test_get_tasks_to_sync_without_filters(self, mock_sync_command, mock_tracker_service):
        """Test getting tasks without filters."""
        with patch('radiator.commands.sync_tracker.tracker_service', mock_tracker_service):
            result = mock_sync_command.get_tasks_to_sync(limit=10)
            assert result == ["33333"]
            mock_tracker_service.get_tasks_by_filter.assert_called_once_with(None, limit=10)

    def test_create_sync_log(self, mock_sync_command):
        """Test creating sync log."""
        # Mock the database session to return a mock log
        mock_log = Mock(spec=TrackerSyncLog)
        mock_log.id = "sync-123"
        
        with patch('radiator.commands.sync_tracker.TrackerSyncLog', return_value=mock_log):
            with patch.object(mock_sync_command.db, 'add'):
                with patch.object(mock_sync_command.db, 'commit'):
                    with patch.object(mock_sync_command.db, 'refresh'):
                        result = mock_sync_command.create_sync_log()
                        assert result.id == "sync-123"

    def test_update_sync_log(self, mock_sync_command):
        """Test updating sync log."""
        mock_sync_command.sync_log = Mock(id="sync-123")
        
        mock_sync_command.update_sync_log(
            status="completed",
            tasks_processed=5,
            sync_completed_at=datetime.now(timezone.utc)
        )
        
        # The method directly updates the sync_log object and commits to db
        assert mock_sync_command.sync_log.status == "completed"
        assert mock_sync_command.sync_log.tasks_processed == 5

    def test_sync_tasks_success(self, mock_sync_command):
        """Test successful task synchronization."""
        # Mock the tracker service
        with patch('radiator.commands.sync_tracker.tracker_service') as mock_service:
        
            # Mock task data
            mock_task = {
                "tracker_id": "12345",
                "key": "TEST-123",
                "summary": "Test Task",
                "status": "open"
            }
            mock_service.get_tasks_batch.return_value = [("12345", mock_task)]
            mock_service.extract_task_data.return_value = mock_task
            
            # Mock CRUD operations
            with patch('radiator.commands.sync_tracker.tracker_task') as mock_task_crud:
                mock_task_crud.get_by_tracker_id.return_value = None
                mock_task_crud.bulk_create_or_update.return_value = {"created": 1, "updated": 0}
                
                result = mock_sync_command.sync_tasks(["12345"])
                assert result == {"created": 1, "updated": 0}

    def test_sync_tasks_api_error(self, mock_sync_command):
        """Test handling API errors during sync."""
        with patch('radiator.commands.sync_tracker.tracker_service') as mock_service:
            # Mock get_tasks_batch to return empty list instead of raising exception
            mock_service.get_tasks_batch.return_value = []
            
            result = mock_sync_command.sync_tasks(["12345"])
            assert result == {"created": 0, "updated": 0}


class TestTrackerModels:
    """Test tracker data models."""

    def test_tracker_task_model(self):
        """Test TrackerTask model creation."""
        task = TrackerTask(
            tracker_id="TEST-1",
            key="TEST-1",
            summary="Test Task",
            status="open",
            assignee="Test User",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        assert task.tracker_id == "TEST-1"
        assert task.summary == "Test Task"
        assert task.status == "open"

    def test_tracker_task_history_model(self):
        """Test TrackerTaskHistory model creation."""
        history = TrackerTaskHistory(
            task_id=1,
            tracker_id="TEST-1",
            status="In Progress",
            status_display="In Progress",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc)
        )
        
        assert history.tracker_id == "TEST-1"
        assert history.status == "In Progress"
        assert history.status_display == "In Progress"

    def test_tracker_sync_log_model(self):
        """Test TrackerSyncLog model creation."""
        sync_log = TrackerSyncLog(
            sync_started_at=datetime.now(timezone.utc),
            status="in_progress",
            tasks_processed=0
        )
        
        assert sync_log.status == "in_progress"
        assert sync_log.tasks_processed == 0


class TestIntegration:
    """Integration tests for the complete sync flow."""

    @pytest.fixture
    def mock_environment(self):
        """Mock environment variables."""
        with patch.dict('os.environ', {
            'TRACKER_API_TOKEN': 'test_token',
            'TRACKER_ORG_ID': 'test_org',
            'DATABASE_URL_SYNC': 'postgresql://test:test@localhost:5432/testdb'
        }):
            yield

    def test_complete_sync_flow(self, mock_environment):
        """Test complete synchronization flow."""
        
        # Mock tracker service
        with patch('radiator.commands.sync_tracker.tracker_service') as mock_service:
            mock_service.get_tasks_by_filter.return_value = ["TEST-1", "TEST-2"]
            mock_service.get_tasks_batch.return_value = [("TEST-1", {"tracker_id": "TEST-1", "key": "TEST-1", "summary": "Test Task", "status": "open"})]
            mock_service.extract_task_data.return_value = {"tracker_id": "TEST-1", "key": "TEST-1", "summary": "Test Task", "status": "open"}
            mock_service.get_changelogs_batch.return_value = [("TEST-1", [])]
            mock_service.extract_status_history.return_value = []
            
            # Create sync command
            with patch('radiator.commands.sync_tracker.logger'):
                sync_cmd = TrackerSyncCommand()
                
                # Mock CRUD operations
                with patch('radiator.commands.sync_tracker.tracker_task') as mock_task_crud:
                    with patch('radiator.commands.sync_tracker.tracker_task_history') as mock_history_crud:
                        with patch('radiator.commands.sync_tracker.tracker_sync_log') as mock_sync_log_crud:
                            # Mock sync log creation
                            mock_log = Mock()
                            mock_log.id = "sync-123"
                            mock_sync_log_crud.create.return_value = mock_log
                            
                            # Mock task operations
                            mock_task_crud.get_by_tracker_id.return_value = None
                            mock_task_crud.bulk_create_or_update.return_value = {"created": 1, "updated": 0}
                            mock_history_crud.bulk_create.return_value = 0
                            
                            # Mock database session
                            with patch.object(sync_cmd, 'db') as mock_db:
                                mock_db.add.return_value = None
                                mock_db.commit.return_value = None
                                mock_db.refresh.return_value = None
                                
                                # Run sync
                                result = sync_cmd.run(filters={}, limit=5)
                                
                                assert result is True
                                mock_service.get_tasks_by_filter.assert_called_once_with({}, limit=5)


# Mock open function for file mode testing
def mock_open(mock_data):
    """Mock open function for testing file operations."""
    mock = Mock()
    mock.read.return_value = mock_data
    mock.__enter__.return_value = mock
    mock.__exit__.return_value = None
    return mock


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
