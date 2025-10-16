"""Tests for optimized sync that uses search data directly."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from radiator.commands.sync_tracker import TrackerSyncCommand
from radiator.models.tracker import TrackerSyncLog, TrackerTask, TrackerTaskHistory


class TestOptimizedSync:
    """Test optimized sync that uses search data directly."""

    def test_sync_uses_search_data_directly(self, db_session):
        """Test that sync uses search data directly without get_tasks_batch."""
        # Create sync command with real database session
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Mock search data with full task information
        search_task_data = {
            "id": "test_optimized_001",
            "key": "TEST-OPT-001",
            "summary": "Test Optimized Task",
            "description": "Test Description",
            "status": {"key": "open", "display": "Open"},
            "createdBy": {"display": "Test Author"},
            "assignee": {"display": "Test Assignee"},
            "businessClient": [{"display": "Test Client"}],
            "63515d47fe387b7ce7b9fc55--team": "frontend",
            "63515d47fe387b7ce7b9fc55--prodteam": "development",
            "63515d47fe387b7ce7b9fc55--profitForecast": "high",
            "updatedAt": "2024-01-01T00:00:00Z",
            "createdAt": "2024-01-01T00:00:00Z",
        }

        # Mock tracker service
        with patch("radiator.commands.sync_tracker.tracker_service") as mock_service:
            # Mock search to return full task data instead of just IDs
            mock_service.get_tasks_by_filter_with_data.return_value = [search_task_data]

            # Mock extract_task_data to process the search data
            mock_service.extract_task_data.return_value = {
                "tracker_id": "test_optimized_001",
                "key": "TEST-OPT-001",
                "summary": "Test Optimized Task",
                "description": "Test Description",
                "status": "Open",
                "author": "Test Author",
                "assignee": "Test Assignee",
                "business_client": "Test Client",
                "team": "frontend",
                "prodteam": "development",
                "profit_forecast": "high",
                "task_updated_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
            }

            # Mock history (not needed for this test)
            mock_service.get_changelogs_batch.return_value = [
                ("test_optimized_001", [])
            ]
            mock_service.extract_status_history_with_initial_status.return_value = []

            # Run sync
            result = sync_cmd.run(filters={"query": "test"}, limit=1, skip_history=True)

            # Verify result
            assert result is True

            # Verify that get_tasks_batch was NOT called
            mock_service.get_tasks_batch.assert_not_called()

            # Verify that get_tasks_by_filter_with_data was called
            mock_service.get_tasks_by_filter_with_data.assert_called_once()

            # Verify that extract_task_data was called with search data
            mock_service.extract_task_data.assert_called_once_with(search_task_data)

            # Verify task was saved to database
            saved_task = (
                db_session.query(TrackerTask)
                .filter(TrackerTask.tracker_id == "test_optimized_001")
                .first()
            )
            assert saved_task is not None
            assert saved_task.key == "TEST-OPT-001"
            assert saved_task.summary == "Test Optimized Task"
            assert saved_task.team == "frontend"
            assert saved_task.prodteam == "development"
            assert saved_task.profit_forecast == "high"

    def test_sync_with_multiple_tasks_from_search(self, db_session):
        """Test sync with multiple tasks returned from search."""
        # Clear existing data
        db_session.query(TrackerTask).delete()
        db_session.commit()

        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Mock multiple search results
        search_tasks_data = [
            {
                "id": "test_opt_001",
                "key": "TEST-OPT-001",
                "summary": "Task 1",
                "status": {"display": "Open"},
                "createdBy": {"display": "Author 1"},
                "assignee": {"display": "Assignee 1"},
                "63515d47fe387b7ce7b9fc55--team": "team1",
                "updatedAt": "2024-01-01T00:00:00Z",
                "createdAt": "2024-01-01T00:00:00Z",
            },
            {
                "id": "test_opt_002",
                "key": "TEST-OPT-002",
                "summary": "Task 2",
                "status": {"display": "Closed"},
                "createdBy": {"display": "Author 2"},
                "assignee": {"display": "Assignee 2"},
                "63515d47fe387b7ce7b9fc55--team": "team2",
                "updatedAt": "2024-01-02T00:00:00Z",
                "createdAt": "2024-01-02T00:00:00Z",
            },
        ]

        with patch("radiator.commands.sync_tracker.tracker_service") as mock_service:
            mock_service.get_tasks_by_filter_with_data.return_value = search_tasks_data

            # Mock extract_task_data for each task
            def mock_extract_task_data(task_data):
                return {
                    "tracker_id": task_data["id"],
                    "key": task_data["key"],
                    "summary": task_data["summary"],
                    "status": task_data["status"]["display"],
                    "author": task_data["createdBy"]["display"],
                    "assignee": task_data["assignee"]["display"],
                    "team": task_data.get("63515d47fe387b7ce7b9fc55--team", ""),
                    "task_updated_at": datetime(
                        2024, 1, int(task_data["id"][-1]), tzinfo=timezone.utc
                    ),
                    "created_at": datetime(
                        2024, 1, int(task_data["id"][-1]), tzinfo=timezone.utc
                    ),
                }

            mock_service.extract_task_data.side_effect = mock_extract_task_data
            mock_service.get_changelogs_batch.return_value = []
            mock_service.extract_status_history_with_initial_status.return_value = []

            # Run sync
            result = sync_cmd.run(filters={"query": "test"}, limit=2, skip_history=True)

            # Verify result
            assert result is True

            # Verify get_tasks_batch was NOT called
            mock_service.get_tasks_batch.assert_not_called()

            # Verify extract_task_data was called for each task
            assert mock_service.extract_task_data.call_count == 2

            # Verify both tasks were saved
            saved_tasks = db_session.query(TrackerTask).all()
            assert len(saved_tasks) == 2

            task_ids = [task.tracker_id for task in saved_tasks]
            assert "test_opt_001" in task_ids
            assert "test_opt_002" in task_ids

    def test_sync_backwards_compatibility(self, db_session):
        """Test that sync still works with old-style ID-only search results."""
        # Clear existing data
        db_session.query(TrackerTask).delete()
        db_session.commit()

        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Mock old-style search (returns only IDs)
        task_ids = ["test_legacy_001", "test_legacy_002"]

        # Mock get_tasks_batch for backwards compatibility
        mock_tasks_batch_data = [
            ("test_legacy_001", {"id": "test_legacy_001", "key": "LEGACY-001"}),
            ("test_legacy_002", {"id": "test_legacy_002", "key": "LEGACY-002"}),
        ]

        with patch("radiator.commands.sync_tracker.tracker_service") as mock_service:
            mock_service.get_tasks_by_filter_with_data.return_value = task_ids
            mock_service.get_tasks_batch.return_value = mock_tasks_batch_data

            def mock_extract_task_data(task_data):
                return {
                    "tracker_id": task_data["id"],
                    "key": task_data["key"],
                    "summary": f"Task {task_data['key']}",
                    "status": "Open",
                    "author": "Test Author",
                    "assignee": "Test Assignee",
                    "team": "test_team",
                    "task_updated_at": datetime.now(timezone.utc),
                    "created_at": datetime.now(timezone.utc),
                }

            mock_service.extract_task_data.side_effect = mock_extract_task_data
            mock_service.get_changelogs_batch.return_value = []
            mock_service.extract_status_history_with_initial_status.return_value = []

            # Run sync
            result = sync_cmd.run(filters={"query": "test"}, limit=2, skip_history=True)

            # Verify result
            assert result is True

            # Verify get_tasks_batch WAS called for backwards compatibility
            mock_service.get_tasks_batch.assert_called_once_with(
                task_ids, expand=["links"]
            )

            # Verify tasks were saved
            saved_tasks = db_session.query(TrackerTask).all()
            assert len(saved_tasks) == 2
