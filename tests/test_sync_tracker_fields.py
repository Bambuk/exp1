"""Tests for sync_tracker with fields parameter usage."""

from unittest.mock import Mock, patch

import pytest

from radiator.commands.sync_tracker import TrackerSyncCommand
from radiator.utils.fields_loader import load_fields_list


class TestSyncTrackerFieldsUsage:
    """Test cases for sync_tracker using fields parameter."""

    def test_sync_tracker_loads_fields_from_file(self):
        """Test that sync_tracker loads fields from fields.txt file."""
        with patch(
            "radiator.commands.sync_tracker.load_fields_list"
        ) as mock_load_fields:
            mock_load_fields.return_value = ["id", "key", "summary", "customer"]

            sync_cmd = TrackerSyncCommand()

            # Verify that load_fields_list was called
            mock_load_fields.assert_called_once()

            # Verify that fields are stored in the command
            assert hasattr(sync_cmd, "fields")
            assert sync_cmd.fields == ["id", "key", "summary", "customer"]

    def test_sync_tracker_passes_fields_to_get_tasks_by_filter_with_data(
        self, db_session
    ):
        """Test that sync_tracker passes fields to get_tasks_by_filter_with_data."""
        with patch(
            "radiator.commands.sync_tracker.load_fields_list"
        ) as mock_load_fields:
            mock_load_fields.return_value = ["id", "key", "summary", "customer"]

            sync_cmd = TrackerSyncCommand()
            sync_cmd.db = db_session

            with patch(
                "radiator.commands.sync_tracker.tracker_service"
            ) as mock_service:
                mock_service.get_tasks_by_filter_with_data.return_value = []

                # Call get_tasks_to_sync
                sync_cmd.get_tasks_to_sync(filters={"query": "test"}, limit=10)

                # Verify that get_tasks_by_filter_with_data was called with fields
                mock_service.get_tasks_by_filter_with_data.assert_called_once()
                call_args = mock_service.get_tasks_by_filter_with_data.call_args

                # Check that fields parameter was passed
                assert call_args[1]["fields"] == ["id", "key", "summary", "customer"]
                assert call_args[0][0] == {
                    "query": "test"
                }  # filters as first positional arg
                assert call_args[1]["limit"] == 10

    def test_sync_tracker_handles_missing_fields_file(self, db_session):
        """Test that sync_tracker handles missing fields file gracefully."""
        with patch(
            "radiator.commands.sync_tracker.load_fields_list"
        ) as mock_load_fields:
            mock_load_fields.side_effect = FileNotFoundError("Fields file not found")

            # Should not raise exception during initialization
            sync_cmd = TrackerSyncCommand()
            sync_cmd.db = db_session

            # Fields should be None or empty list
            assert sync_cmd.fields is None or sync_cmd.fields == []

    def test_sync_tracker_uses_fields_in_full_sync_flow(self, db_session):
        """Test that sync_tracker uses fields in the full sync flow."""
        with patch(
            "radiator.commands.sync_tracker.load_fields_list"
        ) as mock_load_fields:
            mock_load_fields.return_value = ["id", "key", "summary", "customer"]

            sync_cmd = TrackerSyncCommand()
            sync_cmd.db = db_session

            with patch(
                "radiator.commands.sync_tracker.tracker_service"
            ) as mock_service:
                # Mock the full sync flow
                mock_service.get_tasks_by_filter_with_data.return_value = [
                    {
                        "id": "test_001",
                        "key": "TEST-001",
                        "summary": "Test Task",
                        "customer": "Test Customer",
                    }
                ]
                mock_service.extract_task_data.return_value = {
                    "tracker_id": "test_001",
                    "key": "TEST-001",
                    "summary": "Test Task",
                    "customer": "Test Customer",
                    "status": "Open",
                    "author": "Test Author",
                    "assignee": "Test Assignee",
                    "business_client": "Test Client",
                    "team": "frontend",
                    "prodteam": "development",
                    "profit_forecast": "high",
                    "task_updated_at": None,
                    "created_at": None,
                    "links": [],
                    "full_data": {
                        "id": "test_001",
                        "key": "TEST-001",
                        "summary": "Test Task",
                        "customer": "Test Customer",
                    },
                }
                mock_service.get_changelogs_batch.return_value = [("test_001", [])]
                mock_service.extract_status_history_with_initial_status.return_value = (
                    []
                )

                # Run sync
                result = sync_cmd.run(
                    filters={"query": "test"}, limit=1, skip_history=True
                )

                # Verify that get_tasks_by_filter_with_data was called with fields
                mock_service.get_tasks_by_filter_with_data.assert_called_once()
                call_args = mock_service.get_tasks_by_filter_with_data.call_args

                # Check that fields parameter was passed
                assert call_args[1]["fields"] == ["id", "key", "summary", "customer"]

                # Verify sync completed successfully
                assert result is True

    def test_sync_tracker_fields_parameter_integration_with_api_mock(self, db_session):
        """Test integration with API mock to verify fields are passed correctly."""
        with patch(
            "radiator.commands.sync_tracker.load_fields_list"
        ) as mock_load_fields:
            mock_load_fields.return_value = ["id", "key", "summary", "customer"]

            sync_cmd = TrackerSyncCommand()
            sync_cmd.db = db_session

            # Mock the API service to verify fields parameter
            with patch(
                "radiator.commands.sync_tracker.tracker_service"
            ) as mock_service:
                # Create a mock that tracks calls to search_tasks_with_data
                search_calls = []

                def track_search_calls(*args, **kwargs):
                    search_calls.append(kwargs)
                    return []

                mock_service.get_tasks_by_filter_with_data.side_effect = (
                    track_search_calls
                )

                # Call get_tasks_to_sync
                sync_cmd.get_tasks_to_sync(filters={"query": "test"}, limit=10)

                # Verify that the call was made
                assert len(search_calls) == 1
                call_kwargs = search_calls[0]

                # Check that fields parameter was passed
                assert call_kwargs["fields"] == ["id", "key", "summary", "customer"]
                # Note: filters is passed as positional argument, not keyword
                assert call_kwargs["limit"] == 10
