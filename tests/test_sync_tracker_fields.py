"""Tests for sync_tracker with fields parameter usage."""

from unittest.mock import Mock, patch

import pytest

from radiator.commands.sync_tracker import TrackerSyncCommand
from radiator.models.tracker import TrackerTask
from radiator.utils.fields_loader import load_fields_list

FULLSTACK_PRODTEAM_FIELD = "6361307d94f52e42ae308615--prodteam"
FULLSTACK_TEAM_FIELD = "6361307d94f52e42ae308615--team"


class TestSyncTrackerFieldsUsage:
    """Test cases for sync_tracker using fields parameter."""

    def test_default_fields_include_fullstack_prodteam_and_team(self):
        fields = load_fields_list()
        assert FULLSTACK_PRODTEAM_FIELD in fields
        assert FULLSTACK_TEAM_FIELD in fields

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

    def test_bulk_update_does_not_overwrite_prodteam_with_empty(self, db_session):
        cmd = TrackerSyncCommand(db=db_session)
        # seed existing task
        existing = TrackerTask(
            tracker_id="1",
            key="FS-1",
            prodteam="keep-me",
            summary="old",
        )
        db_session.add(existing)
        db_session.commit()

        # incoming data with empty prodteam
        cmd._bulk_create_or_update_tasks(
            [
                {
                    "tracker_id": "1",
                    "key": "FS-1",
                    "summary": "new",
                    "prodteam": "",
                }
            ]
        )

        refreshed = db_session.query(TrackerTask).filter_by(tracker_id="1").first()
        assert refreshed.prodteam == "keep-me"
        assert refreshed.summary == "new"

    def test_sync_run_saves_fullstack_prodteam_field(self, db_session):
        """E2E sync: prodteam из поля FULLSTACK попадает в БД."""
        cmd = TrackerSyncCommand(db=db_session)

        task_data = {
            "id": "777",
            "key": "FULLSTACK-777",
            "summary": "FS task",
            "createdAt": "2025-01-02T00:00:00Z",
            "updatedAt": "2025-01-03T00:00:00Z",
            "links": [],
            "status": {"display": "Open"},
            "createdBy": {"display": "author"},
            "assignee": {"display": "assignee"},
            "63515d47fe387b7ce7b9fc55--team": "team-legacy",
            "6361307d94f52e42ae308615--prodteam": "team-fullstack",
        }

        with patch(
            "radiator.commands.sync_tracker.tracker_service.get_tasks_by_filter_with_data",
            return_value=[task_data],
        ), patch(
            "radiator.commands.sync_tracker.tracker_service.get_changelogs_batch",
            return_value=[],
        ), patch(
            "radiator.commands.sync_tracker.tracker_service.extract_status_history_with_initial_status",
            return_value=[],
        ):
            result = cmd.run(
                filters={"query": "Queue: FULLSTACK"}, limit=1, skip_history=True
            )
            assert result is True

        saved = db_session.query(TrackerTask).filter_by(tracker_id="777").first()
        assert saved is not None
        assert saved.key == "FULLSTACK-777"
        assert saved.prodteam == "team-fullstack"

    def test_sync_run_saves_fullstack_team_field_in_full_data(self, db_session):
        """E2E sync: full_data сохраняет поле FULLSTACK team."""
        cmd = TrackerSyncCommand(db=db_session)

        task_data = {
            "id": "778",
            "key": "FULLSTACK-778",
            "summary": "FS task team",
            "createdAt": "2025-02-02T00:00:00Z",
            "updatedAt": "2025-02-03T00:00:00Z",
            "links": [],
            "status": {"display": "Open"},
            "createdBy": {"display": "author"},
            "assignee": {"display": "assignee"},
            FULLSTACK_TEAM_FIELD: "Team-Field",
        }

        with patch(
            "radiator.commands.sync_tracker.tracker_service.get_tasks_by_filter_with_data",
            return_value=[task_data],
        ), patch(
            "radiator.commands.sync_tracker.tracker_service.get_changelogs_batch",
            return_value=[],
        ), patch(
            "radiator.commands.sync_tracker.tracker_service.extract_status_history_with_initial_status",
            return_value=[],
        ):
            result = cmd.run(
                filters={"query": "Queue: FULLSTACK"}, limit=1, skip_history=True
            )
            assert result is True

        saved = db_session.query(TrackerTask).filter_by(tracker_id="778").first()
        assert saved is not None
        assert saved.full_data.get(FULLSTACK_TEAM_FIELD) == "Team-Field"
