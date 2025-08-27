"""Test integration of the key field in tracker system."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from radiator.models.tracker import TrackerTask
from radiator.services.tracker_service import TrackerAPIService
from radiator.crud.tracker import CRUDTrackerTask


class TestTrackerKeyIntegration:
    """Test that the key field is properly integrated."""

    def test_tracker_task_model_has_key_field(self):
        """Test that TrackerTask model has the key field."""
        # Create a task with key field
        task = TrackerTask(
            tracker_id="TEST-1",
            key="TEST-123",
            summary="Test Task",
            status="open"
        )
        
        assert task.key == "TEST-123"
        assert hasattr(task, 'key')
        assert 'key' in [c.name for c in TrackerTask.__table__.columns]

    def test_api_service_extracts_key_field(self):
        """Test that TrackerAPIService extracts the key field from API response."""
        service = TrackerAPIService()
        
        # Mock API response with key field
        mock_task_data = {
            "id": "TEST-1",
            "key": "TEST-123",
            "summary": "Test Task",
            "status": {"key": "open", "display": "Open"},
            "assignee": {"id": "user1", "display": "Test User"}
        }
        
        result = service.extract_task_data(mock_task_data)
        
        assert result["key"] == "TEST-123"
        assert result["tracker_id"] == "TEST-1"
        assert result["summary"] == "Test Task"

    def test_crud_operations_with_key_field(self):
        """Test that CRUD operations work with the key field."""
        crud = CRUDTrackerTask(TrackerTask)
        
        # Test data with key field
        task_data = {
            "tracker_id": "TEST-1",
            "key": "TEST-123",
            "summary": "Test Task",
            "status": "open",
            "author": "user1",
            "assignee": "Test User"
        }
        
        # Test that we can create a task with key
        task = TrackerTask(**task_data)
        assert task.key == "TEST-123"
        assert task.tracker_id == "TEST-1"

    def test_key_field_in_bulk_operations(self):
        """Test that key field is handled in bulk operations."""
        crud = CRUDTrackerTask(TrackerTask)
        
        # Multiple tasks with different keys
        tasks_data = [
            {
                "tracker_id": "TEST-1",
                "key": "TEST-123",
                "summary": "Task 1",
                "status": "open"
            },
            {
                "tracker_id": "TEST-2",
                "key": "TEST-456",
                "summary": "Task 2",
                "status": "in_progress"
            }
        ]
        
        # Create tasks with keys
        tasks = [TrackerTask(**data) for data in tasks_data]
        
        assert len(tasks) == 2
        assert tasks[0].key == "TEST-123"
        assert tasks[1].key == "TEST-456"
        assert tasks[0].tracker_id == "TEST-1"
        assert tasks[1].tracker_id == "TEST-2"

    def test_key_field_indexing(self):
        """Test that key field has proper indexing."""
        # Check that key field has an index
        key_column = TrackerTask.__table__.columns.get('key')
        assert key_column is not None
        
        # Check that key field is indexed (this is set in the model)
        indexes = [idx.name for idx in TrackerTask.__table__.indexes]
        assert 'idx_tracker_tasks_key' in indexes or any('key' in idx.name for idx in TrackerTask.__table__.indexes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
