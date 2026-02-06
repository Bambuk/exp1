"""Tests for DevLT calculation with as-of-date for unfinished tasks.

These tests verify that DevLT is calculated correctly when using as-of-date
for tasks that are still in work (open "МП / В работе" status).
"""

from datetime import datetime, timedelta, timezone

import pytest

from radiator.commands.models.time_to_market_models import StatusHistoryEntry
from radiator.commands.services.metrics_service import MetricsService


class TestDevLTAsOfDate:
    """Tests for DevLT calculation with as-of-date."""

    def test_calculate_dev_lead_time_with_as_of_date_for_open_work_status(self):
        """Test DevLT calculation with as-of-date for task still in work."""
        metrics_service = MetricsService()

        base_date = datetime(2025, 2, 1, tzinfo=timezone.utc)

        # Task started work on Feb 1, still in work (no end_date)
        history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=base_date,
                end_date=base_date + timedelta(days=1),
            ),
            StatusHistoryEntry(
                status="МП / В работе",
                status_display="МП / В работе",
                start_date=base_date + timedelta(days=1),
                end_date=None,  # Still in work
            ),
        ]

        # Calculate DevLT as of Feb 10 (9 days after work started)
        as_of_date = base_date + timedelta(days=9)
        devlt = metrics_service.calculate_dev_lead_time(history, as_of_date=as_of_date)

        # DevLT should be approximately 8 days (from Feb 2 to Feb 10)
        assert devlt is not None
        assert devlt >= 7 and devlt <= 9

    def test_calculate_dev_lead_time_with_as_of_date_vs_current_date(self):
        """Test that DevLT differs when calculated with as-of-date vs current date."""
        metrics_service = MetricsService()

        base_date = datetime(2025, 2, 1, tzinfo=timezone.utc)

        # Task started work on Feb 1, still in work
        history = [
            StatusHistoryEntry(
                status="МП / В работе",
                status_display="МП / В работе",
                start_date=base_date,
                end_date=None,
            ),
        ]

        # Calculate DevLT as of Feb 10
        as_of_date_feb10 = base_date + timedelta(days=9)
        devlt_feb10 = metrics_service.calculate_dev_lead_time(
            history, as_of_date=as_of_date_feb10
        )

        # Calculate DevLT as of Feb 20
        as_of_date_feb20 = base_date + timedelta(days=19)
        devlt_feb20 = metrics_service.calculate_dev_lead_time(
            history, as_of_date=as_of_date_feb20
        )

        # DevLT should increase by 10 days
        assert devlt_feb10 is not None
        assert devlt_feb20 is not None
        assert devlt_feb20 - devlt_feb10 >= 9
        assert devlt_feb20 - devlt_feb10 <= 11

    def test_calculate_dev_lead_time_without_as_of_date_uses_current_date(self):
        """Test that DevLT without as-of-date uses current date (backward compatible)."""
        metrics_service = MetricsService()

        base_date = datetime(2025, 2, 1, tzinfo=timezone.utc)

        # Task started work recently
        history = [
            StatusHistoryEntry(
                status="МП / В работе",
                status_display="МП / В работе",
                start_date=base_date,
                end_date=None,
            ),
        ]

        # Calculate DevLT without as_of_date (should use current date)
        devlt = metrics_service.calculate_dev_lead_time(history)

        # Should return a value based on current date
        assert devlt is not None
        # Should be approximately days from Feb 1, 2025 to now (2026-02-06)
        # That's about 370 days
        assert devlt > 300

    def test_calculate_dev_lead_time_completed_task_ignores_as_of_date(self):
        """Test that completed tasks ignore as-of-date (DevLT already fixed)."""
        metrics_service = MetricsService()

        base_date = datetime(2025, 2, 1, tzinfo=timezone.utc)

        # Completed task - work and external test both closed
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
                end_date=base_date + timedelta(days=15),
            ),
        ]

        # Calculate DevLT with different as_of_dates
        devlt_feb10 = metrics_service.calculate_dev_lead_time(
            history, as_of_date=base_date + timedelta(days=9)
        )
        devlt_feb20 = metrics_service.calculate_dev_lead_time(
            history, as_of_date=base_date + timedelta(days=19)
        )

        # Both should return same DevLT (10 days) because task is completed
        assert devlt_feb10 == 10
        assert devlt_feb20 == 10

    def test_ttm_details_report_devlt_propagates_as_of_date(self, test_reports_dir):
        """Test that TTMDetailsReportGenerator propagates as_of_date to DevLT calculation."""
        from unittest.mock import Mock, patch

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        base_date = datetime(2025, 2, 1, tzinfo=timezone.utc)
        as_of_date = base_date + timedelta(days=10)

        # Mock history for task in work
        mock_history = [
            StatusHistoryEntry(
                status="МП / В работе",
                status_display="МП / В работе",
                start_date=base_date,
                end_date=None,
            ),
        ]

        # Mock MetricsService to verify as_of_date is passed
        with patch.object(
            generator.metrics_service, "calculate_dev_lead_time", return_value=10
        ) as mock_calculate:
            # Call _calculate_devlt with as_of_date
            result = generator._calculate_devlt(1, mock_history, as_of_date=as_of_date)

            # Verify calculate_dev_lead_time was called with as_of_date
            mock_calculate.assert_called_once()
            call_args = mock_calculate.call_args

            # Check that as_of_date was passed as keyword argument
            assert "as_of_date" in call_args.kwargs
            assert call_args.kwargs["as_of_date"] == as_of_date


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
