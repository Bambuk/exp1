"""Tests for Tail metric functionality."""

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


class TestTailMetric:
    """Tests for Tail metric calculation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MetricsService()

    def test_calculate_tail_metric_success(self):
        """Test successful Tail metric calculation."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 5), None
            ),
            StatusHistoryEntry(
                "Review", "Review", datetime(2024, 1, 7), None
            ),  # Exit from MP/External Test
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 10), None),
        ]

        result = self.service.calculate_tail_metric(history, ["Done"])
        assert result == 5  # 10 days - 5 days (start of MP/External Test) = 5 days

    def test_calculate_tail_metric_multiple_mp_external_test(self):
        """Test Tail metric calculation with multiple MP/External Test occurrences."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "Review", "Review", datetime(2024, 1, 5), None
            ),  # First exit
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 7), None
            ),
            StatusHistoryEntry(
                "Done", "Done", datetime(2024, 1, 10), None
            ),  # Second exit (last one)
        ]

        result = self.service.calculate_tail_metric(history, ["Done"])
        assert (
            result == 3
        )  # 10 days - 7 days (last exit from MP/External Test) = 3 days

    def test_calculate_tail_metric_with_pause_time(self):
        """Test Tail metric calculation excluding pause time."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "Review", "Review", datetime(2024, 1, 5), None
            ),  # Exit from MP/External Test
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 7), None
            ),
            StatusHistoryEntry(
                "Review", "Review", datetime(2024, 1, 9), None
            ),  # Resume
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 12), None),
        ]

        result = self.service.calculate_tail_metric(history, ["Done"])
        # Total time: 12-3=9 days, but 2 days in pause, so effective time: 9-2=7 days
        assert result == 7

    def test_calculate_tail_metric_no_mp_external_test(self):
        """Test Tail metric calculation when MP/External Test status not found."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 5), None),
        ]

        result = self.service.calculate_tail_metric(history, ["Done"])
        assert result is None

    def test_calculate_tail_metric_no_done_status(self):
        """Test Tail metric calculation when no done status found after MP/External Test."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry("Review", "Review", datetime(2024, 1, 5), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 7), None
            ),
        ]

        result = self.service.calculate_tail_metric(history, ["Done"])
        assert result is None

    def test_calculate_tail_metric_ends_in_mp_external_test(self):
        """Test Tail metric calculation when task ends in MP/External Test status."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 3), None
            ),
        ]

        result = self.service.calculate_tail_metric(history, ["Done"])
        assert result is None

    def test_calculate_tail_metric_empty_history(self):
        """Test Tail metric calculation with empty history."""
        result = self.service.calculate_tail_metric([], ["Done"])
        assert result is None

    def test_calculate_tail_metric_multiple_done_statuses(self):
        """Test Tail metric calculation with multiple done statuses."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "Review", "Review", datetime(2024, 1, 5), None
            ),  # Exit from MP/External Test
            StatusHistoryEntry(
                "Выполнено с ИТ", "Выполнено с ИТ", datetime(2024, 1, 8), None
            ),  # First done status
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 10), None),
        ]

        result = self.service.calculate_tail_metric(history, ["Done", "Выполнено с ИТ"])
        assert result == 5  # 8 days - 3 days (start of MP/External Test) = 5 days

    def test_calculate_tail_metric_complex_pause_scenario(self):
        """Test Tail metric calculation with complex pause scenario."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "Review", "Review", datetime(2024, 1, 5), None
            ),  # Exit from MP/External Test
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 7), None
            ),
            StatusHistoryEntry(
                "Review", "Review", datetime(2024, 1, 9), None
            ),  # Resume
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 11), None
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 14), None),
        ]

        result = self.service.calculate_tail_metric(history, ["Done"])
        # Total time: 14-3=11 days, but 5 days in pause (2+3), so effective time: 11-5=6 days
        assert result == 6

    def test_calculate_tail_metric_unsorted_history(self):
        """Test Tail metric calculation with unsorted history (should be sorted internally)."""
        history = [
            StatusHistoryEntry(
                "Review", "Review", datetime(2024, 1, 5), None
            ),  # Exit from MP/External Test
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 10), None),
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 3), None
            ),
        ]

        result = self.service.calculate_tail_metric(history, ["Done"])
        assert result == 7  # 10 days - 3 days (start of MP/External Test) = 7 days

    def test_calculate_tail_metric_filters_short_external_test(self):
        """Test Tail metric ignores short (< 5 min) MP/External Test entries."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            # Длинный "МП / Внешний тест" (> 5 минут)
            StatusHistoryEntry(
                "МП / Внешний тест",
                "МП / Внешний тест",
                datetime(2024, 1, 5),
                datetime(2024, 1, 10),  # 5 дней - длинный
            ),
            StatusHistoryEntry("Review", "Review", datetime(2024, 1, 12), None),
            # Короткий "МП / Внешний тест" (< 5 минут) - должен игнорироваться
            StatusHistoryEntry(
                "МП / Внешний тест",
                "МП / Внешний тест",
                datetime(2024, 1, 15, 10, 0),
                datetime(2024, 1, 15, 10, 2),  # 2 минуты - короткий
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 20), None),
        ]

        result = self.service.calculate_tail_metric(history, ["Done"])

        # Должен использовать первый длинный "МП / Внешний тест" (1/5), не короткий (1/15)
        # Tail = 20 - 5 = 15 дней
        assert result == 15


class TestTailMetricIntegration:
    """Integration tests for Tail metric with other metrics."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MetricsService()

    def test_tail_metric_with_ttd_and_ttm(self):
        """Test Tail metric calculation alongside TTD and TTM."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 3), None
            ),  # First change
            StatusHistoryEntry(
                "Готова к разработке", "Готова к разработке", datetime(2024, 1, 5), None
            ),  # TTD target
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 7), None
            ),
            StatusHistoryEntry(
                "Review", "Review", datetime(2024, 1, 9), None
            ),  # Exit from MP/External Test
            StatusHistoryEntry(
                "Done", "Done", datetime(2024, 1, 12), None
            ),  # TTM target
        ]

        # Calculate all metrics
        ttd = self.service.calculate_time_to_delivery(history, ["Discovery"])
        ttm = self.service.calculate_time_to_market(history, ["Done"])
        tail = self.service.calculate_tail_metric(history, ["Done"])

        assert ttd == 4  # 5-1 = 4 days
        assert ttm == 11  # 12-1 = 11 days
        assert tail == 5  # 12-7 = 5 days (from start of MP/External Test to Done)

    def test_tail_metric_with_pause_time_integration(self):
        """Test Tail metric with pause time integration."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "Готова к разработке", "Готова к разработке", datetime(2024, 1, 5), None
            ),
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 7), None
            ),
            StatusHistoryEntry(
                "Review", "Review", datetime(2024, 1, 9), None
            ),  # Exit from MP/External Test
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 11), None
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 14), None),
        ]

        # Calculate pause time
        pause_time = self.service.calculate_pause_time(history)
        assert pause_time == 3  # 14-11 = 3 days

        # Calculate Tail metric (should exclude pause time)
        tail = self.service.calculate_tail_metric(history, ["Done"])
        # Total time: 14-7=7 days, but 3 days in pause, so effective time: 7-3=4 days
        assert tail == 4


class TestTailMetricGroupMetrics:
    """Tests for Tail metric in group metrics calculation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MetricsService()

    def test_calculate_enhanced_group_metrics_with_tail(self):
        """Test enhanced group metrics calculation including Tail metric."""
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
        assert result.total_tasks == 6  # ttd + ttm count

    def test_calculate_group_metrics_with_tail(self):
        """Test regular group metrics calculation including Tail metric."""
        ttd_times = [1, 2, 3]
        ttm_times = [4, 5, 6]
        tail_times = [1, 2, 3]

        result = self.service.calculate_group_metrics(
            "TestGroup", ttd_times, ttm_times, tail_times
        )

        assert result.group_name == "TestGroup"
        assert result.ttd_metrics.times == ttd_times
        assert result.ttm_metrics.times == ttm_times
        assert result.tail_metrics.times == tail_times
        assert result.total_tasks == 6  # ttd + ttm count

    def test_calculate_enhanced_group_metrics_empty_tail_times(self):
        """Test enhanced group metrics with empty Tail times."""
        ttd_times = [1, 2, 3]
        ttd_pause_times = [0, 1, 2]
        ttm_times = [4, 5, 6]
        ttm_pause_times = [1, 0, 1]
        tail_times = []

        result = self.service.calculate_enhanced_group_metrics(
            "TestGroup",
            ttd_times,
            ttd_pause_times,
            ttm_times,
            ttm_pause_times,
            tail_times,
        )

        assert result.tail_metrics.times == []
        assert result.tail_metrics.pause_times is None
        assert result.tail_metrics.mean is None
        assert result.tail_metrics.p85 is None
        assert result.tail_metrics.count == 0


if __name__ == "__main__":
    pytest.main([__file__])
