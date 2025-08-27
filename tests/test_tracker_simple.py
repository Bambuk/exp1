"""Simple tests for tracker functionality."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from radiator.models.tracker import TrackerTask, TrackerTaskHistory, TrackerSyncLog


class TestTrackerModels:
    """Test tracker data models."""

    def test_tracker_task_model(self):
        """Test TrackerTask model creation."""
        task = TrackerTask(
            tracker_id="TEST-1",
            summary="Test Task",
            status="open",
            author="user1",
            assignee="Test User"
        )
        
        assert task.tracker_id == "TEST-1"
        assert task.summary == "Test Task"
        assert task.status == "open"
        assert task.author == "user1"
        assert task.assignee == "Test User"

    def test_tracker_task_history_model(self):
        """Test TrackerTaskHistory model creation."""
        history = TrackerTaskHistory(
            task_id=1,
            tracker_id="TEST-1",
            status="open",
            status_display="Open",
            start_date=datetime.utcnow()
        )
        
        assert history.tracker_id == "TEST-1"
        assert history.status == "open"
        assert history.status_display == "Open"

    def test_tracker_sync_log_model(self):
        """Test TrackerSyncLog model creation."""
        sync_log = TrackerSyncLog(
            sync_started_at=datetime.utcnow(),
            status="running",
            tasks_processed=0
        )
        
        assert sync_log.status == "running"
        assert sync_log.tasks_processed == 0


class TestTrackerAPIService:
    """Test TrackerAPIService class."""

    def test_service_initialization(self):
        """Test service initialization."""
        from radiator.services.tracker_service import TrackerAPIService
        
        with patch('radiator.services.tracker_service.logger'):
            service = TrackerAPIService()
            # Check that service can be created
            assert service is not None
            assert hasattr(service, 'base_url')
            assert hasattr(service, 'max_workers')
            assert hasattr(service, 'request_delay')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
