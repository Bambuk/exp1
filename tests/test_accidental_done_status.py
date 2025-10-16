"""Test for accidental done status transitions."""

from datetime import datetime, timedelta

import pytest

from radiator.commands.models.time_to_market_models import StatusHistoryEntry
from radiator.commands.services.metrics_service import MetricsService


class TestAccidentalDoneStatus:
    """Test cases for handling accidental done status transitions."""

    @pytest.fixture
    def metrics_service(self):
        """Create metrics service with 300 second minimum duration."""
        return MetricsService(min_status_duration_seconds=300)

    def _create_entry(self, status: str, start_date: datetime) -> StatusHistoryEntry:
        """Helper to create status history entry."""
        return StatusHistoryEntry(
            status=status,
            status_display=status,
            start_date=start_date,
            end_date=None,
        )

    def test_accidental_done_between_work_statuses(self, metrics_service):
        """
        Test scenario: Task accidentally moved to 'Выполнено с ИТ' for 2 minutes,
        then moved back to work status.

        Expected:
        - TTD should be calculated (has 'Готова к разработке')
        - TTM should NOT be calculated (accidental Done filtered out, no real done status)
        """
        base_date = datetime(2025, 10, 1, 9, 0, 0)

        history = [
            self._create_entry("Discovery Backlog", base_date),
            self._create_entry(
                "Готова к разработке", base_date + timedelta(hours=1)
            ),  # 10:00
            self._create_entry("МП/В работе", base_date + timedelta(hours=2)),  # 11:00
            self._create_entry(
                "Выполнено с ИТ", base_date + timedelta(hours=2, minutes=30)
            ),  # 11:30 - ACCIDENT!
            self._create_entry(
                "МП/Внешний тест", base_date + timedelta(hours=2, minutes=32)
            ),  # 11:32 - fixed
        ]

        done_statuses = [
            "Выполнено с ИТ",
            "Выполнено без ИТ",
            "Done",
            "Закрыт",
            "Раскатано на всех",
            "Выпилено",
        ]

        # Check filtered history
        filtered = metrics_service._filter_short_status_transitions(history)
        filtered_statuses = [entry.status for entry in filtered]

        # "Выполнено с ИТ" should be filtered out (only 2 minutes)
        assert "Выполнено с ИТ" not in filtered_statuses, (
            f"Accidental 'Выполнено с ИТ' should be filtered out. "
            f"Filtered statuses: {filtered_statuses}"
        )

        # TTD should be calculated (has 'Готова к разработке')
        ttd = metrics_service.calculate_time_to_delivery(history, [])
        assert ttd is not None, "TTD should be calculated"
        assert ttd == 0, "TTD should be 0 days (same day)"

        # TTM should NOT be calculated (no real done status after filtering)
        ttm = metrics_service.calculate_time_to_market(history, done_statuses)
        assert ttm is None, (
            "TTM should NOT be calculated because accidental Done was filtered out. "
            f"Got TTM={ttm}"
        )

    def test_real_done_after_accidental_done(self, metrics_service):
        """
        Test scenario: Accidental done, then fixed, then real done.

        Expected:
        - TTM should be calculated to the REAL done status (not accidental)
        """
        base_date = datetime(2025, 10, 1)

        history = [
            self._create_entry("Discovery Backlog", base_date),
            self._create_entry("Готова к разработке", base_date + timedelta(days=1)),
            self._create_entry("МП/В работе", base_date + timedelta(days=2)),
            # Accidental done for 2 minutes
            self._create_entry("Done", base_date + timedelta(days=3, minutes=0)),
            self._create_entry("МП/В работе", base_date + timedelta(days=3, minutes=2)),
            # Real done
            self._create_entry("Done", base_date + timedelta(days=10)),
        ]

        done_statuses = ["Done"]

        # Check filtered history
        filtered = metrics_service._filter_short_status_transitions(history)
        done_entries = [e for e in filtered if e.status == "Done"]

        # Should only have one Done (the real one)
        assert (
            len(done_entries) == 1
        ), f"Should have only 1 Done after filtering, got {len(done_entries)}"
        assert done_entries[0].start_date == base_date + timedelta(days=10)

        # TTM should be calculated to the real Done
        ttm = metrics_service.calculate_time_to_market(history, done_statuses)
        assert ttm == 10, f"TTM should be 10 days (to real Done), got {ttm}"

    def test_long_accidental_done_not_filtered(self, metrics_service):
        """
        Test scenario: Task in Done for 10 minutes (> 5 min threshold).

        Expected:
        - Done status NOT filtered (duration > threshold)
        - TTM calculated to this Done (even though it was corrected later)
        """
        base_date = datetime(2025, 10, 1, 9, 0, 0)

        history = [
            self._create_entry("Discovery Backlog", base_date),
            self._create_entry("Готова к разработке", base_date + timedelta(hours=1)),
            self._create_entry("Done", base_date + timedelta(hours=2)),  # 11:00
            # Stayed in Done for 10 minutes (> 5 min threshold)
            self._create_entry(
                "МП/В работе", base_date + timedelta(hours=2, minutes=10)
            ),  # 11:10
        ]

        done_statuses = ["Done"]

        # Check filtered history
        filtered = metrics_service._filter_short_status_transitions(history)
        filtered_statuses = [entry.status for entry in filtered]

        # Done should NOT be filtered (10 minutes > 5 minutes threshold)
        assert "Done" in filtered_statuses, (
            "Done with 10 min duration should NOT be filtered. "
            f"Filtered statuses: {filtered_statuses}"
        )

        # TTM should be calculated to this Done
        ttm = metrics_service.calculate_time_to_market(history, done_statuses)
        assert ttm is not None, "TTM should be calculated (Done duration > threshold)"

    def test_no_done_status_in_history(self, metrics_service):
        """
        Test scenario: Task never reached done status.

        Expected:
        - TTD calculated
        - TTM NOT calculated
        """
        base_date = datetime(2025, 10, 1)

        history = [
            self._create_entry("Discovery Backlog", base_date),
            self._create_entry("Готова к разработке", base_date + timedelta(days=1)),
            self._create_entry("МП/В работе", base_date + timedelta(days=2)),
            self._create_entry("МП/Внешний тест", base_date + timedelta(days=5)),
        ]

        done_statuses = ["Done", "Выполнено с ИТ"]

        # TTD should be calculated
        ttd = metrics_service.calculate_time_to_delivery(history, [])
        assert ttd is not None, "TTD should be calculated"
        assert ttd == 1, f"TTD should be 1 day, got {ttd}"

        # TTM should NOT be calculated
        ttm = metrics_service.calculate_time_to_market(history, done_statuses)
        assert ttm is None, "TTM should NOT be calculated (no done status)"
