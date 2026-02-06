"""Utility functions for datetime handling and timezone normalization."""

from datetime import datetime, timezone
from typing import Optional


def normalize_to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Normalize datetime to UTC timezone-aware.

    Handles:
    - None values (returns None)
    - Naive datetimes (assumes UTC and adds timezone info)
    - Timezone-aware datetimes (converts to UTC)

    Args:
        dt: Datetime to normalize (can be None, naive, or timezone-aware)

    Returns:
        Timezone-aware datetime in UTC, or None if input was None

    Examples:
        >>> naive = datetime(2025, 2, 10, 12, 30)
        >>> result = normalize_to_utc(naive)
        >>> result.tzinfo == timezone.utc
        True

        >>> aware = datetime(2025, 2, 10, 12, 30, tzinfo=timezone.utc)
        >>> result = normalize_to_utc(aware)
        >>> result == aware
        True

        >>> result = normalize_to_utc(None)
        >>> result is None
        True
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        # Naive datetime - assume UTC
        return dt.replace(tzinfo=timezone.utc)

    # Already timezone-aware - convert to UTC
    return dt.astimezone(timezone.utc)
