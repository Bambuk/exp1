"""Tests for datetime_utils module."""

from datetime import datetime, timezone

import pytest

from radiator.commands.services.datetime_utils import normalize_to_utc


class TestDatetimeUtils:
    """Tests for datetime utility functions."""

    def test_normalize_to_utc_handles_naive(self):
        """Test that naive datetime is normalized to UTC."""
        naive_dt = datetime(2025, 2, 10, 12, 30)
        result = normalize_to_utc(naive_dt)

        assert result.tzinfo == timezone.utc
        assert result.year == 2025
        assert result.month == 2
        assert result.day == 10
        assert result.hour == 12
        assert result.minute == 30

    def test_normalize_to_utc_handles_aware(self):
        """Test that timezone-aware datetime is preserved."""
        aware_dt = datetime(2025, 2, 10, 12, 30, tzinfo=timezone.utc)
        result = normalize_to_utc(aware_dt)

        assert result == aware_dt
        assert result.tzinfo == timezone.utc

    def test_normalize_to_utc_handles_none(self):
        """Test that None is handled correctly."""
        result = normalize_to_utc(None)

        assert result is None

    def test_normalize_to_utc_converts_non_utc_to_utc(self):
        """Test that non-UTC timezone is converted to UTC."""
        from datetime import timedelta

        # Create datetime with +3 hours offset
        tz_plus3 = timezone(timedelta(hours=3))
        dt_plus3 = datetime(2025, 2, 10, 15, 30, tzinfo=tz_plus3)

        result = normalize_to_utc(dt_plus3)

        assert result.tzinfo == timezone.utc
        # 15:30+03:00 should be 12:30 UTC
        assert result.hour == 12
        assert result.minute == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
