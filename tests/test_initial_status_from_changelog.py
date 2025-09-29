"""TDD tests for extracting initial status from changelog - these tests should FAIL until implementation."""

from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

from radiator.services.tracker_service import TrackerAPIService


class TestInitialStatusFromChangelog:
    """TDD tests that should FAIL until we implement proper initial status extraction from changelog."""

    @pytest.fixture
    def mock_service(self):
        """Create mock TrackerAPIService instance."""
        with patch("radiator.services.tracker_service.logger"):
            service = TrackerAPIService()
            return service

    def test_extract_status_history_should_use_from_field_for_initial_status(
        self, mock_service
    ):
        """🔴 RED: This test should FAIL - we need to use 'from' field to determine initial status."""
        # Given: Changelog with first status change that has 'from' field
        changelog = [
            {
                "id": 1,
                "updatedAt": "2024-01-01T10:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status", "display": "Status"},
                        "from": {"display": "Беклог"},  # ← ИСХОДНЫЙ статус
                        "to": {"display": "В работе"},  # ← НОВЫЙ статус
                    }
                ],
            }
        ]

        task_data = {
            "tracker_id": "12345",
            "key": "TEST-123",
            "status": "Готово",  # Текущий статус (не должен использоваться)
            "created_at": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        }

        # When: We extract status history
        result = mock_service.extract_status_history_with_initial_status(
            changelog, task_data, "TEST-123"
        )

        # Then: We should get TWO entries - initial status and first change
        assert len(result) == 2, f"Should have 2 status entries, got {len(result)}"

        # First entry should be the initial status from 'from' field
        initial_entry = result[0]
        assert (
            initial_entry["status"] == "Беклог"
        ), f"Initial status should be 'Беклог', got '{initial_entry['status']}'"
        assert initial_entry["status_display"] == "Беклог", "Should set status_display"
        assert (
            initial_entry["start_date"] == task_data["created_at"]
        ), "Should use created_at as start_date"
        assert initial_entry["end_date"] == datetime(
            2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc
        ), "Should end when first change starts"

        # Second entry should be the first change
        change_entry = result[1]
        assert (
            change_entry["status"] == "В работе"
        ), f"First change should be 'В работе', got '{change_entry['status']}'"
        assert change_entry["status_display"] == "В работе", "Should set status_display"
        assert change_entry["start_date"] == datetime(
            2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc
        ), "Should start when change occurred"
        assert change_entry["end_date"] is None, "Last status should have no end_date"

    def test_extract_status_history_should_handle_multiple_changes_correctly(
        self, mock_service
    ):
        """🔴 RED: This test should FAIL - we need to handle multiple status changes correctly."""
        # Given: Changelog with multiple status changes
        changelog = [
            {
                "id": 1,
                "updatedAt": "2024-01-01T10:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status", "display": "Status"},
                        "from": {"display": "Беклог"},
                        "to": {"display": "В работе"},
                    }
                ],
            },
            {
                "id": 2,
                "updatedAt": "2024-01-01T15:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status", "display": "Status"},
                        "from": {"display": "В работе"},
                        "to": {"display": "Готово"},
                    }
                ],
            },
        ]

        task_data = {
            "tracker_id": "67890",
            "key": "TEST-456",
            "status": "Готово",
            "created_at": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        }

        # When: We extract status history
        result = mock_service.extract_status_history_with_initial_status(
            changelog, task_data, "TEST-456"
        )

        # Then: We should get THREE entries
        assert len(result) == 3, f"Should have 3 status entries, got {len(result)}"

        # First entry: initial status
        assert result[0]["status"] == "Беклог"
        assert result[0]["start_date"] == task_data["created_at"]
        assert result[0]["end_date"] == datetime(
            2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc
        )

        # Second entry: first change
        assert result[1]["status"] == "В работе"
        assert result[1]["start_date"] == datetime(
            2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc
        )
        assert result[1]["end_date"] == datetime(
            2024, 1, 1, 15, 0, 0, tzinfo=timezone.utc
        )

        # Third entry: second change
        assert result[2]["status"] == "Готово"
        assert result[2]["start_date"] == datetime(
            2024, 1, 1, 15, 0, 0, tzinfo=timezone.utc
        )
        assert result[2]["end_date"] is None

    def test_extract_status_history_should_fallback_to_current_status_when_no_from_field(
        self, mock_service
    ):
        """🔴 RED: This test should FAIL - we need to handle cases where 'from' field is missing."""
        # Given: Changelog where first entry has no 'from' field
        changelog = [
            {
                "id": 1,
                "updatedAt": "2024-01-01T10:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status", "display": "Status"},
                        "from": None,  # ← НЕТ исходного статуса
                        "to": {"display": "В работе"},
                    }
                ],
            }
        ]

        task_data = {
            "tracker_id": "99999",
            "key": "TEST-999",
            "status": "Беклог",  # Текущий статус должен использоваться как fallback
            "created_at": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        }

        # When: We extract status history
        result = mock_service.extract_status_history_with_initial_status(
            changelog, task_data, "TEST-999"
        )

        # Then: We should get TWO entries - fallback initial status and change
        assert len(result) == 2, f"Should have 2 status entries, got {len(result)}"

        # First entry should use current status as fallback
        assert (
            result[0]["status"] == "Беклог"
        ), "Should use current status as fallback when 'from' is missing"
        assert result[0]["start_date"] == task_data["created_at"]
        assert result[0]["end_date"] == datetime(
            2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc
        )

        # Second entry should be the change
        assert result[1]["status"] == "В работе"
        assert result[1]["start_date"] == datetime(
            2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc
        )
        assert result[1]["end_date"] is None

    def test_extract_status_history_should_handle_empty_changelog_with_current_status(
        self, mock_service
    ):
        """🔴 RED: This test should FAIL - we need to handle empty changelog correctly."""
        # Given: Empty changelog
        changelog = []

        task_data = {
            "tracker_id": "11111",
            "key": "TEST-111",
            "status": "Беклог",
            "created_at": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        }

        # When: We extract status history
        result = mock_service.extract_status_history_with_initial_status(
            changelog, task_data, "TEST-111"
        )

        # Then: We should get ONE entry with current status
        assert len(result) == 1, f"Should have 1 status entry, got {len(result)}"

        assert (
            result[0]["status"] == "Беклог"
        ), "Should use current status when changelog is empty"
        assert result[0]["status_display"] == "Беклог"
        assert result[0]["start_date"] == task_data["created_at"]
        assert result[0]["end_date"] is None

    def test_extract_status_history_should_ignore_non_status_fields(self, mock_service):
        """🔴 RED: This test should FAIL - we need to ignore non-status field changes."""
        # Given: Changelog with status and non-status changes
        changelog = [
            {
                "id": 1,
                "updatedAt": "2024-01-01T10:00:00Z",
                "fields": [
                    {
                        "field": {
                            "id": "assignee",
                            "display": "Assignee",
                        },  # ← НЕ статус
                        "from": {"display": "User1"},
                        "to": {"display": "User2"},
                    }
                ],
            },
            {
                "id": 2,
                "updatedAt": "2024-01-01T15:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status", "display": "Status"},  # ← СТАТУС
                        "from": {"display": "Беклог"},
                        "to": {"display": "В работе"},
                    }
                ],
            },
        ]

        task_data = {
            "tracker_id": "22222",
            "key": "TEST-222",
            "status": "В работе",
            "created_at": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        }

        # When: We extract status history
        result = mock_service.extract_status_history_with_initial_status(
            changelog, task_data, "TEST-222"
        )

        # Then: We should get TWO entries (only status changes, ignore assignee)
        assert len(result) == 2, f"Should have 2 status entries, got {len(result)}"

        # Should only process status field changes
        assert result[0]["status"] == "Беклог"
        assert result[1]["status"] == "В работе"
