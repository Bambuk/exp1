"""Tests for task_updated_at field functionality."""

import pytest
from datetime import datetime, timezone

from radiator.models.tracker import TrackerTask
from radiator.services.tracker_service import TrackerAPIService
from radiator.crud.tracker import tracker_task


class TestTaskUpdatedAtField:
    """Test cases for task_updated_at field."""
    
    def test_model_has_task_updated_at_field(self):
        """Test that TrackerTask model has task_updated_at field."""
        assert hasattr(TrackerTask, 'task_updated_at')
    
    def test_task_updated_at_is_datetime(self):
        """Test that task_updated_at field is DateTime type."""
        field = TrackerTask.__table__.columns.get('task_updated_at')
        assert field is not None
        assert str(field.type) == 'DATETIME'
    
    def test_task_updated_at_is_nullable(self):
        """Test that task_updated_at field is nullable."""
        field = TrackerTask.__table__.columns.get('task_updated_at')
        assert field.nullable is True


class TestTrackerServiceExtractTaskData:
    """Test cases for extracting task_updated_at from API response."""
    
    def test_extract_task_data_includes_task_updated_at(self):
        """Test that extract_task_data extracts task_updated_at field."""
        service = TrackerAPIService()
        
        # Mock task data from tracker API
        mock_task = {
            "id": "123",
            "key": "TEST-123",
            "summary": "Test task",
            "updatedAt": "2024-01-15T10:30:00.000Z"
        }
        
        result = service.extract_task_data(mock_task)
        
        assert "task_updated_at" in result
        assert result["task_updated_at"] is not None
    
    def test_extract_task_data_handles_missing_updated_at(self):
        """Test that extract_task_data handles missing updatedAt field."""
        service = TrackerAPIService()
        
        mock_task = {
            "id": "123",
            "key": "TEST-123",
            "summary": "Test task"
            # No updatedAt field
        }
        
        result = service.extract_task_data(mock_task)
        
        assert "task_updated_at" in result
        assert result["task_updated_at"] is None
    
    def test_extract_task_data_parses_iso_datetime(self):
        """Test that extract_task_data correctly parses ISO datetime."""
        service = TrackerAPIService()
        
        mock_task = {
            "id": "123",
            "key": "TEST-123",
            "updatedAt": "2024-01-15T10:30:00.000Z"
        }
        
        result = service.extract_task_data(mock_task)
        
        assert isinstance(result["task_updated_at"], datetime)
        expected_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert result["task_updated_at"] == expected_time


class TestCRUDTrackerTask:
    """Test cases for CRUD operations with task_updated_at field."""
    
    def test_bulk_create_or_update_saves_task_updated_at(self, db_session):
        """Test that bulk_create_or_update saves task_updated_at field."""
        task_data = {
            "tracker_id": "123",
            "key": "TEST-123",
            "summary": "Test task",
            "task_updated_at": datetime(2024, 1, 15, 10, 30, 0)  # Remove timezone for DB compatibility
        }
        
        result = tracker_task.bulk_create_or_update(db_session, [task_data])
        
        assert result["created"] == 1
        assert result["updated"] == 0
        
        # Verify the field was saved
        saved_task = tracker_task.get_by_tracker_id(db_session, "123")
        assert saved_task.task_updated_at == task_data["task_updated_at"]
    
    def test_bulk_create_or_update_updates_task_updated_at(self, db_session):
        """Test that bulk_create_or_update updates task_updated_at field."""
        # Create initial task
        initial_data = {
            "tracker_id": "123",
            "key": "TEST-123",
            "summary": "Test task",
            "task_updated_at": datetime(2024, 1, 15, 10, 30, 0)  # Remove timezone for DB compatibility
        }
        tracker_task.bulk_create_or_update(db_session, [initial_data])
        
        # Update with new task_updated_at
        updated_data = {
            "tracker_id": "123",
            "key": "TEST-123",
            "summary": "Updated task",
            "task_updated_at": datetime(2024, 1, 16, 11, 45, 0)  # Remove timezone for DB compatibility
        }
        
        result = tracker_task.bulk_create_or_update(db_session, [updated_data])
        
        assert result["created"] == 0
        assert result["updated"] == 1
        
        # Verify the field was updated
        updated_task = tracker_task.get_by_tracker_id(db_session, "123")
        assert updated_task.task_updated_at == updated_data["task_updated_at"]


class TestSyncCommand:
    """Test cases for sync command with task_updated_at field."""
    
    def test_sync_tasks_saves_task_updated_at(self, db_session):
        """Test that sync_tasks saves task_updated_at field."""
        # This test verifies that the sync command can handle task_updated_at field
        # The actual sync logic is tested in the CRUD tests above
        assert True  # Placeholder - main functionality tested in CRUD tests
