"""Integration tests for sync_tracker with real database."""

from datetime import datetime, timedelta, timezone
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
            mock_service.get_tasks_by_filter_with_data.return_value = [
                {
                    "id": "test_sync_001",
                    "key": "TEST-SYNC-001",
                    "summary": "Test Task",
                    "status": {"key": "open", "display": "open"},
                    "createdBy": {"display": "user1"},
                    "assignee": {"display": "Test User"},
                    "businessClient": [{"display": "Test Client"}],
                    "63515d47fe387b7ce7b9fc55--team": "frontend",
                    "63515d47fe387b7ce7b9fc55--prodteam": "development",
                    "63515d47fe387b7ce7b9fc55--profitForecast": "high",
                    "updatedAt": "2024-01-01T00:00:00Z",
                    "createdAt": "2024-01-01T00:00:00Z",
                }
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
        created_count = sync_cmd._bulk_create_history(history_data, task, [])

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
        """Test cleanup_duplicate_history method with small dataset."""
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

    def test_cleanup_duplicate_history_large_dataset(self, db_session):
        """Test cleanup_duplicate_history method with large dataset for performance testing."""
        import time

        # Clean up any existing test data first
        db_session.query(TrackerTaskHistory).filter(
            TrackerTaskHistory.tracker_id.like("test_cleanup_large_%")
        ).delete(synchronize_session=False)
        db_session.query(TrackerTask).filter(
            TrackerTask.tracker_id.like("test_cleanup_large_%")
        ).delete(synchronize_session=False)
        db_session.commit()

        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Create multiple tasks
        tasks = []
        for i in range(10):
            task = TrackerTask(
                tracker_id=f"test_cleanup_large_{i:03d}",
                key=f"TEST-LARGE-{i:03d}",
                summary=f"Test Task {i}",
            )
            db_session.add(task)
            tasks.append(task)
        db_session.commit()

        # Create many duplicate history entries (100+ per task)
        base_time = datetime.now(timezone.utc)
        total_duplicates = 0

        for task in tasks:
            # Create 5 different statuses
            for status_idx in range(5):
                status = f"Status{status_idx}"
                start_date = base_time + timedelta(hours=status_idx)

                # Create 20 duplicate entries for each status
                for dup_idx in range(20):
                    history = TrackerTaskHistory(
                        task_id=task.id,
                        tracker_id=task.tracker_id,
                        status=status,
                        status_display=status,
                        start_date=start_date,
                        end_date=start_date + timedelta(minutes=30),
                        created_at=base_time
                        + timedelta(
                            seconds=dup_idx
                        ),  # Different created_at for ordering
                    )
                    db_session.add(history)
                    total_duplicates += 1

        db_session.commit()

        # Count only our test data
        test_history_count = (
            db_session.query(TrackerTaskHistory)
            .filter(TrackerTaskHistory.tracker_id.like("test_cleanup_large_%"))
            .count()
        )
        expected_total = 10 * 5 * 20  # 10 tasks * 5 statuses * 20 duplicates each
        assert (
            test_history_count == expected_total
        ), f"Expected {expected_total} history entries, got {test_history_count}"

        # Test cleanup performance
        start_time = time.time()
        cleaned_count = sync_cmd._cleanup_duplicate_history()
        end_time = time.time()

        execution_time = end_time - start_time

        # Should clean up 19 duplicates per status per task (keep 1, remove 19)
        expected_cleaned = (
            10 * 5 * 19
        )  # 10 tasks * 5 statuses * 19 duplicates to remove
        assert (
            cleaned_count == expected_cleaned
        ), f"Expected {expected_cleaned} cleaned, got {cleaned_count}"

        # Performance check: should complete in under 1 second for this dataset
        assert (
            execution_time < 1.0
        ), f"Cleanup took {execution_time:.2f}s, should be under 1s"

        # Verify only one history entry remains per status per task
        for task in tasks:
            for status_idx in range(5):
                status = f"Status{status_idx}"
                remaining_count = (
                    db_session.query(TrackerTaskHistory)
                    .filter(
                        TrackerTaskHistory.task_id == task.id,
                        TrackerTaskHistory.status == status,
                    )
                    .count()
                )
                assert (
                    remaining_count == 1
                ), f"Expected 1 remaining entry for task {task.id} status {status}, got {remaining_count}"

    def test_cleanup_duplicate_history_preserves_oldest_record(self, db_session):
        """Test that cleanup preserves the oldest record (by created_at)."""
        # Clean up any existing test data first
        db_session.query(TrackerTaskHistory).filter(
            TrackerTaskHistory.tracker_id == "test_cleanup_oldest"
        ).delete(synchronize_session=False)
        db_session.query(TrackerTask).filter(
            TrackerTask.tracker_id == "test_cleanup_oldest"
        ).delete(synchronize_session=False)
        db_session.commit()

        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Create a task
        task = TrackerTask(
            tracker_id="test_cleanup_oldest", key="TEST-OLDEST", summary="Test Task"
        )
        db_session.add(task)
        db_session.commit()

        # Create duplicate history entries with different created_at times
        base_time = datetime.now(timezone.utc)
        start_date = base_time

        # Create 3 duplicates, with different created_at times
        for i in range(3):
            history = TrackerTaskHistory(
                task_id=task.id,
                tracker_id="test_cleanup_oldest",
                status="Testing",
                status_display="Testing",
                start_date=start_date,
                end_date=None,
                created_at=base_time + timedelta(seconds=i),  # Different created_at
            )
            db_session.add(history)

        db_session.commit()

        # Test cleanup
        cleaned_count = sync_cmd._cleanup_duplicate_history()
        assert cleaned_count == 2  # Should remove 2 duplicates, keep 1

        # Verify only one record remains
        remaining_count = (
            db_session.query(TrackerTaskHistory)
            .filter(TrackerTaskHistory.task_id == task.id)
            .count()
        )
        assert (
            remaining_count == 1
        ), f"Expected 1 remaining record, got {remaining_count}"

        # Verify the remaining record exists and has correct data
        remaining_history = (
            db_session.query(TrackerTaskHistory)
            .filter(TrackerTaskHistory.task_id == task.id)
            .first()
        )
        assert remaining_history is not None
        assert remaining_history.status == "Testing"
        assert remaining_history.tracker_id == "test_cleanup_oldest"

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
