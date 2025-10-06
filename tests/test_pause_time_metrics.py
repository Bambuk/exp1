"""Tests for pause time metrics functionality."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from radiator.commands.models.time_to_market_models import (
    GroupMetrics,
    StatusHistoryEntry,
    StatusMapping,
    TimeMetrics,
)
from radiator.commands.services.metrics_service import MetricsService


class TestPauseTimeMetrics:
    """Tests for pause time calculation and exclusion from TTM/TTD."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MetricsService()

    def test_calculate_pause_time_single_pause_period(self):
        """Test calculation of pause time for single pause period."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 5), None
            ),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 8), None
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 10), None),
        ]

        pause_time = self.service.calculate_pause_time(history)
        assert pause_time == 3  # 8 days - 5 days = 3 days in pause

    def test_calculate_pause_time_multiple_pause_periods(self):
        """Test calculation of pause time for multiple pause periods."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 5), None
            ),
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 7), None
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 9), None),
        ]

        pause_time = self.service.calculate_pause_time(history)
        assert pause_time == 4  # (5-3) + (9-7) = 2 + 2 = 4 days in pause

    def test_calculate_pause_time_no_pause(self):
        """Test calculation when no pause periods exist."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 5), None),
        ]

        pause_time = self.service.calculate_pause_time(history)
        assert pause_time == 0

    def test_calculate_pause_time_ends_in_pause(self):
        """Test calculation when task ends in pause status."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 5), None
            ),
        ]

        pause_time = self.service.calculate_pause_time(history)
        assert pause_time == 0  # No end date for pause, so no time calculated

    def test_calculate_time_to_delivery_excludes_pause_time(self):
        """Test that TTD calculation excludes pause time."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 5), None
            ),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 8), None
            ),
            StatusHistoryEntry(
                "Готова к разработке",
                "Готова к разработке",
                datetime(2024, 1, 10),
                None,
            ),
        ]

        ttd = self.service.calculate_time_to_delivery(history, ["Discovery"])
        # Total time: 10-1=9 days, but 3 days in pause, so effective time: 9-3=6 days
        assert ttd == 6

    def test_calculate_time_to_market_excludes_pause_time(self):
        """Test that TTM calculation excludes pause time."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 5), None
            ),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 8), None
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 10), None),
        ]

        ttm = self.service.calculate_time_to_market(history, ["Done"])
        # Total time: 10-1=9 days, but 3 days in pause, so effective time: 9-3=6 days
        assert ttm == 6

    def test_calculate_enhanced_statistics_with_pause_time(self):
        """Test enhanced statistics calculation including pause time."""
        times = [1, 2, 3]
        pause_times = [0, 1, 2]

        result = self.service.calculate_enhanced_statistics(times, pause_times)

        assert result.times == times
        assert result.mean == 2.0
        assert result.p85 == 2.7
        assert result.count == 3
        assert result.pause_times == pause_times
        assert result.pause_mean == 1.0
        assert result.pause_p85 == 1.7

    def test_calculate_enhanced_group_metrics_with_pause_time(self):
        """Test enhanced group metrics calculation including pause time."""
        ttd_times = [1, 2, 3]
        ttd_pause_times = [0, 1, 2]
        ttm_times = [4, 5, 6]
        ttm_pause_times = [1, 0, 1]
        tail_times = [1, 2, 3]

        result = self.service.calculate_enhanced_group_metrics(
            "TestGroup",
            ttd_times,
            ttd_pause_times,
            ttm_times,
            ttm_pause_times,
            tail_times,
        )

        assert result.group_name == "TestGroup"
        assert result.ttd_metrics.times == ttd_times
        assert result.ttd_metrics.pause_times == ttd_pause_times
        assert result.ttm_metrics.times == ttm_times
        assert result.ttm_metrics.pause_times == ttm_pause_times
        assert result.tail_metrics.times == tail_times
        assert result.tail_metrics.pause_times is None
        assert result.total_tasks == 6

    def test_calculate_pause_time_empty_history(self):
        """Test pause time calculation with empty history."""
        pause_time = self.service.calculate_pause_time([])
        assert pause_time == 0

    def test_calculate_pause_time_single_entry(self):
        """Test pause time calculation with single history entry."""
        history = [
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 1), None
            ),
        ]

        pause_time = self.service.calculate_pause_time(history)
        assert pause_time == 0  # No end date, so no time calculated


class TestPauseTimeIntegration:
    """Integration tests for pause time functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MetricsService()

    def test_full_workflow_with_pause_time(self):
        """Test full workflow including pause time calculation and exclusion."""
        # Create a complex history with multiple pause periods
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 5), None
            ),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 8), None
            ),
            StatusHistoryEntry(
                "Готова к разработке",
                "Готова к разработке",
                datetime(2024, 1, 10),
                None,
            ),
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 12), None
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 15), None),
        ]

        # Calculate pause time
        pause_time = self.service.calculate_pause_time(history)
        assert pause_time == 6  # (8-5) + (15-12) = 3 + 3 = 6

        # Calculate TTD (should exclude pause time)
        ttd = self.service.calculate_time_to_delivery(history, ["Discovery"])
        # Total time to 'Готова к разработке': 10-1=9 days, minus 3 days pause (only up to 'Готова к разработке') = 6 days
        assert ttd == 6

        # Calculate TTM (should exclude pause time)
        ttm = self.service.calculate_time_to_market(history, ["Done"])
        # Total time to 'Done': 15-1=14 days, minus 6 days pause = 8 days
        assert ttm == 8

    def test_pause_time_up_to_date_excludes_later_pauses(self):
        """Test that pause time calculation up to a date excludes pauses after that date."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 5), None
            ),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 8), None
            ),
            StatusHistoryEntry(
                "Готова к разработке",
                "Готова к разработке",
                datetime(2024, 1, 10),
                None,
            ),
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 12), None
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 15), None),
        ]

        # Calculate pause time up to "Готова к разработке"
        ttd_target_date = datetime(2024, 1, 10)
        pause_time_up_to_ttd = self.service.calculate_pause_time_up_to_date(
            history, ttd_target_date
        )
        # Should only include pause from 5th to 8th = 3 days
        # Should NOT include pause from 12th to 15th
        assert pause_time_up_to_ttd == 3

        # Calculate pause time up to "Done"
        ttm_target_date = datetime(2024, 1, 15)
        pause_time_up_to_ttm = self.service.calculate_pause_time_up_to_date(
            history, ttm_target_date
        )
        # Should include BOTH pauses: (8-5) + (15-12) = 3 + 3 = 6 days
        assert pause_time_up_to_ttm == 6

        # Total pause time (without limit) should be the same as up to Done
        total_pause_time = self.service.calculate_pause_time(history)
        assert total_pause_time == 6

    def test_pause_time_statistics_match_calculation(self):
        """Test that pause time in statistics matches what was actually subtracted from TTD/TTM."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 6), None
            ),  # 3 days pause
            StatusHistoryEntry(
                "Готова к разработке",
                "Готова к разработке",
                datetime(2024, 1, 8),
                None,
            ),
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 10), None
            ),
            StatusHistoryEntry(
                "Done", "Done", datetime(2024, 1, 13), None
            ),  # 3 days pause
        ]

        # Calculate TTD
        ttd = self.service.calculate_time_to_delivery(history, ["Готова к разработке"])
        # Total: 8-1=7 days, minus 3 days pause before TTD = 4 days
        assert ttd == 4

        # Calculate pause time up to TTD target
        ttd_target_date = datetime(2024, 1, 8)
        pause_time_for_ttd = self.service.calculate_pause_time_up_to_date(
            history, ttd_target_date
        )
        # Should be 3 days (the pause BEFORE TTD target)
        assert pause_time_for_ttd == 3

        # Calculate TTM
        ttm = self.service.calculate_time_to_market(history, ["Done"])
        # Total: 13-1=12 days, minus 6 days pause (both) = 6 days
        assert ttm == 6

        # Calculate pause time up to TTM target
        ttm_target_date = datetime(2024, 1, 13)
        pause_time_for_ttm = self.service.calculate_pause_time_up_to_date(
            history, ttm_target_date
        )
        # Should be 6 days (both pauses)
        assert pause_time_for_ttm == 6


if __name__ == "__main__":
    pytest.main([__file__])
