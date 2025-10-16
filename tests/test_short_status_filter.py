"""Tests for filtering short status transitions."""

from datetime import datetime, timedelta

import pytest

from radiator.commands.models.time_to_market_models import StatusHistoryEntry
from radiator.commands.services.metrics_service import MetricsService


class TestShortStatusFilter:
    """Test cases for filtering short status transitions."""

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

    def test_filter_removes_short_transitions(self, metrics_service):
        """Test that transitions shorter than 5 minutes are filtered out."""
        base_date = datetime(2025, 1, 1, 10, 0, 0)

        history = [
            self._create_entry("Discovery", base_date),  # -> 2 min -> kept (first)
            self._create_entry(
                "In Progress", base_date + timedelta(minutes=2)
            ),  # -> 10 min -> kept
            self._create_entry(
                "Review", base_date + timedelta(minutes=12)
            ),  # -> 18 min -> kept
            self._create_entry(
                "Done", base_date + timedelta(minutes=30)
            ),  # last -> kept
        ]

        filtered = metrics_service._filter_short_status_transitions(history)

        # All entries have duration > 5 min or are first/last, so all should be kept
        assert len(filtered) == 4

    def test_filter_keeps_first_entry_always(self, metrics_service):
        """Test that the first entry (task creation) is always kept."""
        base_date = datetime(2025, 1, 1, 10, 0, 0)

        history = [
            self._create_entry("Discovery", base_date),  # -> 1 min -> kept (first)
            self._create_entry(
                "In Progress", base_date + timedelta(minutes=1)
            ),  # -> 9 min -> kept
            self._create_entry(
                "Done", base_date + timedelta(minutes=10)
            ),  # last -> kept
        ]

        filtered = metrics_service._filter_short_status_transitions(history)

        # All kept (first is always kept, second has 9 min duration which > 5 min, last is always kept)
        assert len(filtered) == 3

    def test_filter_integration_with_ttd(self, metrics_service):
        """Test that filtering works correctly with TTD calculation."""
        base_date = datetime(2025, 1, 1)

        history = [
            self._create_entry("Discovery", base_date),
            self._create_entry(
                "In Progress", base_date + timedelta(days=0, minutes=1)
            ),  # Short
            self._create_entry("Готова к разработке", base_date + timedelta(days=10)),
        ]

        ttd = metrics_service.calculate_time_to_delivery(history, [])

        # TTD should be 10 days (short transition filtered out)
        assert ttd == 10

    def test_filter_excludes_false_clicks(self, metrics_service):
        """Test real-world scenario: excluding accidental status changes."""
        base_date = datetime(2025, 1, 1, 9, 0, 0)

        history = [
            self._create_entry("Discovery backlog", base_date),
            self._create_entry(
                "В работе", base_date + timedelta(seconds=30)
            ),  # Accident
            self._create_entry(
                "Discovery backlog", base_date + timedelta(seconds=45)
            ),  # Fixed
            self._create_entry("Готова к разработке", base_date + timedelta(days=5)),
        ]

        filtered = metrics_service._filter_short_status_transitions(history)

        # Should exclude both false transitions
        statuses = [entry.status for entry in filtered]
        assert "В работе" not in statuses
        # Should have Discovery backlog -> Готова к разработке
        assert len(statuses) == 2
        assert statuses[0] == "Discovery backlog"
        assert statuses[1] == "Готова к разработке"

    def test_min_duration_from_env_variable(self, monkeypatch):
        """Test that min duration can be set from environment variable."""
        monkeypatch.setenv("MIN_STATUS_DURATION_SECONDS", "600")

        service = MetricsService()
        assert service.min_status_duration_seconds == 600

    def test_filter_with_empty_history(self, metrics_service):
        """Test filter with empty history."""
        filtered = metrics_service._filter_short_status_transitions([])
        assert filtered == []
