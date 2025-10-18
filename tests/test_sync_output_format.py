"""Tests for sync output format - API errors display and task loading indicator."""

import io
from contextlib import redirect_stdout
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from radiator.commands.sync_tracker import TrackerSyncCommand
from radiator.models.tracker import TrackerSyncLog, TrackerTask, TrackerTaskHistory


class TestSyncOutputFormat:
    """Test output format improvements in sync operations."""

    def setup_method(self):
        """Clean up database before each test."""
        pass

    def teardown_method(self):
        """Clean up database after each test."""
        pass

    def test_api_errors_always_displayed_when_zero(self, db_session):
        """Test that API errors are always displayed, even when zero."""
        # Clean up database before test
        db_session.query(TrackerTaskHistory).delete()
        db_session.query(TrackerTask).delete()
        db_session.query(TrackerSyncLog).delete()
        db_session.commit()

        # Create sync command with real database session
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Mock tracker service to return successful results (no errors)
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

            # Mock get_changelogs_batch to return successful results
            def mock_get_changelogs_batch(task_ids):
                return [("test_sync_001", [])]  # Success - empty changelog

            mock_service.get_changelogs_batch.side_effect = mock_get_changelogs_batch

            # Mock extract_status_history_with_initial_status
            mock_service.extract_status_history_with_initial_status.return_value = []

            # Capture stdout to check final statistics
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

            # TDD: Check that API errors are ALWAYS displayed (even when 0)
            # This test should FAIL until we implement the feature
            assert "✅ Ошибок API: 0" in output  # Should be present after implementation

            # Verify sync log tracks error count
            sync_log = db_session.query(TrackerSyncLog).first()
            assert sync_log is not None
            assert sync_log.status == "completed"
            assert sync_log.errors_count == 0

    def test_api_errors_displayed_when_present(self, db_session):
        """Test that API errors are displayed with correct format when present."""
        # Clean up database before test
        db_session.query(TrackerTaskHistory).delete()
        db_session.query(TrackerTask).delete()
        db_session.query(TrackerSyncLog).delete()
        db_session.commit()

        # Create sync command with real database session
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Mock tracker service to return mixed results (some tasks fail)
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

            # Mock get_changelogs_batch to return API error
            def mock_get_changelogs_batch(task_ids):
                return [("test_sync_001", None)]  # API error - None indicates failure

            mock_service.get_changelogs_batch.side_effect = mock_get_changelogs_batch

            # Mock extract_status_history_with_initial_status
            mock_service.extract_status_history_with_initial_status.return_value = []

            # Capture stdout to check final statistics
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

            # TDD: Check that API errors are displayed with correct format
            # This test should FAIL until we implement the feature
            assert "❌ Ошибок API: 1" in output  # Should be present after implementation

            # Verify sync log tracks error count
            sync_log = db_session.query(TrackerSyncLog).first()
            assert sync_log is not None
            assert sync_log.status == "completed"
            assert sync_log.errors_count == 1

    def test_task_loading_indicator_displayed(self, db_session):
        """Test that task loading indicator is displayed before first stage."""
        # Clean up database before test
        db_session.query(TrackerTaskHistory).delete()
        db_session.query(TrackerTask).delete()
        db_session.query(TrackerSyncLog).delete()
        db_session.commit()

        # Create sync command with real database session
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Mock tracker service to return successful results
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

            # Mock get_changelogs_batch to return successful results
            def mock_get_changelogs_batch(task_ids):
                return [("test_sync_001", [])]  # Success - empty changelog

            mock_service.get_changelogs_batch.side_effect = mock_get_changelogs_batch

            # Mock extract_status_history_with_initial_status
            mock_service.extract_status_history_with_initial_status.return_value = []

            # Capture stdout to check output
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

            # TDD: Check that task loading indicator is displayed
            # This test should FAIL until we implement the feature
            assert (
                "📥 Загрузка задач из Tracker..." in output
            )  # Should be present after implementation
            assert (
                "✅ Загружено 1 задач" in output
            )  # Should be present after implementation
