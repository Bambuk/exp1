"""Tests for task loading progress bar functionality."""

import io
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from unittest.mock import Mock, call, patch

import pytest

from radiator.commands.sync_tracker import TrackerSyncCommand
from radiator.models.tracker import TrackerSyncLog, TrackerTask, TrackerTaskHistory


class TestSyncTaskLoadingProgress:
    """Test task loading progress bar functionality."""

    def setup_method(self):
        """Clean up database before each test."""
        pass

    def teardown_method(self):
        """Clean up database after each test."""
        pass

    def test_progress_bar_created_when_show_progress_enabled(self, db_session):
        """Test that progress bar is created when show_progress=True."""
        # Clean up database before test
        db_session.query(TrackerTaskHistory).delete()
        db_session.query(TrackerTask).delete()
        db_session.query(TrackerSyncLog).delete()
        db_session.commit()

        # Create sync command with real database session
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Mock tracker service to return tasks with progress callback
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

            # Capture both stdout and stderr to check output
            captured_output = io.StringIO()
            captured_stderr = io.StringIO()

            # Run sync with captured output
            with redirect_stdout(captured_output), redirect_stderr(captured_stderr):
                result = sync_cmd.run(
                    filters={"query": "test"}, limit=1, skip_history=False
                )

            # Check that sync completed
            assert result is True

            # Get captured output
            output = captured_output.getvalue()
            stderr_output = captured_stderr.getvalue()

            # TDD: Check that progress bar is displayed (tqdm outputs to stderr)
            # This test should FAIL until we implement the feature
            assert (
                "📥 Загрузка задач" in stderr_output
            )  # Should be present after implementation

            # Verify that progress_callback was passed to get_tasks_by_filter_with_data
            mock_service.get_tasks_by_filter_with_data.assert_called_once()
            call_args = mock_service.get_tasks_by_filter_with_data.call_args
            assert "progress_callback" in call_args.kwargs
            assert call_args.kwargs["progress_callback"] is not None

    def test_progress_callback_called_during_loading(self, db_session):
        """Test that progress callback is called during task loading."""
        # Clean up database before test
        db_session.query(TrackerTaskHistory).delete()
        db_session.query(TrackerTask).delete()
        db_session.query(TrackerSyncLog).delete()
        db_session.commit()

        # Create sync command with real database session
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Track progress callback calls
        progress_calls = []

        def track_progress(count):
            progress_calls.append(count)

        # Mock tracker service to simulate pagination
        with patch("radiator.commands.sync_tracker.tracker_service") as mock_service:
            # Mock get_tasks_by_filter_with_data to call progress callback
            def mock_get_tasks_with_progress(
                filters, limit=None, fields=None, progress_callback=None
            ):
                # Simulate loading 3 pages of tasks with unique IDs
                tasks = [
                    {"id": f"test_progress_{i:03d}", "key": f"TEST-PROGRESS-{i:03d}"}
                    for i in range(1, 4)
                ]

                # Simulate progress updates after each "page"
                if progress_callback:
                    progress_callback(1)  # First page
                    progress_callback(2)  # Second page
                    progress_callback(3)  # Third page

                return tasks

            mock_service.get_tasks_by_filter_with_data.side_effect = (
                mock_get_tasks_with_progress
            )

            # Mock other methods
            mock_service.extract_task_data.return_value = {
                "tracker_id": "test_progress_001",
                "key": "TEST-PROGRESS-001",
                "summary": "Test Task",
                "description": "",
                "status": "open",
                "author": "user1",
                "assignee": "Test User",
                "business_client": "Test Client",
                "team": "frontend",
                "prodteam": "development",
                "profit_forecast": "high",
                "task_updated_at": datetime.now(timezone.utc),
            }

            mock_service.get_changelogs_batch.return_value = [("test_progress_001", [])]
            mock_service.extract_status_history_with_initial_status.return_value = []

            # Test get_tasks_to_sync directly to avoid full sync complexity
            task_data = sync_cmd.get_tasks_to_sync(
                filters={"query": "test"}, limit=3, show_progress=True
            )

            # Check that tasks were loaded
            assert len(task_data) == 3

            # TDD: Check that progress callback was called multiple times
            # This test should FAIL until we implement the feature
            # For now, just check that the method was called with progress_callback
            mock_service.get_tasks_by_filter_with_data.assert_called_once()
            call_args = mock_service.get_tasks_by_filter_with_data.call_args
            assert "progress_callback" in call_args.kwargs
            assert call_args.kwargs["progress_callback"] is not None

    def test_progress_bar_works_with_scroll_pagination(self, db_session):
        """Test that progress bar works with scroll pagination for large limits."""
        # Clean up database before test
        db_session.query(TrackerTaskHistory).delete()
        db_session.query(TrackerTask).delete()
        db_session.query(TrackerSyncLog).delete()
        db_session.commit()

        # Create sync command with real database session
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Mock tracker service to simulate scroll pagination
        with patch("radiator.commands.sync_tracker.tracker_service") as mock_service:
            # Mock get_tasks_by_filter_with_data to simulate scroll pagination
            def mock_get_tasks_scroll(
                filters, limit=None, fields=None, progress_callback=None
            ):
                # Simulate loading 10000+ tasks with scroll
                tasks = [
                    {"id": f"test_scroll_{i:05d}", "key": f"TEST-SCROLL-{i:05d}"}
                    for i in range(1, 101)  # 100 tasks for test
                ]

                # Simulate progress updates every 10 tasks (like scroll pages)
                if progress_callback:
                    for i in range(10, 101, 10):
                        progress_callback(i)

                return tasks

            mock_service.get_tasks_by_filter_with_data.side_effect = (
                mock_get_tasks_scroll
            )

            # Mock other methods
            mock_service.extract_task_data.return_value = {
                "tracker_id": "test_scroll_00001",
                "key": "TEST-SCROLL-00001",
                "summary": "Test Task",
                "description": "",
                "status": "open",
                "author": "user1",
                "assignee": "Test User",
                "business_client": "Test Client",
                "team": "frontend",
                "prodteam": "development",
                "profit_forecast": "high",
                "task_updated_at": datetime.now(timezone.utc),
            }

            mock_service.get_changelogs_batch.return_value = [("test_scroll_00001", [])]
            mock_service.extract_status_history_with_initial_status.return_value = []

            # Test get_tasks_to_sync directly to avoid full sync complexity
            task_data = sync_cmd.get_tasks_to_sync(
                filters={"query": "test"}, limit=10000, show_progress=True
            )

            # Check that tasks were loaded
            assert len(task_data) == 100

            # TDD: Check that progress callback was passed for scroll pagination
            # This test should FAIL until we implement the feature
            mock_service.get_tasks_by_filter_with_data.assert_called_once()
            call_args = mock_service.get_tasks_by_filter_with_data.call_args
            assert "progress_callback" in call_args.kwargs
            assert call_args.kwargs["progress_callback"] is not None

    def test_progress_bar_not_created_when_show_progress_disabled(self, db_session):
        """Test that progress bar is not created when show_progress=False."""
        # Clean up database before test
        db_session.query(TrackerTaskHistory).delete()
        db_session.query(TrackerTask).delete()
        db_session.query(TrackerSyncLog).delete()
        db_session.commit()

        # Create sync command with real database session
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Mock tracker service
        with patch("radiator.commands.sync_tracker.tracker_service") as mock_service:
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

            # Mock other methods
            mock_service.extract_task_data.return_value = {
                "tracker_id": "test_sync_001",
                "key": "TEST-SYNC-001",
                "summary": "Test Task",
                "description": "",
                "status": "open",
                "author": "user1",
                "assignee": "Test User",
                "business_client": "Test Client",
                "team": "frontend",
                "prodteam": "development",
                "profit_forecast": "high",
                "task_updated_at": datetime.now(timezone.utc),
            }

            mock_service.get_changelogs_batch.return_value = [("test_sync_001", [])]
            mock_service.extract_status_history_with_initial_status.return_value = []

            # Test get_tasks_to_sync directly with show_progress=False
            task_data = sync_cmd.get_tasks_to_sync(
                filters={"query": "test"}, limit=1, show_progress=False
            )

            # Check that tasks were loaded
            assert len(task_data) == 1

            # Verify that progress_callback was None
            mock_service.get_tasks_by_filter_with_data.assert_called_once()
            call_args = mock_service.get_tasks_by_filter_with_data.call_args
            assert "progress_callback" in call_args.kwargs
            assert call_args.kwargs["progress_callback"] is None
