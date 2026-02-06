"""History filter service for filtering task history by as-of-date."""

from datetime import datetime, timezone
from typing import List

from radiator.commands.models.time_to_market_models import StatusHistoryEntry


class HistoryFilter:
    """Service for filtering task history by as-of-date."""

    @staticmethod
    def filter_by_as_of_date(
        history: List[StatusHistoryEntry], as_of_date: datetime
    ) -> List[StatusHistoryEntry]:
        """
        Filter history entries by as-of-date.

        Rules:
        1. Drop entries where start_date > as_of_date
        2. Set end_date = None if end_date > as_of_date
        3. Normalize all datetimes to UTC timezone-aware
        4. Create new instances to avoid modifying originals

        Args:
            history: List of StatusHistoryEntry objects
            as_of_date: The date to filter by

        Returns:
            Filtered list of StatusHistoryEntry objects
        """
        if not history:
            return []

        # Normalize as_of_date to UTC
        as_of_date_utc = HistoryFilter._normalize_to_utc(as_of_date)

        filtered = []

        for entry in history:
            # Normalize entry dates to UTC
            start_date_utc = HistoryFilter._normalize_to_utc(entry.start_date)
            end_date_utc = (
                HistoryFilter._normalize_to_utc(entry.end_date)
                if entry.end_date
                else None
            )

            # Drop entries that start after as_of_date
            if start_date_utc > as_of_date_utc:
                continue

            # Truncate end_date if it's after as_of_date
            if end_date_utc and end_date_utc > as_of_date_utc:
                end_date_utc = None

            # Create new instance to avoid modifying original
            filtered_entry = StatusHistoryEntry(
                status=entry.status,
                status_display=entry.status_display,
                start_date=start_date_utc,
                end_date=end_date_utc,
            )

            filtered.append(filtered_entry)

        return filtered

    @staticmethod
    def _normalize_to_utc(dt: datetime) -> datetime:
        """
        Normalize datetime to UTC timezone-aware.

        Args:
            dt: Datetime to normalize

        Returns:
            Timezone-aware datetime in UTC
        """
        if dt is None:
            return None

        if dt.tzinfo is None:
            # Naive datetime - assume UTC
            return dt.replace(tzinfo=timezone.utc)

        # Already timezone-aware - convert to UTC
        return dt.astimezone(timezone.utc)
