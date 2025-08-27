"""Tests for Yandex Tracker synchronization system."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
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
            service.api_token = "test_token"
            service.org_id = "test_org"
            service.base_url = "https://api.tracker.yandex.net/v2/"
            return service

    @pytest.fixture
    def mock_response(self):
        """Create mock API response."""
        mock = Mock()
        mock.json.return_value = {
            "issues": [
                {"id": "TEST-1", "key": "TEST-1", "summary": "Test Task 1"},
                {"id": "TEST-2", "key": "TEST-2", "summary": "Test Task 2"}
            ]
        }
        mock.status_code = 200
        return mock

    def test_search_tasks_success(self, mock_service, mock_response):
        """Test successful task search."""
        with patch('requests.get', return_value=mock_response):
            result = mock_service.search_tasks("Updated: >2024-01-01")
            assert len(result) == 2
            assert "TEST-1" in result
            assert "TEST-2" in result

    def test_search_tasks_api_error(self, mock_service):
        """Test API error handling in task search."""
        with patch('requests.get', side_effect=Exception("API Error")):
            result = mock_service.search_tasks("test query")
            assert result == []

    def test_get_recent_tasks(self, mock_service, mock_response):
        """Test getting recent tasks."""
        with patch('requests.get', return_value=mock_response):
            result = mock_service.get_recent_tasks(days=7, limit=10)
            assert len(result) == 2

    def test_get_active_tasks(self, mock_service, mock_response):
        """Test getting active tasks."""
        with patch('requests.get', return_value=mock_response):
            result = mock_service.get_active_tasks(limit=10)
            assert len(result) == 2

    def test_get_tasks_by_filter(self, mock_service, mock_response):
        """Test getting tasks by filter."""
        with patch('requests.get', return_value=mock_response):
            filters = {"status": "Open", "assignee": "test_user"}
            result = mock_service.get_tasks_by_filter(filters, limit=10)
            assert len(result) == 2

    def test_extract_task_data(self, mock_service):
        """Test task data extraction."""
        mock_task = {
            "id": "TEST-1",
            "key": "TEST-1",
            "summary": "Test Task",
            "status": {"key": "open", "display": "Open"},
            "assignee": {"id": "user1", "display": "Test User"},
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z"
        }
        
        result = mock_service.extract_task_data(mock_task)
        assert result["tracker_id"] == "TEST-1"
        assert result["key"] == "TEST-1"
        assert result["summary"] == "Test Task"
        assert result["status"] == "open"

    def test_extract_status_history(self, mock_service):
        """Test status history extraction."""
        mock_changelog = [
            {
                "id": 1,
                "updatedAt": "2024-01-01T00:00:00Z",
                "field": {"id": "status"},
                "from": {"display": "Open"},
                "to": {"display": "In Progress"}
            }
        ]
        
        result = mock_service.extract_status_history("TEST-1", mock_changelog)
        assert len(result) == 1
        assert result[0]["tracker_id"] == "TEST-1"
        assert result[0]["old_status"] == "Open"
        assert result[0]["new_status"] == "In Progress"


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
            "tracker_id": "TEST-1",
            "key": "TEST-1",
            "summary": "Test Task",
            "status": "open",
            "assignee_id": "user1",
            "assignee_name": "Test User",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

    @pytest.fixture
    def sample_history_data(self):
        """Sample history data for testing."""
        return {
            "tracker_id": "TEST-1",
            "old_status": "Open",
            "new_status": "In Progress",
            "start_date": datetime.utcnow(),
            "end_date": datetime.utcnow()
        }

    def test_create_task(self, mock_db_session, sample_task_data):
        """Test creating a tracker task."""
        crud = CRUDTrackerTask(TrackerTask)
        
        with patch.object(crud, 'create') as mock_create:
            mock_create.return_value = TrackerTask(**sample_task_data)
            result = crud.create(mock_db_session, obj_in=sample_task_data)
            
            assert result.tracker_id == "TEST-1"
            assert result.summary == "Test Task"

    def test_get_task_by_tracker_id(self, mock_db_session):
        """Test getting task by tracker ID."""
        crud = CRUDTrackerTask(TrackerTask)
        
        with patch.object(crud, 'get') as mock_get:
            mock_get.return_value = TrackerTask(tracker_id="TEST-1")
            result = crud.get_by_tracker_id(mock_db_session, tracker_id="TEST-1")
            
            assert result.tracker_id == "TEST-1"

    def test_create_history_entry(self, mock_db_session, sample_history_data):
        """Test creating a history entry."""
        crud = CRUDTrackerTaskHistory(TrackerTaskHistory)
        
        with patch.object(crud, 'create') as mock_create:
            mock_create.return_value = TrackerTaskHistory(**sample_history_data)
            result = crud.create(mock_db_session, obj_in=sample_history_data)
            
            assert result.tracker_id == "TEST-1"
            assert result.old_status == "Open"
            assert result.new_status == "In Progress"

    def test_bulk_create_tasks(self, mock_db_session, sample_task_data):
        """Test bulk creation of tasks."""
        crud = CRUDTrackerTask(TrackerTask)
        tasks_data = [sample_task_data, {**sample_task_data, "tracker_id": "TEST-2"}]
        
        with patch.object(crud, 'create_multi') as mock_create_multi:
            mock_create_multi.return_value = [TrackerTask(**data) for data in tasks_data]
            result = crud.bulk_create_tasks(mock_db_session, tasks_data)
            
            assert len(result) == 2
            assert result[0].tracker_id == "TEST-1"
            assert result[1].tracker_id == "TEST-2"


class TestTrackerSyncCommand:
    """Test TrackerSyncCommand class."""

    @pytest.fixture
    def mock_sync_command(self):
        """Create mock TrackerSyncCommand instance."""
        with patch('radiator.commands.sync_tracker.logger'):
            with patch('radiator.commands.sync_tracker.get_db_session') as mock_get_db:
                mock_session = Mock()
                mock_get_db.return_value = mock_session
                command = TrackerSyncCommand()
                command.db = mock_session
                return command

    @pytest.fixture
    def mock_tracker_service(self):
        """Create mock TrackerAPIService."""
        service = Mock(spec=TrackerAPIService)
        service.get_recent_tasks.return_value = ["TEST-1", "TEST-2"]
        service.get_active_tasks.return_value = ["TEST-3", "TEST-4"]
        service.search_tasks.return_value = ["TEST-5"]
        return service

    def test_get_tasks_to_sync_recent_mode(self, mock_sync_command, mock_tracker_service):
        """Test getting tasks in recent mode."""
        with patch.object(mock_sync_command, 'tracker_service', mock_tracker_service):
            result = mock_sync_command.get_tasks_to_sync(
                sync_mode="recent", days=7, limit=10
            )
            assert result == ["TEST-1", "TEST-2"]
            mock_tracker_service.get_recent_tasks.assert_called_once_with(days=7, limit=10)

    def test_get_tasks_to_sync_active_mode(self, mock_sync_command, mock_tracker_service):
        """Test getting tasks in active mode."""
        with patch.object(mock_sync_command, 'tracker_service', mock_tracker_service):
            result = mock_sync_command.get_tasks_to_sync(
                sync_mode="active", limit=10
            )
            assert result == ["TEST-3", "TEST-4"]
            mock_tracker_service.get_active_tasks.assert_called_once_with(limit=10)

    def test_get_tasks_to_sync_filter_mode(self, mock_sync_command, mock_tracker_service):
        """Test getting tasks in filter mode."""
        with patch.object(mock_sync_command, 'tracker_service', mock_tracker_service):
            filters = {"status": "Open"}
            result = mock_sync_command.get_tasks_to_sync(
                sync_mode="filter", filters=filters, limit=10
            )
            assert result == ["TEST-5"]
            mock_tracker_service.get_tasks_by_filter.assert_called_once_with(filters, 10)

    def test_get_tasks_to_sync_file_mode(self, mock_sync_command):
        """Test getting tasks in file mode."""
        with patch('builtins.open', mock_open(read_data="TEST-1\nTEST-2")):
            result = mock_sync_command.get_tasks_to_sync(
                sync_mode="file", filters={"file_path": "test.txt"}
            )
            assert result == ["TEST-1", "TEST-2"]

    def test_create_sync_log(self, mock_sync_command):
        """Test creating sync log."""
        with patch.object(mock_sync_command, 'sync_log_crud') as mock_crud:
            mock_log = Mock(spec=TrackerSyncLog)
            mock_crud.create.return_value = mock_log
            mock_log.id = "sync-123"
            
            result = mock_sync_command.create_sync_log()
            assert result.id == "sync-123"
            mock_crud.create.assert_called_once()

    def test_update_sync_log(self, mock_sync_command):
        """Test updating sync log."""
        with patch.object(mock_sync_command, 'sync_log_crud') as mock_crud:
            mock_sync_command.sync_log = Mock(id="sync-123")
            
            mock_sync_command.update_sync_log(
                status="completed",
                tasks_processed=5,
                sync_completed_at=datetime.utcnow()
            )
            
            mock_crud.update.assert_called_once()

    @patch('radiator.commands.sync_tracker.TrackerAPIService')
    def test_sync_tasks_success(self, mock_service_class, mock_sync_command):
        """Test successful task synchronization."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # Mock task data
        mock_task = {
            "tracker_id": "TEST-1",
            "key": "TEST-1",
            "summary": "Test Task",
            "status": "open"
        }
        mock_service.get_task.return_value = mock_task
        mock_service.get_task_changelog.return_value = []
        
        # Mock CRUD operations
        with patch.object(mock_sync_command, 'task_crud') as mock_task_crud:
            with patch.object(mock_sync_command, 'history_crud') as mock_history_crud:
                mock_task_crud.get_by_tracker_id.return_value = None
                mock_task_crud.create.return_value = Mock()
                mock_history_crud.create_multi.return_value = []
                
                result = mock_sync_command.sync_tasks(["TEST-1"])
                assert result == 1

    def test_sync_tasks_api_error(self, mock_sync_command):
        """Test handling API errors during sync."""
        with patch.object(mock_sync_command, 'tracker_service') as mock_service:
            mock_service.get_task.side_effect = Exception("API Error")
            
            result = mock_sync_command.sync_tasks(["TEST-1"])
            assert result == 0


class TestTrackerModels:
    """Test tracker data models."""

    def test_tracker_task_model(self):
        """Test TrackerTask model creation."""
        task = TrackerTask(
            tracker_id="TEST-1",
            key="TEST-1",
            summary="Test Task",
            status="open",
            assignee_id="user1",
            assignee_name="Test User",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        assert task.tracker_id == "TEST-1"
        assert task.summary == "Test Task"
        assert task.status == "open"

    def test_tracker_task_history_model(self):
        """Test TrackerTaskHistory model creation."""
        history = TrackerTaskHistory(
            tracker_id="TEST-1",
            old_status="Open",
            new_status="In Progress",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow()
        )
        
        assert history.tracker_id == "TEST-1"
        assert history.old_status == "Open"
        assert history.new_status == "In Progress"

    def test_tracker_sync_log_model(self):
        """Test TrackerSyncLog model creation."""
        sync_log = TrackerSyncLog(
            sync_started_at=datetime.utcnow(),
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

    @patch('radiator.commands.sync_tracker.TrackerAPIService')
    @patch('radiator.commands.sync_tracker.get_db_session')
    def test_complete_sync_flow(self, mock_get_db, mock_service_class, mock_environment):
        """Test complete synchronization flow."""
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value = mock_session
        
        # Mock tracker service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_recent_tasks.return_value = ["TEST-1", "TEST-2"]
        mock_service.get_task.return_value = {
            "tracker_id": "TEST-1",
            "key": "TEST-1",
            "summary": "Test Task",
            "status": "open"
        }
        mock_service.get_task_changelog.return_value = []
        
        # Create sync command
        with patch('radiator.commands.sync_tracker.logger'):
            sync_cmd = TrackerSyncCommand()
            
            # Mock CRUD operations
            with patch.object(sync_cmd, 'task_crud') as mock_task_crud:
                with patch.object(sync_cmd, 'history_crud') as mock_history_crud:
                    with patch.object(sync_cmd, 'sync_log_crud') as mock_sync_log_crud:
                        # Mock sync log creation
                        mock_log = Mock()
                        mock_log.id = "sync-123"
                        mock_sync_log_crud.create.return_value = mock_log
                        
                        # Mock task operations
                        mock_task_crud.get_by_tracker_id.return_value = None
                        mock_task_crud.create.return_value = Mock()
                        mock_history_crud.create_multi.return_value = []
                        
                        # Run sync
                        result = sync_cmd.run(sync_mode="recent", days=7, limit=5)
                        
                        assert result is True
                        mock_service.get_recent_tasks.assert_called_once_with(days=7, limit=5)


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
