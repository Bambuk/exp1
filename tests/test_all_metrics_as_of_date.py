"""Comprehensive tests for all metrics with as-of-date functionality.

This test suite verifies that all metrics in TTM Details report correctly
handle the as_of_date parameter for unfinished tasks.

Tests are designed to FAIL for metrics that don't yet support as_of_date,
showing which metrics need to be updated.

Metrics tested:
- TTM (Time To Market) - _calculate_ttm_unfinished
- Pause - calculate_pause_time_up_to_date
- Tail - _calculate_tail
- DevLT (Development Lead Time) - ✅ already supports as_of_date
- TTD (Time To Delivery) - calculate_time_to_delivery
- TTD Pause - _calculate_ttd_pause
- Discovery backlog (дни) - _calculate_discovery_backlog_days
- Готова к разработке (дни) - _calculate_ready_for_dev_days
- calculate_status_duration - generic helper method
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from radiator.commands.generate_ttm_details_report import TTMDetailsReportGenerator
from radiator.commands.models.time_to_market_models import StatusHistoryEntry
from radiator.commands.services.metrics_service import MetricsService


class TestTTMUnfinishedAsOfDate:
    """Tests for TTM calculation for unfinished tasks with as-of-date."""

    def test_ttm_unfinished_with_as_of_date(self):
        """Test that _calculate_ttm_unfinished uses as_of_date for open intervals."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        base_date = datetime(2025, 2, 1, tzinfo=timezone.utc)
        done_statuses = ["Закрыт", "Done", "Выполнено"]

        # Task still in work (open interval)
        history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=base_date,
                end_date=base_date + timedelta(days=5),
            ),
            StatusHistoryEntry(
                status="МП / В работе",
                status_display="МП / В работе",
                start_date=base_date + timedelta(days=5),
                end_date=None,  # Still in work
            ),
        ]

        # Calculate TTM as of Feb 10 (should be ~10 days)
        as_of_date_feb10 = base_date + timedelta(days=10)
        ttm_feb10 = generator._calculate_ttm_unfinished(
            history, done_statuses, as_of_date_feb10
        )

        # Calculate TTM as of Feb 20 (should be ~20 days)
        as_of_date_feb20 = base_date + timedelta(days=20)
        ttm_feb20 = generator._calculate_ttm_unfinished(
            history, done_statuses, as_of_date_feb20
        )

        # Assertions
        assert (
            ttm_feb10 is not None
        ), "TTM должен рассчитываться для незавершенной задачи"
        assert (
            ttm_feb20 is not None
        ), "TTM должен рассчитываться для незавершенной задачи"
        assert ttm_feb20 > ttm_feb10, "TTM должен расти с увеличением as_of_date"
        assert (
            ttm_feb20 - ttm_feb10 >= 9
        ), f"Разница TTM должна быть ~10 дней, получено {ttm_feb20 - ttm_feb10}"


class TestPauseTimeAsOfDate:
    """Tests for Pause time calculation with as-of-date."""

    def test_pause_time_with_as_of_date_for_open_pause(self):
        """Test pause time when task is currently paused (open interval)."""
        metrics_service = MetricsService()

        base_date = datetime(2025, 2, 1, tzinfo=timezone.utc)

        # Task currently paused (open interval)
        history = [
            StatusHistoryEntry(
                status="МП / В работе",
                status_display="МП / В работе",
                start_date=base_date,
                end_date=base_date + timedelta(days=5),
            ),
            StatusHistoryEntry(
                status="Приостановлено",
                status_display="Приостановлено",
                start_date=base_date + timedelta(days=5),
                end_date=None,  # Still paused
            ),
        ]

        # Calculate pause as of Feb 10 (5 days paused)
        as_of_date_feb10 = base_date + timedelta(days=10)
        pause_feb10 = metrics_service.calculate_pause_time_up_to_date(
            history, as_of_date_feb10
        )

        # Calculate pause as of Feb 20 (15 days paused)
        as_of_date_feb20 = base_date + timedelta(days=20)
        pause_feb20 = metrics_service.calculate_pause_time_up_to_date(
            history, as_of_date_feb20
        )

        # Assertions
        assert pause_feb10 is not None, "Pause time должен рассчитываться"
        assert pause_feb20 is not None, "Pause time должен рассчитываться"
        assert (
            pause_feb10 >= 4 and pause_feb10 <= 6
        ), f"Pause должен быть ~5 дней, получено {pause_feb10}"
        assert (
            pause_feb20 >= 14 and pause_feb20 <= 16
        ), f"Pause должен быть ~15 дней, получено {pause_feb20}"
        assert (
            pause_feb20 - pause_feb10 >= 9
        ), f"Разница должна быть ~10 дней, получено {pause_feb20 - pause_feb10}"


class TestTailAsOfDate:
    """Tests for Tail time calculation with as-of-date."""

    def test_tail_with_as_of_date_for_open_external_test(self):
        """Test tail time when task is in external test (open interval)."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        base_date = datetime(2025, 2, 1, tzinfo=timezone.utc)
        done_statuses = ["Закрыт", "Done", "Выполнено"]

        # Task in external test (open interval)
        history = [
            StatusHistoryEntry(
                status="МП / В работе",
                status_display="МП / В работе",
                start_date=base_date,
                end_date=base_date + timedelta(days=10),
            ),
            StatusHistoryEntry(
                status="МП / Внешний тест",
                status_display="МП / Внешний тест",
                start_date=base_date + timedelta(days=10),
                end_date=None,  # Still in test
            ),
        ]

        # Calculate tail as of Feb 15 (5 days in test)
        as_of_date_feb15 = base_date + timedelta(days=15)
        tail_feb15 = generator._calculate_tail(
            1, done_statuses, history, as_of_date_feb15
        )

        # Calculate tail as of Feb 25 (15 days in test)
        as_of_date_feb25 = base_date + timedelta(days=25)
        tail_feb25 = generator._calculate_tail(
            1, done_statuses, history, as_of_date_feb25
        )

        # Assertions
        assert (
            tail_feb15 is not None
        ), "Tail должен рассчитываться для задачи в external test"
        assert (
            tail_feb25 is not None
        ), "Tail должен рассчитываться для задачи в external test"
        assert tail_feb25 > tail_feb15, "Tail должен расти с увеличением as_of_date"
        assert (
            tail_feb25 - tail_feb15 >= 9
        ), f"Разница должна быть ~10 дней, получено {tail_feb25 - tail_feb15}"


class TestTTDAsOfDate:
    """Tests for TTD (Time To Delivery) calculation with as-of-date."""

    def test_ttd_with_as_of_date_for_open_ready_interval(self):
        """Test TTD when task is still in 'Готова к разработке' (open interval)."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        base_date = datetime(2025, 2, 1, tzinfo=timezone.utc)
        target_statuses = ["Готова к разработке"]

        # Task still in "Готова к разработке" (open interval)
        history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=base_date,
                end_date=base_date + timedelta(days=5),
            ),
            StatusHistoryEntry(
                status="Готова к разработке",
                status_display="Готова к разработке",
                start_date=base_date + timedelta(days=5),
                end_date=None,  # Still in this status
            ),
        ]

        # Calculate TTD as of Feb 10 (should include ~5 days in ready status)
        as_of_date_feb10 = base_date + timedelta(days=10)
        ttd_feb10 = generator._calculate_ttd(
            1, target_statuses, history, as_of_date_feb10
        )

        # Calculate TTD as of Feb 20 (should include ~15 days in ready status)
        as_of_date_feb20 = base_date + timedelta(days=20)
        ttd_feb20 = generator._calculate_ttd(
            1, target_statuses, history, as_of_date_feb20
        )

        # Assertions
        assert ttd_feb10 is not None, "TTD должен рассчитываться"
        assert ttd_feb20 is not None, "TTD должен рассчитываться"
        assert ttd_feb20 > ttd_feb10, "TTD должен расти с увеличением as_of_date"
        assert (
            ttd_feb20 - ttd_feb10 >= 9
        ), f"Разница должна быть ~10 дней, получено {ttd_feb20 - ttd_feb10}"


class TestDiscoveryBacklogAsOfDate:
    """Tests for Discovery backlog days calculation with as-of-date."""

    def test_discovery_backlog_with_as_of_date_for_open_interval(self):
        """Test discovery backlog days when task is still in backlog (open interval)."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        base_date = datetime(2025, 2, 1, tzinfo=timezone.utc)

        # Task still in Discovery backlog (open interval)
        history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=base_date,
                end_date=base_date + timedelta(days=2),
            ),
            StatusHistoryEntry(
                status="Discovery backlog",
                status_display="Discovery backlog",
                start_date=base_date + timedelta(days=2),
                end_date=None,  # Still in backlog
            ),
        ]

        # Calculate as of Feb 10 (8 days in backlog)
        as_of_date_feb10 = base_date + timedelta(days=10)
        days_feb10 = generator._calculate_discovery_backlog_days(
            1, history, as_of_date_feb10
        )

        # Calculate as of Feb 20 (18 days in backlog)
        as_of_date_feb20 = base_date + timedelta(days=20)
        days_feb20 = generator._calculate_discovery_backlog_days(
            1, history, as_of_date_feb20
        )

        # Assertions
        assert days_feb10 is not None, "Discovery backlog days должен рассчитываться"
        assert days_feb20 is not None, "Discovery backlog days должен рассчитываться"
        assert (
            days_feb10 >= 7 and days_feb10 <= 9
        ), f"Должно быть ~8 дней, получено {days_feb10}"
        assert (
            days_feb20 >= 17 and days_feb20 <= 19
        ), f"Должно быть ~18 дней, получено {days_feb20}"
        assert (
            days_feb20 - days_feb10 >= 9
        ), f"Разница должна быть ~10 дней, получено {days_feb20 - days_feb10}"


class TestReadyForDevAsOfDate:
    """Tests for 'Готова к разработке' days calculation with as-of-date."""

    def test_ready_for_dev_with_as_of_date_for_open_interval(self):
        """Test ready for dev days when task is still ready (open interval)."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        base_date = datetime(2025, 2, 1, tzinfo=timezone.utc)

        # Task still in "Готова к разработке" (open interval)
        history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=base_date,
                end_date=base_date + timedelta(days=3),
            ),
            StatusHistoryEntry(
                status="Готова к разработке",
                status_display="Готова к разработке",
                start_date=base_date + timedelta(days=3),
                end_date=None,  # Still ready
            ),
        ]

        # Calculate as of Feb 12 (9 days ready)
        as_of_date_feb12 = base_date + timedelta(days=12)
        days_feb12 = generator._calculate_ready_for_dev_days(
            1, history, as_of_date_feb12
        )

        # Calculate as of Feb 22 (19 days ready)
        as_of_date_feb22 = base_date + timedelta(days=22)
        days_feb22 = generator._calculate_ready_for_dev_days(
            1, history, as_of_date_feb22
        )

        # Assertions
        assert days_feb12 is not None, "Ready for dev days должен рассчитываться"
        assert days_feb22 is not None, "Ready for dev days должен рассчитываться"
        assert (
            days_feb12 >= 8 and days_feb12 <= 10
        ), f"Должно быть ~9 дней, получено {days_feb12}"
        assert (
            days_feb22 >= 18 and days_feb22 <= 20
        ), f"Должно быть ~19 дней, получено {days_feb22}"
        assert (
            days_feb22 - days_feb12 >= 9
        ), f"Разница должна быть ~10 дней, получено {days_feb22 - days_feb12}"


class TestTTDPauseAsOfDate:
    """Tests for TTD Pause calculation with as-of-date."""

    def test_ttd_pause_with_as_of_date_for_open_pause(self):
        """Test TTD pause when task is paused before reaching ready status (open interval)."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        base_date = datetime(2025, 2, 1, tzinfo=timezone.utc)

        # Task paused before reaching "Готова к разработке" (open pause)
        history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=base_date,
                end_date=base_date + timedelta(days=2),
            ),
            StatusHistoryEntry(
                status="Аналитика / В работе",
                status_display="Аналитика / В работе",
                start_date=base_date + timedelta(days=2),
                end_date=base_date + timedelta(days=5),
            ),
            StatusHistoryEntry(
                status="Приостановлено",
                status_display="Приостановлено",
                start_date=base_date + timedelta(days=5),
                end_date=None,  # Still paused
            ),
        ]

        # Calculate TTD pause as of Feb 10 (5 days paused)
        as_of_date_feb10 = base_date + timedelta(days=10)
        ttd_pause_feb10 = generator._calculate_ttd_pause(1, history, as_of_date_feb10)

        # Calculate TTD pause as of Feb 20 (15 days paused)
        as_of_date_feb20 = base_date + timedelta(days=20)
        ttd_pause_feb20 = generator._calculate_ttd_pause(1, history, as_of_date_feb20)

        # Assertions
        assert ttd_pause_feb10 is not None, "TTD Pause должен рассчитываться"
        assert ttd_pause_feb20 is not None, "TTD Pause должен рассчитываться"
        assert (
            ttd_pause_feb10 >= 4 and ttd_pause_feb10 <= 6
        ), f"Должно быть ~5 дней, получено {ttd_pause_feb10}"
        assert (
            ttd_pause_feb20 >= 14 and ttd_pause_feb20 <= 16
        ), f"Должно быть ~15 дней, получено {ttd_pause_feb20}"
        assert (
            ttd_pause_feb20 - ttd_pause_feb10 >= 9
        ), f"Разница должна быть ~10 дней, получено {ttd_pause_feb20 - ttd_pause_feb10}"


class TestStatusDurationAsOfDate:
    """Tests for generic calculate_status_duration with as-of-date."""

    def test_status_duration_with_as_of_date_for_open_interval(self):
        """Test status duration for open interval with different as_of_dates."""
        metrics_service = MetricsService()

        base_date = datetime(2025, 2, 1, tzinfo=timezone.utc)

        # Task in specific status (open interval)
        history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=base_date,
                end_date=base_date + timedelta(days=3),
            ),
            StatusHistoryEntry(
                status="Аналитика / В работе",
                status_display="Аналитика / В работе",
                start_date=base_date + timedelta(days=3),
                end_date=None,  # Still in this status
            ),
        ]

        # This test expects calculate_status_duration to accept as_of_date parameter
        # Currently it doesn't, so this test will FAIL
        try:
            # Try to calculate with as_of_date
            duration_feb10 = metrics_service.calculate_status_duration(
                history,
                "Аналитика / В работе",
                as_of_date=base_date + timedelta(days=10),
            )
            duration_feb20 = metrics_service.calculate_status_duration(
                history,
                "Аналитика / В работе",
                as_of_date=base_date + timedelta(days=20),
            )

            assert (
                duration_feb20 > duration_feb10
            ), "Duration должен расти с увеличением as_of_date"
            assert (
                duration_feb20 - duration_feb10 >= 9
            ), f"Разница должна быть ~10 дней, получено {duration_feb20 - duration_feb10}"
        except TypeError as e:
            if "as_of_date" in str(e):
                pytest.fail(
                    "calculate_status_duration не поддерживает as_of_date параметр"
                )
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
