"""Tests for HistoryFilter - filters task history by as-of-date.

Following TDD approach: tests first, then implementation.
"""

from datetime import datetime, timedelta, timezone

import pytest

from radiator.commands.models.time_to_market_models import StatusHistoryEntry
from radiator.commands.services.history_filter import HistoryFilter


class TestHistoryFilter:
    """Test cases for HistoryFilter."""

    def test_filter_history_drops_entries_after_as_of_date(self):
        """Test that entries starting after as-of-date are dropped."""
        as_of_date = datetime(2025, 2, 10, tzinfo=timezone.utc)

        history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 2, 1, tzinfo=timezone.utc),
                end_date=datetime(2025, 2, 5, tzinfo=timezone.utc),
            ),
            StatusHistoryEntry(
                status="В работе",
                status_display="В работе",
                start_date=datetime(2025, 2, 5, tzinfo=timezone.utc),
                end_date=datetime(2025, 2, 15, tzinfo=timezone.utc),
            ),
            # This entry should be dropped (starts after as_of_date)
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 2, 15, tzinfo=timezone.utc),
                end_date=None,
            ),
        ]

        filtered = HistoryFilter.filter_by_as_of_date(history, as_of_date)

        # Should only have first 2 entries
        assert len(filtered) == 2
        assert filtered[0].status == "Открыт"
        assert filtered[1].status == "В работе"

    def test_filter_history_sets_end_date_to_none_if_after_as_of_date(self):
        """Test that end_date is set to None if it's after as-of-date."""
        as_of_date = datetime(2025, 2, 10, tzinfo=timezone.utc)

        history = [
            StatusHistoryEntry(
                status="В работе",
                status_display="В работе",
                start_date=datetime(2025, 2, 5, tzinfo=timezone.utc),
                end_date=datetime(2025, 2, 15, tzinfo=timezone.utc),  # After as_of_date
            ),
        ]

        filtered = HistoryFilter.filter_by_as_of_date(history, as_of_date)

        assert len(filtered) == 1
        assert filtered[0].status == "В работе"
        assert filtered[0].start_date == datetime(2025, 2, 5, tzinfo=timezone.utc)
        assert filtered[0].end_date is None  # Should be set to None

    def test_filter_history_keeps_entries_before_as_of_date(self):
        """Test that entries completely before as-of-date are kept unchanged."""
        as_of_date = datetime(2025, 2, 20, tzinfo=timezone.utc)

        history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 2, 1, tzinfo=timezone.utc),
                end_date=datetime(2025, 2, 5, tzinfo=timezone.utc),
            ),
            StatusHistoryEntry(
                status="В работе",
                status_display="В работе",
                start_date=datetime(2025, 2, 5, tzinfo=timezone.utc),
                end_date=datetime(2025, 2, 10, tzinfo=timezone.utc),
            ),
        ]

        filtered = HistoryFilter.filter_by_as_of_date(history, as_of_date)

        # Both entries should be kept unchanged
        assert len(filtered) == 2
        assert filtered[0].start_date == datetime(2025, 2, 1, tzinfo=timezone.utc)
        assert filtered[0].end_date == datetime(2025, 2, 5, tzinfo=timezone.utc)
        assert filtered[1].start_date == datetime(2025, 2, 5, tzinfo=timezone.utc)
        assert filtered[1].end_date == datetime(2025, 2, 10, tzinfo=timezone.utc)

    def test_filter_history_handles_naive_datetimes(self):
        """Test that naive datetimes are normalized to UTC."""
        # Naive as_of_date
        as_of_date = datetime(2025, 2, 10)  # No timezone

        history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 2, 1),  # Naive
                end_date=datetime(2025, 2, 5),  # Naive
            ),
        ]

        # Should not raise an error
        filtered = HistoryFilter.filter_by_as_of_date(history, as_of_date)

        assert len(filtered) == 1
        # Filtered entries should have timezone
        assert filtered[0].start_date.tzinfo is not None
        assert filtered[0].end_date.tzinfo is not None

    def test_filter_history_handles_timezone_aware_datetimes(self):
        """Test that timezone-aware datetimes are handled correctly."""
        as_of_date = datetime(2025, 2, 10, tzinfo=timezone.utc)

        history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 2, 1, tzinfo=timezone.utc),
                end_date=datetime(2025, 2, 5, tzinfo=timezone.utc),
            ),
        ]

        filtered = HistoryFilter.filter_by_as_of_date(history, as_of_date)

        assert len(filtered) == 1
        assert filtered[0].start_date.tzinfo == timezone.utc
        assert filtered[0].end_date.tzinfo == timezone.utc

    def test_filter_history_preserves_order(self):
        """Test that the order of history entries is preserved."""
        as_of_date = datetime(2025, 2, 20, tzinfo=timezone.utc)

        history = [
            StatusHistoryEntry(
                status="Status1",
                status_display="Status1",
                start_date=datetime(2025, 2, 1, tzinfo=timezone.utc),
                end_date=datetime(2025, 2, 5, tzinfo=timezone.utc),
            ),
            StatusHistoryEntry(
                status="Status2",
                status_display="Status2",
                start_date=datetime(2025, 2, 5, tzinfo=timezone.utc),
                end_date=datetime(2025, 2, 10, tzinfo=timezone.utc),
            ),
            StatusHistoryEntry(
                status="Status3",
                status_display="Status3",
                start_date=datetime(2025, 2, 10, tzinfo=timezone.utc),
                end_date=datetime(2025, 2, 15, tzinfo=timezone.utc),
            ),
        ]

        filtered = HistoryFilter.filter_by_as_of_date(history, as_of_date)

        # Order should be preserved
        assert len(filtered) == 3
        assert filtered[0].status == "Status1"
        assert filtered[1].status == "Status2"
        assert filtered[2].status == "Status3"

    def test_filter_history_handles_empty_history(self):
        """Test that empty history list is handled correctly."""
        as_of_date = datetime(2025, 2, 10, tzinfo=timezone.utc)

        history = []

        filtered = HistoryFilter.filter_by_as_of_date(history, as_of_date)

        assert filtered == []

    def test_filter_history_handles_none_end_dates(self):
        """Test that None end_dates (current status) are handled correctly."""
        as_of_date = datetime(2025, 2, 10, tzinfo=timezone.utc)

        history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 2, 1, tzinfo=timezone.utc),
                end_date=datetime(2025, 2, 5, tzinfo=timezone.utc),
            ),
            # Current status (end_date = None) that started before as_of_date
            StatusHistoryEntry(
                status="В работе",
                status_display="В работе",
                start_date=datetime(2025, 2, 5, tzinfo=timezone.utc),
                end_date=None,
            ),
        ]

        filtered = HistoryFilter.filter_by_as_of_date(history, as_of_date)

        # Both entries should be kept
        assert len(filtered) == 2
        assert filtered[1].end_date is None  # Should remain None

    def test_filter_history_at_exact_boundary(self):
        """Test filtering at exact boundary dates."""
        as_of_date = datetime(2025, 2, 10, tzinfo=timezone.utc)

        history = [
            # Entry that ends exactly at as_of_date
            StatusHistoryEntry(
                status="Status1",
                status_display="Status1",
                start_date=datetime(2025, 2, 5, tzinfo=timezone.utc),
                end_date=datetime(2025, 2, 10, tzinfo=timezone.utc),
            ),
            # Entry that starts exactly at as_of_date (should be kept)
            StatusHistoryEntry(
                status="Status2",
                status_display="Status2",
                start_date=datetime(2025, 2, 10, tzinfo=timezone.utc),
                end_date=datetime(2025, 2, 15, tzinfo=timezone.utc),
            ),
        ]

        filtered = HistoryFilter.filter_by_as_of_date(history, as_of_date)

        # Entry starting at as_of_date should be included
        assert len(filtered) == 2
        assert filtered[0].end_date == datetime(2025, 2, 10, tzinfo=timezone.utc)
        assert filtered[1].start_date == datetime(2025, 2, 10, tzinfo=timezone.utc)
        assert filtered[1].end_date is None  # end_date after as_of_date

    def test_filter_history_creates_new_instances(self):
        """Test that filter creates new StatusHistoryEntry instances, not modifying originals."""
        as_of_date = datetime(2025, 2, 10, tzinfo=timezone.utc)

        original_entry = StatusHistoryEntry(
            status="В работе",
            status_display="В работе",
            start_date=datetime(2025, 2, 5, tzinfo=timezone.utc),
            end_date=datetime(2025, 2, 15, tzinfo=timezone.utc),
        )

        history = [original_entry]

        filtered = HistoryFilter.filter_by_as_of_date(history, as_of_date)

        # Original should not be modified
        assert original_entry.end_date == datetime(2025, 2, 15, tzinfo=timezone.utc)

        # Filtered should have None end_date
        assert filtered[0].end_date is None

        # Should be a different instance
        assert filtered[0] is not original_entry
