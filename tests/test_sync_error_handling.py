"""Tests for sync error handling and API error statistics."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from radiator.commands.sync_tracker import TrackerSyncCommand
from radiator.models.tracker import TrackerSyncLog, TrackerTask, TrackerTaskHistory


class TestSyncErrorHandling:
    """Test error handling in sync operations."""

    def setup_method(self):
        """Clean up database before each test."""
        # This will be called before each test method
        pass

    def teardown_method(self):
        """Clean up database after each test."""
        # This will be called after each test method
        pass

    def test_api_errors_not_reflected_in_final_statistics(
        self, db_session, sample_task_data
    ):
        """Test that API errors are not reflected in final statistics output."""
        # Clean up database before test
        db_session.query(TrackerTaskHistory).delete()
        db_session.query(TrackerTask).delete()
        db_session.query(TrackerSyncLog).delete()
        db_session.commit()

        # Create sync command with real database session
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Mock tracker service to return mixed results (some tasks fail, some succeed)
        with patch("radiator.commands.sync_tracker.tracker_service") as mock_service:
            # Mock successful task search
            mock_service.get_tasks_by_filter_with_data.return_value = [
                {
                    "id": "test_sync_001",
                    "key": "TEST-SYNC-001",
                    "summary": "Test Task 1",
                    "status": {"key": "open", "display": "open"},
                    "createdBy": {"display": "user1"},
                    "assignee": {"display": "Test User"},
                    "businessClient": [{"display": "Test Client"}],
                    "63515d47fe387b7ce7b9fc55--team": "frontend",
                    "63515d47fe387b7ce7b9fc55--prodteam": "development",
                    "63515d47fe387b7ce7b9fc55--profitForecast": "high",
                    "updatedAt": "2024-01-01T00:00:00Z",
                    "createdAt": "2024-01-01T00:00:00Z",
                },
                {
                    "id": "test_sync_002",
                    "key": "TEST-SYNC-002",
                    "summary": "Test Task 2",
                    "status": {"key": "open", "display": "open"},
                    "createdBy": {"display": "user2"},
                    "assignee": {"display": "Test User 2"},
                    "businessClient": [{"display": "Test Client 2"}],
                    "63515d47fe387b7ce7b9fc55--team": "backend",
                    "63515d47fe387b7ce7b9fc55--prodteam": "development",
                    "63515d47fe387b7ce7b9fc55--profitForecast": "medium",
                    "updatedAt": "2024-01-01T00:00:00Z",
                    "createdAt": "2024-01-01T00:00:00Z",
                },
            ]

            # Mock extract_task_data to return valid data for both tasks
            def mock_extract_task_data(task_obj):
                return {
                    "tracker_id": task_obj["id"],
                    "key": task_obj["key"],
                    "summary": task_obj["summary"],
                    "description": "",
                    "status": task_obj["status"]["display"],
                    "author": task_obj["createdBy"]["display"],
                    "assignee": task_obj["assignee"]["display"],
                    "business_client": "Test Client",
                    "team": task_obj["63515d47fe387b7ce7b9fc55--team"],
                    "prodteam": task_obj["63515d47fe387b7ce7b9fc55--prodteam"],
                    "profit_forecast": task_obj[
                        "63515d47fe387b7ce7b9fc55--profitForecast"
                    ],
                    "task_updated_at": datetime.fromisoformat(
                        task_obj["updatedAt"].replace("Z", "+00:00")
                    ),
                }

            mock_service.extract_task_data.side_effect = mock_extract_task_data

            # Mock get_changelogs_batch to return mixed results (one task fails)
            def mock_get_changelogs_batch(task_ids):
                return [
                    ("test_sync_001", []),  # Success - empty changelog
                    ("test_sync_002", None),  # Failure - None indicates API error
                ]

            mock_service.get_changelogs_batch.side_effect = mock_get_changelogs_batch

            # Mock extract_status_history_with_initial_status to handle None
            def mock_extract_status_history(changelog, task_info, task_key):
                if changelog is None:
                    return []  # Simulate API error
                return []

            mock_service.extract_status_history_with_initial_status.side_effect = (
                mock_extract_status_history
            )

            # Capture stdout to check final statistics
            import io
            import sys
            from contextlib import redirect_stdout

            captured_output = io.StringIO()

            # Run sync with captured output
            with redirect_stdout(captured_output):
                result = sync_cmd.run(
                    filters={"query": "test"}, limit=2, skip_history=False
                )

            # Check that sync completed successfully
            assert result is True

            # Get captured output
            output = captured_output.getvalue()

            # Check that final statistics are printed
            assert "🎉 Синхронизация завершена успешно!" in output
            assert "📝 Создано:" in output
            assert "🔄 Обновлено:" in output
            assert "📚 Записей истории:" in output
            assert "📋 Задач с историей:" in output

            # PROBLEM: No information about API errors in statistics
            # TDD: Check that API errors ARE reflected in final statistics
            # This test should FAIL until we implement the feature
            assert "❌ Ошибок API: 1" in output  # Should be present after implementation

            # Verify that tasks were still created despite API errors
            created_tasks = db_session.query(TrackerTask).all()
            assert len(created_tasks) == 2  # Both tasks were created

            # Verify sync log was created
            sync_log = db_session.query(TrackerSyncLog).first()
            assert sync_log is not None
            assert sync_log.status == "completed"
            assert sync_log.tasks_processed == 2
            assert sync_log.tasks_created == 2
            assert sync_log.tasks_updated == 0

    def test_api_errors_not_counted_in_statistics(self, db_session, sample_task_data):
        """Test that API errors are not counted in final statistics - this is the problem."""
        # Clean up database before test
        db_session.query(TrackerTaskHistory).delete()
        db_session.query(TrackerTask).delete()
        db_session.query(TrackerSyncLog).delete()
        db_session.commit()

        # Create sync command with real database session
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Mock tracker service to return mixed results (some tasks fail, some succeed)
        with patch("radiator.commands.sync_tracker.tracker_service") as mock_service:
            # Mock successful task search
            mock_service.get_tasks_by_filter_with_data.return_value = [
                {
                    "id": "test_sync_001",
                    "key": "TEST-SYNC-001",
                    "summary": "Test Task 1",
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

            # Mock extract_task_data
            def mock_extract_task_data(task_obj):
                return {
                    "tracker_id": task_obj["id"],
                    "key": task_obj["key"],
                    "summary": task_obj["summary"],
                    "description": "",
                    "status": task_obj["status"]["display"],
                    "author": task_obj["createdBy"]["display"],
                    "assignee": task_obj["assignee"]["display"],
                    "business_client": "Test Client",
                    "team": task_obj["63515d47fe387b7ce7b9fc55--team"],
                    "prodteam": task_obj["63515d47fe387b7ce7b9fc55--prodteam"],
                    "profit_forecast": task_obj[
                        "63515d47fe387b7ce7b9fc55--profitForecast"
                    ],
                    "task_updated_at": datetime.fromisoformat(
                        task_obj["updatedAt"].replace("Z", "+00:00")
                    ),
                }

            mock_service.extract_task_data.side_effect = mock_extract_task_data

            # Mock get_changelogs_batch to return None for one task (API error)
            def mock_get_changelogs_batch(task_ids):
                return [("test_sync_001", None)]  # API error - None indicates failure

            mock_service.get_changelogs_batch.side_effect = mock_get_changelogs_batch

            # Mock extract_status_history_with_initial_status
            mock_service.extract_status_history_with_initial_status.return_value = []

            # Capture stdout to check final statistics
            import io
            from contextlib import redirect_stdout

            captured_output = io.StringIO()

            # Run sync with captured output
            with redirect_stdout(captured_output):
                result = sync_cmd.run(
                    filters={"query": "test"}, limit=1, skip_history=False
                )

            # Check that sync completed
            assert result is True

            # Get captured output
            output = captured_output.getvalue()

            # TDD: Check that API errors ARE reflected in final statistics
            # This test should FAIL until we implement the feature
            assert "❌ Ошибок API: 1" in output  # Should be present after implementation

            # TDD: Verify that sync log DOES track error count
            sync_log = db_session.query(TrackerSyncLog).first()
            assert sync_log is not None
            assert sync_log.status == "completed"
            # Should track error count after implementation
            assert hasattr(sync_log, "errors_count")
            assert sync_log.errors_count == 1  # Should be 1 after implementation
