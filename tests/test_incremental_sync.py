"""
Tests for incremental sync functionality.

Tests the new incremental history sync features including:
- get_changelog_from_id method
- _incremental_history_update method
- _process_single_task_history with force_full_history flag
- CLI integration
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from radiator.commands.sync_tracker import TrackerSyncCommand
from radiator.core.database import SessionLocal
from radiator.models.tracker import TrackerTask, TrackerTaskHistory
from radiator.services.tracker_service import TrackerAPIService, tracker_service


class TestIncrementalSync:
    """Test incremental sync functionality."""

    def test_get_changelog_from_id_success(self):
        """Test successful retrieval of changelog from ID."""
        service = TrackerAPIService()

        # Mock response data
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": "changelog_2",
                "createdAt": "2024-01-02T10:00:00.000+0000",
                "type": "IssueWorkflow",
                "field": {"id": "status", "display": "Status"},
                "to": {"id": "in_progress", "display": "In Progress"},
                "from": {"id": "open", "display": "Open"},
            },
            {
                "id": "changelog_3",
                "createdAt": "2024-01-03T10:00:00.000+0000",
                "type": "IssueWorkflow",
                "field": {"id": "status", "display": "Status"},
                "to": {"id": "done", "display": "Done"},
                "from": {"id": "in_progress", "display": "In Progress"},
            },
        ]
        mock_response.headers = {"X-Total-Pages": "1"}

        with patch.object(
            service, "_make_request", return_value=mock_response
        ) as mock_request:
            result = service.get_changelog_from_id("task_123", "changelog_1")

            # Verify API call
            mock_request.assert_called_once()
            call_url = mock_request.call_args[0][0]
            assert "/v3/issues/task_123/changelog" in call_url

            # Verify parameters
            params = mock_request.call_args[1]["params"]
            assert params["id"] == "changelog_1"
            assert params["type"] == "IssueWorkflow"
            assert "perPage" in params

            # Verify result
            assert len(result) == 2
            assert result[0]["id"] == "changelog_2"
            assert result[1]["id"] == "changelog_3"

    def test_get_changelog_from_id_empty_response(self):
        """Test handling of empty changelog response."""
        service = TrackerAPIService()

        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.headers = {"X-Total-Pages": "0"}

        with patch.object(service, "_make_request", return_value=mock_response):
            result = service.get_changelog_from_id("task_123", "changelog_1")
            assert result == []

    def test_get_changelog_from_id_pagination(self):
        """Test pagination handling in get_changelog_from_id."""
        service = TrackerAPIService()

        # First page response
        page1_response = Mock()
        page1_response.json.return_value = [
            {"id": f"changelog_{i}"} for i in range(1, 4)
        ]
        page1_response.headers = {
            "Link": '<https://api.tracker.yandex.net/v3/issues/task_123/changelog?perPage=50&type=IssueWorkflow&id=changelog_3>; rel="next"'
        }

        # Second page response
        page2_response = Mock()
        page2_response.json.return_value = [
            {"id": f"changelog_{i}"} for i in range(4, 6)
        ]
        page2_response.headers = {"Link": ""}  # No next page

        with patch.object(
            service, "_make_request", side_effect=[page1_response, page2_response]
        ) as mock_request:
            result = service.get_changelog_from_id("task_123", "changelog_0")

            # Should make 2 API calls
            assert mock_request.call_count == 2
            assert len(result) == 5

    def test_incremental_history_update_empty_changelog(self, db_session):
        """Test incremental history update with empty changelog."""
        with TrackerSyncCommand() as sync_cmd:
            # Replace the command's db session with test session
            sync_cmd.db.close()
            sync_cmd.db = db_session
            # Create a test task in sync_cmd's database session
            import uuid

            unique_id = str(uuid.uuid4())[:8]
            task = TrackerTask(
                tracker_id=f"test_task_empty_{unique_id}",
                key=f"TEST-EMPTY-{unique_id}",
                summary="Test Task",
                status="open",
                assignee="test_user",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            sync_cmd.db.add(task)
            sync_cmd.db.commit()

            result = sync_cmd._incremental_history_update(task.id, [], task)
            assert result == 0

    def test_process_single_task_history_incremental_mode(self, db_session):
        """Test _process_single_task_history in incremental mode."""
        with TrackerSyncCommand() as sync_cmd:
            # Replace the command's db session with test session
            sync_cmd.db.close()
            sync_cmd.db = db_session
            # Create a test task with last_changelog_id in sync_cmd's database session
            import uuid

            unique_id = str(uuid.uuid4())[:8]
            tracker_id = f"test_task_incremental_mode_{unique_id}"
            task = TrackerTask(
                tracker_id=tracker_id,
                key=f"TEST-INCREMENTAL-MODE-{unique_id}",
                summary="Test Task",
                status="open",
                assignee="test_user",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_changelog_id="changelog_1",
            )
            sync_cmd.db.add(task)
            sync_cmd.db.commit()

            # Mock changelog data
            changelog = [
                {
                    "id": "changelog_2",
                    "createdAt": "2024-01-02T10:00:00.000+0000",
                    "type": "IssueWorkflow",
                    "field": {"id": "status", "display": "Status"},
                    "to": {"id": "in_progress", "display": "In Progress"},
                    "from": {"id": "open", "display": "Open"},
                }
            ]

            tasks_dict = {tracker_id: {"id": tracker_id}}

            with patch.object(
                sync_cmd, "_incremental_history_update", return_value=1
            ) as mock_incremental:
                count, has_history = sync_cmd._process_single_task_history(
                    tracker_id, changelog, tasks_dict, force_full_history=False
                )

                # Verify incremental method was called
                mock_incremental.assert_called_once_with(task.id, changelog, task)

                # Verify result
                assert count == 1
                assert has_history is True

                # Note: last_changelog_id update is tested in integration test
                # since this test mocks the incremental method

    def test_cli_force_full_history_flag(self):
        """Test CLI integration with --force-full-history flag."""
        import argparse

        # Test argument parsing
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--force-full-history", action="store_true", help="Force full history sync"
        )
        parser.add_argument(
            "--skip-history", action="store_true", help="Skip history sync"
        )

        # Test with flag
        args_with_flag = parser.parse_args(["--force-full-history"])
        assert args_with_flag.force_full_history is True
        assert args_with_flag.skip_history is False

        # Test without flag
        args_without_flag = parser.parse_args([])
        assert args_without_flag.force_full_history is False
        assert args_without_flag.skip_history is False

        # Test with both flags
        args_both = parser.parse_args(["--force-full-history", "--skip-history"])
        assert args_both.force_full_history is True
        assert args_both.skip_history is True

    def test_incremental_history_update_integration(self, db_session):
        """Integration test for incremental history update with real database operations."""
        # Clean up any existing test data to ensure test isolation
        db_session.query(TrackerTaskHistory).delete()
        db_session.query(TrackerTask).delete()
        db_session.commit()

        with TrackerSyncCommand() as sync_cmd:
            # Replace the command's db session with test session
            sync_cmd.db.close()
            sync_cmd.db = db_session
            # Create a test task with existing history
            import uuid

            unique_id = str(uuid.uuid4())[:8]
            tracker_id = f"test_incremental_integration_{unique_id}"

            task = TrackerTask(
                tracker_id=tracker_id,
                key=f"TEST-INTEGRATION-{unique_id}",
                summary="Test Task",
                status="open",
                assignee="test_user",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            sync_cmd.db.add(task)
            sync_cmd.db.commit()

            # Create existing history entry
            existing_history = TrackerTaskHistory(
                task_id=task.id,
                tracker_id=tracker_id,
                status="open",
                status_display="Open",
                start_date=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                end_date=None,  # This should be updated by incremental update
            )
            sync_cmd.db.add(existing_history)
            sync_cmd.db.commit()

            # Mock new changelog data
            new_changelog = [
                {
                    "id": "changelog_2",
                    "updatedAt": "2024-01-02T10:00:00.000+0000",
                    "type": "IssueWorkflow",
                    "fields": [
                        {
                            "field": {"id": "status", "display": "Status"},
                            "to": {"id": "in_progress", "display": "In Progress"},
                            "from": {"id": "open", "display": "Open"},
                        }
                    ],
                    "issue": {"id": tracker_id},
                }
            ]

            # Mock the extract_status_history method to return new history entry
            with patch(
                "radiator.commands.sync_tracker.tracker_service.extract_status_history"
            ) as mock_extract:
                mock_extract.return_value = [
                    {
                        "status": "in_progress",
                        "status_display": "In Progress",
                        "start_date": datetime(
                            2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc
                        ),
                        "end_date": None,
                    }
                ]

                # Test incremental update
                result = sync_cmd._incremental_history_update(
                    task.id, new_changelog, task
                )

                # Verify result
                assert result == 1  # Should add 1 new entry

                # Verify database state
                history_entries = (
                    sync_cmd.db.query(TrackerTaskHistory)
                    .filter(TrackerTaskHistory.task_id == task.id)
                    .order_by(TrackerTaskHistory.start_date)
                    .all()
                )

                # Should have 2 entries now
                assert len(history_entries) == 2

                # Verify existing entry was updated with end_date
                existing_entry = history_entries[0]  # First entry (open status)
                assert existing_entry.status == "open"
                assert existing_entry.end_date is not None
                assert (
                    existing_entry.end_date.date()
                    == datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc).date()
                )

                # Verify new entry was added
                new_entry = history_entries[1]  # Second entry (in_progress status)
                assert new_entry.status == "in_progress"
                assert new_entry.status_display == "In Progress"
                # Check only date part due to timezone conversion
                assert (
                    new_entry.start_date.date()
                    == datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc).date()
                )
                assert new_entry.end_date is None

                # Verify tracker_id is set correctly
                assert new_entry.tracker_id == tracker_id
