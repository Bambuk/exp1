"""Tests for tracker CRUD operations."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from radiator.models.tracker import TrackerTask, TrackerTaskHistory, TrackerSyncLog
from radiator.crud.tracker import (
    CRUDTrackerTask,
    CRUDTrackerTaskHistory,
    CRUDTrackerSyncLog
)




class TestCRUDTrackerTask:
    """Test CRUD operations for TrackerTask."""

    @pytest.fixture
    def crud(self):
        """Create CRUD instance."""
        return CRUDTrackerTask(TrackerTask)

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for testing."""
        return {
            "tracker_id": "TEST-1",
            "key": "TEST-1",
            "summary": "Test Task",
            "description": "Test Description",
            "status": "open",
            "priority": "normal",
            "assignee_id": "user1",
            "assignee_name": "Test User",
            "reporter_id": "user2",
            "reporter_name": "Reporter User",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "resolved_at": None,
            "due_date": None,
            "tags": ["test", "bug"],
            "components": ["frontend"],
            "versions": ["v1.0"],
            "labels": ["urgent"]
        }

    def test_create_task(self, crud, mock_session, sample_task_data):
        """Test creating a single task."""
        with patch.object(crud, 'create') as mock_create:
            mock_task = TrackerTask(**sample_task_data)
            mock_create.return_value = mock_task
            
            result = crud.create(mock_session, obj_in=sample_task_data)
            
            assert result.tracker_id == "TEST-1"
            assert result.summary == "Test Task"
            assert result.status == "open"
            mock_create.assert_called_once_with(mock_session, obj_in=sample_task_data)

    def test_get_by_tracker_id(self, crud, mock_session):
        """Test getting task by tracker ID."""
        mock_task = TrackerTask(tracker_id="TEST-1", summary="Test Task")
        
        with patch.object(crud, 'get') as mock_get:
            mock_get.return_value = mock_task
            
            result = crud.get_by_tracker_id(mock_session, tracker_id="TEST-1")
            
            assert result.tracker_id == "TEST-1"
            assert result.summary == "Test Task"
            mock_get.assert_called_once_with(mock_session, id="TEST-1")

    def test_get_by_tracker_id_not_found(self, crud, mock_session):
        """Test getting task by tracker ID when not found."""
        with patch.object(crud, 'get') as mock_get:
            mock_get.return_value = None
            
            result = crud.get_by_tracker_id(mock_session, tracker_id="NONEXISTENT")
            
            assert result is None

    def test_update_task(self, crud, mock_session, sample_task_data):
        """Test updating a task."""
        mock_task = TrackerTask(**sample_task_data)
        update_data = {"status": "in_progress", "summary": "Updated Task"}
        
        with patch.object(crud, 'update') as mock_update:
            mock_updated_task = TrackerTask(**{**sample_task_data, **update_data})
            mock_update.return_value = mock_updated_task
            
            result = crud.update(mock_session, db_obj=mock_task, obj_in=update_data)
            
            assert result.status == "in_progress"
            assert result.summary == "Updated Task"
            mock_update.assert_called_once_with(mock_session, db_obj=mock_task, obj_in=update_data)

    def test_delete_task(self, crud, mock_session, sample_task_data):
        """Test deleting a task."""
        mock_task = TrackerTask(**sample_task_data)
        
        with patch.object(crud, 'remove') as mock_remove:
            mock_remove.return_value = mock_task
            
            result = crud.delete(mock_session, id="TEST-1")
            
            assert result.tracker_id == "TEST-1"
            mock_remove.assert_called_once_with(mock_session, id="TEST-1")

    def test_get_tasks_by_status(self, crud, mock_session):
        """Test getting tasks by status."""
        mock_tasks = [
            TrackerTask(tracker_id="TEST-1", status="open"),
            TrackerTask(tracker_id="TEST-2", status="open"),
            TrackerTask(tracker_id="TEST-3", status="closed")
        ]
        
        with patch.object(crud, 'get_multi') as mock_get_multi:
            mock_get_multi.return_value = mock_tasks[:2]
            
            result = crud.get_tasks_by_status(mock_session, status="open")
            
            assert len(result) == 2
            assert all(task.status == "open" for task in result)

    def test_get_tasks_by_assignee(self, crud, mock_session):
        """Test getting tasks by assignee."""
        mock_tasks = [
            TrackerTask(tracker_id="TEST-1", assignee="user1"),
            TrackerTask(tracker_id="TEST-2", assignee="user1"),
            TrackerTask(tracker_id="TEST-3", assignee="user2")
        ]
        
        with patch.object(crud, 'get_multi') as mock_get_multi:
            mock_get_multi.return_value = mock_tasks[:2]
            
            result = crud.get_tasks_by_assignee(mock_session, assignee_id="user1")
            
            assert len(result) == 2
            assert all(task.assignee == "user1" for task in result)

    def test_bulk_create_tasks(self, crud, mock_session, sample_task_data):
        """Test bulk creation of tasks."""
        tasks_data = [
            sample_task_data,
            {**sample_task_data, "tracker_id": "TEST-2"},
            {**sample_task_data, "tracker_id": "TEST-3"}
        ]
        
        with patch.object(crud, 'create_multi') as mock_create_multi:
            mock_created_tasks = [TrackerTask(**data) for data in tasks_data]
            mock_create_multi.return_value = mock_created_tasks
            
            result = crud.bulk_create_tasks(mock_session, tasks_data)
            
            assert len(result) == 3
            assert result[0].tracker_id == "TEST-1"
            assert result[1].tracker_id == "TEST-2"
            assert result[2].tracker_id == "TEST-3"
            mock_create_multi.assert_called_once_with(mock_session, obj_in_list=tasks_data)

    def test_get_tasks_updated_since(self, crud, mock_session):
        """Test getting tasks updated since a specific date."""
        updated_since = datetime.utcnow() - timedelta(days=7)
        mock_tasks = [
            TrackerTask(tracker_id="TEST-1", updated_at=datetime.utcnow()),
            TrackerTask(tracker_id="TEST-2", updated_at=datetime.utcnow() - timedelta(days=3))
        ]
        
        with patch.object(crud, 'get_multi') as mock_get_multi:
            mock_get_multi.return_value = mock_tasks
            
            result = crud.get_tasks_updated_since(mock_session, updated_since=updated_since)
            
            assert len(result) == 2
            mock_get_multi.assert_called_once()


class TestCRUDTrackerTaskHistory:
    """Test CRUD operations for TrackerTaskHistory."""

    @pytest.fixture
    def crud(self):
        """Create CRUD instance."""
        return CRUDTrackerTaskHistory(TrackerTaskHistory)

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def sample_history_data(self):
        """Sample history data for testing."""
        return {
            "tracker_id": "TEST-1",
            "old_status": "Open",
            "new_status": "In Progress",
            "start_date": datetime.utcnow(),
            "end_date": datetime.utcnow() + timedelta(hours=2),
            "duration_minutes": 120,
            "changed_by": "user1",
            "change_reason": "Work started"
        }

    def test_create_history_entry(self, crud, mock_session, sample_history_data):
        """Test creating a history entry."""
        with patch.object(crud, 'create') as mock_create:
            mock_history = TrackerTaskHistory(**sample_history_data)
            mock_create.return_value = mock_history
            
            result = crud.create(mock_session, obj_in=sample_history_data)
            
            assert result.tracker_id == "TEST-1"
            assert result.old_status == "Open"
            assert result.new_status == "In Progress"
            mock_create.assert_called_once_with(mock_session, obj_in=sample_history_data)

    def test_get_history_for_task(self, crud, mock_session):
        """Test getting history for a specific task."""
        mock_history = [
            TrackerTaskHistory(tracker_id="TEST-1", old_status="Open", new_status="In Progress"),
            TrackerTaskHistory(tracker_id="TEST-1", old_status="In Progress", new_status="Testing")
        ]
        
        with patch.object(crud, 'get_multi') as mock_get_multi:
            mock_get_multi.return_value = mock_history
            
            result = crud.get_history_for_task(mock_session, tracker_id="TEST-1")
            
            assert len(result) == 2
            assert all(entry.tracker_id == "TEST-1" for entry in result)

    def test_get_status_changes(self, crud, mock_session):
        """Test getting status changes for a task."""
        mock_changes = [
            TrackerTaskHistory(tracker_id="TEST-1", old_status="Open", new_status="In Progress"),
            TrackerTaskHistory(tracker_id="TEST-1", old_status="In Progress", new_status="Testing")
        ]
        
        with patch.object(crud, 'get_multi') as mock_get_multi:
            mock_get_multi.return_value = mock_changes
            
            result = crud.get_status_changes(mock_session, tracker_id="TEST-1")
            
            assert len(result) == 2
            assert result[0].old_status == "Open"
            assert result[0].new_status == "In Progress"

    def test_bulk_create_history(self, crud, mock_session, sample_history_data):
        """Test bulk creation of history entries."""
        history_data = [
            sample_history_data,
            {**sample_history_data, "old_status": "In Progress", "new_status": "Testing"}
        ]
        
        with patch.object(crud, 'create_multi') as mock_create_multi:
            mock_created_history = [TrackerTaskHistory(**data) for data in history_data]
            mock_create_multi.return_value = mock_created_history
            
            result = crud.bulk_create_history(mock_session, history_data)
            
            assert len(result) == 2
            assert result[0].new_status == "In Progress"
            assert result[1].new_status == "Testing"


class TestCRUDTrackerSyncLog:
    """Test CRUD operations for TrackerSyncLog."""

    @pytest.fixture
    def crud(self):
        """Create CRUD instance."""
        return CRUDTrackerSyncLog(TrackerSyncLog)

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def sample_sync_log_data(self):
        """Sample sync log data for testing."""
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

    def test_create_sync_log(self, crud, mock_session, sample_sync_log_data):
        """Test creating a sync log entry."""
        with patch.object(crud, 'create') as mock_create:
            mock_log = TrackerSyncLog(**sample_sync_log_data)
            mock_log.id = "sync-123"
            mock_create.return_value = mock_log
            
            result = crud.create(mock_session, obj_in=sample_sync_log_data)
            
            assert result.id == "sync-123"
            assert result.status == "in_progress"
            mock_create.assert_called_once_with(mock_session, obj_in=sample_sync_log_data)

    def test_get_latest_sync_log(self, crud, mock_session):
        """Test getting the latest sync log."""
        mock_log = TrackerSyncLog(id="sync-123", status="completed")
        
        with patch.object(crud, 'get_multi') as mock_get_multi:
            mock_get_multi.return_value = [mock_log]
            
            result = crud.get_latest_sync_log(mock_session)
            
            assert result.id == "sync-123"
            assert result.status == "completed"

    def test_get_sync_logs_by_status(self, crud, mock_session):
        """Test getting sync logs by status."""
        mock_logs = [
            TrackerSyncLog(id="sync-1", status="completed"),
            TrackerSyncLog(id="sync-2", status="completed"),
            TrackerSyncLog(id="sync-3", status="failed")
        ]
        
        with patch.object(crud, 'get_multi') as mock_get_multi:
            mock_get_multi.return_value = mock_logs[:2]
            
            result = crud.get_sync_logs_by_status(mock_session, status="completed")
            
            assert len(result) == 2
            assert all(log.status == "completed" for log in result)

    def test_get_sync_statistics(self, crud, mock_session):
        """Test getting sync statistics."""
        mock_logs = [
            TrackerSyncLog(tasks_processed=10, tasks_created=5, tasks_updated=3),
            TrackerSyncLog(tasks_processed=15, tasks_created=8, tasks_updated=4),
            TrackerSyncLog(tasks_processed=8, tasks_created=2, tasks_updated=1)
        ]
        
        with patch.object(crud, 'get_multi') as mock_get_multi:
            mock_get_multi.return_value = mock_logs
            
            result = crud.get_sync_statistics(mock_session, days=7)
            
            assert result["total_syncs"] == 3
            assert result["total_tasks_processed"] == 33
            assert result["total_tasks_created"] == 15
            assert result["total_tasks_updated"] == 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
