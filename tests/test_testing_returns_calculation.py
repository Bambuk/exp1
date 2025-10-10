"""Tests for testing returns calculation logic."""

from datetime import datetime

import pytest

from radiator.commands.models.time_to_market_models import StatusHistoryEntry
from radiator.commands.services.testing_returns_service import TestingReturnsService


class TestTestingReturnsCalculation:
    """Test cases for testing returns calculation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = TestingReturnsService()

    def test_count_single_testing_entry_no_returns(self):
        """Test: task enters Testing once -> 0 returns."""
        history = [
            StatusHistoryEntry(
                status="Open",
                status_display="Open",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 2),
            ),
            StatusHistoryEntry(
                status="Testing",
                status_display="Testing",
                start_date=datetime(2024, 1, 2),
                end_date=None,
            ),
        ]

        returns = self.service.count_status_returns(history, "Testing")
        assert returns == 0

    def test_count_multiple_testing_entries(self):
        """Test: task enters Testing 3 times -> 2 returns."""
        history = [
            StatusHistoryEntry(
                status="Open",
                status_display="Open",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 2),
            ),
            StatusHistoryEntry(
                status="Testing",
                status_display="Testing",
                start_date=datetime(2024, 1, 2),
                end_date=datetime(2024, 1, 3),
            ),
            StatusHistoryEntry(
                status="In Progress",
                status_display="In Progress",
                start_date=datetime(2024, 1, 3),
                end_date=datetime(2024, 1, 4),
            ),
            StatusHistoryEntry(
                status="Testing",
                status_display="Testing",
                start_date=datetime(2024, 1, 4),
                end_date=datetime(2024, 1, 5),
            ),
            StatusHistoryEntry(
                status="In Progress",
                status_display="In Progress",
                start_date=datetime(2024, 1, 5),
                end_date=datetime(2024, 1, 6),
            ),
            StatusHistoryEntry(
                status="Testing",
                status_display="Testing",
                start_date=datetime(2024, 1, 6),
                end_date=None,
            ),
        ]

        returns = self.service.count_status_returns(history, "Testing")
        assert returns == 2

    def test_count_external_test_returns(self):
        """Test: task enters Внешний тест 2 times -> 1 return."""
        history = [
            StatusHistoryEntry(
                status="Open",
                status_display="Open",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 2),
            ),
            StatusHistoryEntry(
                status="Внешний тест",
                status_display="Внешний тест",
                start_date=datetime(2024, 1, 2),
                end_date=datetime(2024, 1, 3),
            ),
            StatusHistoryEntry(
                status="In Progress",
                status_display="In Progress",
                start_date=datetime(2024, 1, 3),
                end_date=datetime(2024, 1, 4),
            ),
            StatusHistoryEntry(
                status="Внешний тест",
                status_display="Внешний тест",
                start_date=datetime(2024, 1, 4),
                end_date=None,
            ),
        ]

        returns = self.service.count_status_returns(history, "Внешний тест")
        assert returns == 1

    def test_count_both_statuses(self):
        """Test: task enters both Testing and Внешний тест multiple times."""
        history = [
            StatusHistoryEntry(
                status="Open",
                status_display="Open",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 2),
            ),
            StatusHistoryEntry(
                status="Testing",
                status_display="Testing",
                start_date=datetime(2024, 1, 2),
                end_date=datetime(2024, 1, 3),
            ),
            StatusHistoryEntry(
                status="Внешний тест",
                status_display="Внешний тест",
                start_date=datetime(2024, 1, 3),
                end_date=datetime(2024, 1, 4),
            ),
            StatusHistoryEntry(
                status="Testing",
                status_display="Testing",
                start_date=datetime(2024, 1, 4),
                end_date=datetime(2024, 1, 5),
            ),
            StatusHistoryEntry(
                status="Внешний тест",
                status_display="Внешний тест",
                start_date=datetime(2024, 1, 5),
                end_date=None,
            ),
        ]

        testing_returns = self.service.count_status_returns(history, "Testing")
        external_returns = self.service.count_status_returns(history, "Внешний тест")

        assert testing_returns == 1  # 2 entries - 1 = 1 return
        assert external_returns == 1  # 2 entries - 1 = 1 return

    def test_empty_history(self):
        """Test: empty history -> 0 returns."""
        history = []

        returns = self.service.count_status_returns(history, "Testing")
        assert returns == 0

    def test_no_testing_statuses(self):
        """Test: no Testing status in history -> 0 returns."""
        history = [
            StatusHistoryEntry(
                status="Open",
                status_display="Open",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 2),
            ),
            StatusHistoryEntry(
                status="In Progress",
                status_display="In Progress",
                start_date=datetime(2024, 1, 2),
                end_date=datetime(2024, 1, 3),
            ),
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2024, 1, 3),
                end_date=None,
            ),
        ]

        returns = self.service.count_status_returns(history, "Testing")
        assert returns == 0

    def test_consecutive_duplicate_statuses(self):
        """Test: consecutive duplicate statuses are counted as one entry."""
        history = [
            StatusHistoryEntry(
                status="Open",
                status_display="Open",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 2),
            ),
            StatusHistoryEntry(
                status="Testing",
                status_display="Testing",
                start_date=datetime(2024, 1, 2),
                end_date=datetime(2024, 1, 3),
            ),
            StatusHistoryEntry(
                status="Testing",
                status_display="Testing",
                start_date=datetime(2024, 1, 3),
                end_date=datetime(2024, 1, 4),
            ),
            StatusHistoryEntry(
                status="Testing",
                status_display="Testing",
                start_date=datetime(2024, 1, 4),
                end_date=datetime(2024, 1, 5),
            ),
            StatusHistoryEntry(
                status="In Progress",
                status_display="In Progress",
                start_date=datetime(2024, 1, 5),
                end_date=None,
            ),
        ]

        returns = self.service.count_status_returns(history, "Testing")
        assert returns == 0  # Only one entry (consecutive duplicates), so 0 returns

    def test_unsorted_history(self):
        """Test: history not sorted by date is handled correctly."""
        history = [
            StatusHistoryEntry(
                status="Testing",
                status_display="Testing",
                start_date=datetime(2024, 1, 3),
                end_date=datetime(2024, 1, 4),
            ),
            StatusHistoryEntry(
                status="Open",
                status_display="Open",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 2),
            ),
            StatusHistoryEntry(
                status="In Progress",
                status_display="In Progress",
                start_date=datetime(2024, 1, 4),
                end_date=datetime(2024, 1, 5),
            ),
            StatusHistoryEntry(
                status="Testing",
                status_display="Testing",
                start_date=datetime(2024, 1, 5),
                end_date=None,
            ),
        ]

        returns = self.service.count_status_returns(history, "Testing")
        assert returns == 1  # 2 entries - 1 = 1 return

    def test_none_history(self):
        """Test: None history -> 0 returns."""
        returns = self.service.count_status_returns(None, "Testing")
        assert returns == 0

    def test_status_case_sensitivity(self):
        """Test: status matching is case sensitive."""
        history = [
            StatusHistoryEntry(
                status="Testing",  # uppercase
                status_display="Testing",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 2),
            ),
            StatusHistoryEntry(
                status="In Progress",  # different status
                status_display="In Progress",
                start_date=datetime(2024, 1, 2),
                end_date=datetime(2024, 1, 3),
            ),
            StatusHistoryEntry(
                status="Testing",  # uppercase again
                status_display="Testing",
                start_date=datetime(2024, 1, 3),
                end_date=None,
            ),
        ]

        # Should find 2 separate entries
        returns = self.service.count_status_returns(history, "Testing")
        assert returns == 1  # 2 entries - 1 = 1 return

        # Test case sensitivity with lowercase
        history_lower = [
            StatusHistoryEntry(
                status="testing",  # lowercase
                status_display="Testing",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 2),
            ),
            StatusHistoryEntry(
                status="In Progress",  # different status
                status_display="In Progress",
                start_date=datetime(2024, 1, 2),
                end_date=datetime(2024, 1, 3),
            ),
            StatusHistoryEntry(
                status="testing",  # lowercase again
                status_display="Testing",
                start_date=datetime(2024, 1, 3),
                end_date=None,
            ),
        ]

        returns_lower = self.service.count_status_returns(history_lower, "testing")
        assert returns_lower == 1  # 2 entries - 1 = 1 return
