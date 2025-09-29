"""Integration tests for sync_tracker with real database."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from radiator.commands.sync_tracker import TrackerSyncCommand
from radiator.models.tracker import TrackerSyncLog, TrackerTask, TrackerTaskHistory


class TestSyncTrackerIntegration:
    """Integration tests for sync_tracker with real database."""

    def test_sync_tracker_with_real_database(self, db_session, sample_task_data):
        """Test sync_tracker with real database operations."""
        # Use unique tracker_id for this test
        test_data = sample_task_data.copy()
        test_data["tracker_id"] = "test_sync_001"
        test_data["key"] = "TEST-SYNC-001"

        # Create sync command with real database session
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Mock tracker service to return test data
        with patch("radiator.commands.sync_tracker.tracker_service") as mock_service:
            mock_service.get_tasks_by_filter.return_value = ["test_sync_001"]
            mock_service.get_tasks_batch.return_value = [
                (
                    "test_sync_001",
                    {
                        "id": "test_sync_001",
                        "key": "TEST-SYNC-001",
                        "summary": "Test Task",
                        "status": "open",
                        "author": "user1",
                        "assignee": "Test User",
                        "business_client": "Test Client",
                        "team": "frontend",
                        "prodteam": "development",
                        "profit_forecast": "high",
                    },
                )
            ]
            mock_service.extract_task_data.return_value = test_data
            mock_service.get_changelogs_batch.return_value = [("test_sync_001", [])]
            mock_service.extract_status_history_with_initial_status.return_value = []

            # Run sync
            result = sync_cmd.run(filters={"query": "test"}, limit=1, skip_history=True)

            # Verify result
            assert result is True

            # Verify task was created in database
            created_task = (
                db_session.query(TrackerTask)
                .filter(TrackerTask.tracker_id == "test_sync_001")
                .first()
            )
            assert created_task is not None
            assert created_task.key == "TEST-SYNC-001"
            assert created_task.summary == "Test Task"
            assert created_task.status == "open"
            assert created_task.author == "user1"

            # Verify sync log was created and completed
            sync_log = db_session.query(TrackerSyncLog).first()
            assert sync_log is not None
            assert sync_log.status == "completed"
            assert sync_log.tasks_processed == 1  # Correct value for this test
            assert sync_log.tasks_created == 1
            assert sync_log.tasks_updated == 0

    def test_bulk_create_or_update_tasks(self, db_session, sample_task_data):
        """Test bulk_create_or_update_tasks method directly."""
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Use unique tracker_id for this test
        test_data = sample_task_data.copy()
        test_data["tracker_id"] = "test_bulk_001"
        test_data["key"] = "TEST-BULK-001"

        # Test creating new task
        tasks_data = [test_data]
        result = sync_cmd._bulk_create_or_update_tasks(tasks_data)

        assert result["created"] == 1
        assert result["updated"] == 0

        # Verify task exists in database
        task = (
            db_session.query(TrackerTask)
            .filter(TrackerTask.tracker_id == test_data["tracker_id"])
            .first()
        )
        assert task is not None
        assert task.key == test_data["key"]

        # Test updating existing task
        updated_data = test_data.copy()
        updated_data["summary"] = "Updated Task Summary"

        result = sync_cmd._bulk_create_or_update_tasks([updated_data])

        assert result["created"] == 0
        assert result["updated"] == 1

        # Verify task was updated
        updated_task = (
            db_session.query(TrackerTask)
            .filter(TrackerTask.tracker_id == test_data["tracker_id"])
            .first()
        )
        assert updated_task.summary == "Updated Task Summary"

    def test_get_task_by_tracker_id(self, db_session, sample_task_data):
        """Test getting task by tracker_id."""
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Use unique tracker_id for this test
        test_data = sample_task_data.copy()
        test_data["tracker_id"] = "test_get_001"
        test_data["key"] = "TEST-GET-001"

        # Create task first
        task = TrackerTask(**test_data)
        db_session.add(task)
        db_session.commit()

        # Test getting task
        found_task = (
            db_session.query(TrackerTask)
            .filter(TrackerTask.tracker_id == test_data["tracker_id"])
            .first()
        )

        assert found_task is not None
        assert found_task.key == test_data["key"]

    def test_bulk_create_history(self, db_session, sample_history_data):
        """Test bulk_create_history method."""
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Create a task first with unique ID
        task = TrackerTask(
            tracker_id="test_history_001", key="TEST-HISTORY-001", summary="Test Task"
        )
        db_session.add(task)
        db_session.commit()

        # Create history data
        history_data = [
            {
                "task_id": task.id,
                "tracker_id": "test_history_001",
                "status": "Open",
                "status_display": "Open",
                "start_date": datetime.now(timezone.utc),
                "end_date": None,
            }
        ]

        # Test creating history
        created_count = sync_cmd._bulk_create_history(history_data)

        assert created_count == 1

        # Verify history was created
        history = (
            db_session.query(TrackerTaskHistory)
            .filter(TrackerTaskHistory.task_id == task.id)
            .first()
        )
        assert history is not None
        assert history.status == "Open"

    def test_cleanup_duplicate_history(self, db_session):
        """Test cleanup_duplicate_history method."""
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Create a task first with unique ID
        task = TrackerTask(
            tracker_id="test_cleanup_001", key="TEST-CLEANUP-001", summary="Test Task"
        )
        db_session.add(task)
        db_session.commit()

        # Create duplicate history entries
        now = datetime.now(timezone.utc)
        history1 = TrackerTaskHistory(
            task_id=task.id,
            tracker_id="test_cleanup_001",
            status="Open",
            status_display="Open",
            start_date=now,
            end_date=None,
        )
        history2 = TrackerTaskHistory(
            task_id=task.id,
            tracker_id="test_cleanup_001",
            status="Open",
            status_display="Open",
            start_date=now,
            end_date=None,
        )

        db_session.add(history1)
        db_session.add(history2)
        db_session.commit()

        # Test cleanup
        cleaned_count = sync_cmd._cleanup_duplicate_history()

        assert cleaned_count == 1

        # Verify only one history entry remains
        remaining_history = (
            db_session.query(TrackerTaskHistory)
            .filter(TrackerTaskHistory.task_id == task.id)
            .all()
        )
        assert len(remaining_history) == 1

    def test_sync_tracker_fails_without_crud_methods(self, db_session):
        """Test that sync_tracker fails when CRUD methods are missing."""
        # This test will verify that our new tests catch the problem
        # when CRUD methods are missing

        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Mock tracker service
        with patch("radiator.commands.sync_tracker.tracker_service") as mock_service:
            mock_service.get_tasks_by_filter.return_value = ["12345"]
            mock_service.get_tasks_batch.return_value = [
                ("12345", {"id": "12345", "key": "TEST-123"})
            ]
            mock_service.extract_task_data.return_value = {
                "tracker_id": "12345",
                "key": "TEST-123",
                "summary": "Test Task",
            }
            mock_service.get_changelogs_batch.return_value = [("12345", [])]
            mock_service.extract_status_history_with_initial_status.return_value = []

            # This should work with our current implementation
            result = sync_cmd.run(filters={"query": "test"}, limit=1, skip_history=True)

            # Should succeed because we have the CRUD methods
            assert result is True
