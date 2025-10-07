"""Tests for status duration metrics functionality."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from radiator.commands.models.time_to_market_models import (
    StatusHistoryEntry,
    StatusMapping,
)
from radiator.commands.services.metrics_service import MetricsService


class TestStatusDurationMetrics:
    """Tests for calculating time spent in specific statuses."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MetricsService()

    def test_calculate_discovery_backlog_duration_single_period(self):
        """Test calculation of time spent in Discovery backlog status."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "Discovery backlog", "Discovery backlog", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry("В работе", "В работе", datetime(2024, 1, 8), None),
            StatusHistoryEntry(
                "Готова к разработке",
                "Готова к разработке",
                datetime(2024, 1, 15),
                None,
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 20), None),
        ]

        duration = self.service.calculate_status_duration(history, "Discovery backlog")
        assert duration == 5  # 8 days - 3 days = 5 days in Discovery backlog

    def test_calculate_discovery_backlog_duration_multiple_periods(self):
        """Test calculation of time spent in Discovery backlog across multiple periods."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "Discovery backlog", "Discovery backlog", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry("В работе", "В работе", datetime(2024, 1, 8), None),
            StatusHistoryEntry(
                "Discovery backlog", "Discovery backlog", datetime(2024, 1, 12), None
            ),
            StatusHistoryEntry(
                "Готова к разработке",
                "Готова к разработке",
                datetime(2024, 1, 18),
                None,
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 25), None),
        ]

        duration = self.service.calculate_status_duration(history, "Discovery backlog")
        assert duration == 11  # (8-3) + (18-12) = 5 + 6 = 11 days

    def test_calculate_ready_for_development_duration_single_period(self):
        """Test calculation of time spent in 'Готова к разработке' status."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry("В работе", "В работе", datetime(2024, 1, 3), None),
            StatusHistoryEntry(
                "Готова к разработке",
                "Готова к разработке",
                datetime(2024, 1, 10),
                None,
            ),
            StatusHistoryEntry(
                "МП / В работе", "МП / В работе", datetime(2024, 1, 15), None
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 25), None),
        ]

        duration = self.service.calculate_status_duration(
            history, "Готова к разработке"
        )
        assert duration == 5  # 15 days - 10 days = 5 days in "Готова к разработке"

    def test_calculate_ready_for_development_duration_multiple_periods(self):
        """Test calculation of time spent in 'Готова к разработке' across multiple periods."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "Готова к разработке", "Готова к разработке", datetime(2024, 1, 5), None
            ),
            StatusHistoryEntry("В работе", "В работе", datetime(2024, 1, 8), None),
            StatusHistoryEntry(
                "Готова к разработке",
                "Готова к разработке",
                datetime(2024, 1, 12),
                None,
            ),
            StatusHistoryEntry(
                "МП / В работе", "МП / В работе", datetime(2024, 1, 18), None
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 30), None),
        ]

        duration = self.service.calculate_status_duration(
            history, "Готова к разработке"
        )
        assert duration == 9  # (8-5) + (18-12) = 3 + 6 = 9 days

    def test_calculate_status_duration_with_pause(self):
        """Test calculation of status duration when task is paused."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "Discovery backlog", "Discovery backlog", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 6), None
            ),
            StatusHistoryEntry(
                "Discovery backlog", "Discovery backlog", datetime(2024, 1, 9), None
            ),
            StatusHistoryEntry("В работе", "В работе", datetime(2024, 1, 12), None),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 20), None),
        ]

        duration = self.service.calculate_status_duration(history, "Discovery backlog")
        assert duration == 6  # (6-3) + (12-9) = 3 + 3 = 6 days (pause time excluded)

    def test_calculate_status_duration_status_not_found(self):
        """Test calculation when target status is not found in history."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry("В работе", "В работе", datetime(2024, 1, 3), None),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 10), None),
        ]

        duration = self.service.calculate_status_duration(history, "Discovery backlog")
        assert duration == 0  # Status not found, should return 0

    def test_calculate_status_duration_empty_history(self):
        """Test calculation with empty history."""
        history = []

        duration = self.service.calculate_status_duration(history, "Discovery backlog")
        assert duration == 0

    def test_calculate_status_duration_single_entry(self):
        """Test calculation with single history entry."""
        history = [
            StatusHistoryEntry(
                "Discovery backlog", "Discovery backlog", datetime(2024, 1, 1), None
            ),
        ]

        duration = self.service.calculate_status_duration(history, "Discovery backlog")
        assert duration == 0  # Single entry, no duration to calculate

    def test_calculate_status_duration_last_status(self):
        """Test calculation when target status is the last status in history."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry("В работе", "В работе", datetime(2024, 1, 3), None),
            StatusHistoryEntry(
                "Готова к разработке",
                "Готова к разработке",
                datetime(2024, 1, 10),
                None,
            ),
        ]

        duration = self.service.calculate_status_duration(
            history, "Готова к разработке"
        )
        assert duration == 0  # Last status, no next status to calculate duration

    def test_calculate_status_duration_with_same_status_consecutive(self):
        """Test calculation when same status appears consecutively."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "Discovery backlog", "Discovery backlog", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "Discovery backlog", "Discovery backlog", datetime(2024, 1, 5), None
            ),  # Same status
            StatusHistoryEntry("В работе", "В работе", datetime(2024, 1, 8), None),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 15), None),
        ]

        duration = self.service.calculate_status_duration(history, "Discovery backlog")
        assert (
            duration == 5
        )  # (8-3) = 5 days (second entry ignored as it's the same status)

    def test_calculate_status_duration_edge_case_same_day(self):
        """Test calculation when status changes happen on the same day."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "Discovery backlog", "Discovery backlog", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "В работе", "В работе", datetime(2024, 1, 3), None
            ),  # Same day
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 10), None),
        ]

        duration = self.service.calculate_status_duration(history, "Discovery backlog")
        assert duration == 0  # Same day transition, duration is 0

    def test_calculate_status_duration_negative_duration(self):
        """Test calculation when dates are in wrong order (should not happen in real data)."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "Discovery backlog", "Discovery backlog", datetime(2024, 1, 8), None
            ),
            StatusHistoryEntry(
                "В работе", "В работе", datetime(2024, 1, 3), None
            ),  # Earlier date
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 10), None),
        ]

        duration = self.service.calculate_status_duration(history, "Discovery backlog")
        # After sorting, Discovery backlog goes from 8 to 10 (Done), so duration is 2 days
        assert duration == 2  # (10-8) = 2 days


class TestStatusDurationIntegration:
    """Integration tests for status duration metrics with TTM/TTD calculations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MetricsService()

    def test_status_duration_with_ttd_calculation(self):
        """Test that status duration calculation works alongside TTD calculation."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "Discovery backlog", "Discovery backlog", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry("В работе", "В работе", datetime(2024, 1, 8), None),
            StatusHistoryEntry(
                "Готова к разработке",
                "Готова к разработке",
                datetime(2024, 1, 15),
                None,
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 25), None),
        ]

        # Calculate TTD
        ttd = self.service.calculate_time_to_delivery(history, ["Discovery backlog"])

        # Calculate status durations
        discovery_backlog_duration = self.service.calculate_status_duration(
            history, "Discovery backlog"
        )
        ready_for_dev_duration = self.service.calculate_status_duration(
            history, "Готова к разработке"
        )

        assert ttd == 14  # (15-1) = 14 days
        assert discovery_backlog_duration == 5  # (8-3) = 5 days
        assert (
            ready_for_dev_duration == 10
        )  # (25-15) = 10 days (from "Готова к разработке" to "Done")

    def test_status_duration_with_ttm_calculation(self):
        """Test that status duration calculation works alongside TTM calculation."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "Discovery backlog", "Discovery backlog", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry("В работе", "В работе", datetime(2024, 1, 8), None),
            StatusHistoryEntry(
                "Готова к разработке",
                "Готова к разработке",
                datetime(2024, 1, 15),
                None,
            ),
            StatusHistoryEntry(
                "МП / В работе", "МП / В работе", datetime(2024, 1, 20), None
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 30), None),
        ]

        # Calculate TTM
        ttm = self.service.calculate_time_to_market(history, ["Done"])

        # Calculate status durations
        discovery_backlog_duration = self.service.calculate_status_duration(
            history, "Discovery backlog"
        )
        ready_for_dev_duration = self.service.calculate_status_duration(
            history, "Готова к разработке"
        )

        assert ttm == 29  # (30-1) = 29 days
        assert discovery_backlog_duration == 5  # (8-3) = 5 days
        assert ready_for_dev_duration == 5  # (20-15) = 5 days
