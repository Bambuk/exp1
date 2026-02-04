"""Metrics calculation service for Time To Market report."""

import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Protocol

import numpy as np

from radiator.commands.models.time_to_market_models import (
    GroupMetrics,
    StatusHistoryEntry,
    StatusMapping,
    TaskData,
    TimeMetrics,
)
from radiator.commands.services.config_service import ConfigService
from radiator.core.logging import logger


class StartDateStrategy(Protocol):
    """Protocol for start date calculation strategies."""

    def calculate_start_date(
        self, history_data: List[StatusHistoryEntry]
    ) -> Optional[datetime]:
        """
        Calculate start date for time metrics.

        Args:
            history_data: List of status history entries

        Returns:
            Start date or None if not found
        """


class CreationDateStrategy:
    """Strategy: Use task creation date as start date."""

    def calculate_start_date(
        self, history_data: List[StatusHistoryEntry]
    ) -> Optional[datetime]:
        """Use the earliest date in history as start date."""
        if not history_data:
            return None
        return min(entry.start_date for entry in history_data)


class FirstChangeStrategy:
    """Strategy: Use task creation date as start date (first entry in history)."""

    def calculate_start_date(
        self, history_data: List[StatusHistoryEntry]
    ) -> Optional[datetime]:
        """Use task creation date as start date (first entry in history)."""
        if not history_data:
            return None

        # Sort history by date
        sorted_history = sorted(history_data, key=lambda x: x.start_date)

        # Use the earliest date in history as the start date (task creation)
        return sorted_history[0].start_date


class ReadyForDevelopmentStrategy:
    """Strategy: Use first status change after creation as start date, but find 'Готова к разработке' as target."""

    def calculate_start_date(
        self, history_data: List[StatusHistoryEntry]
    ) -> Optional[datetime]:
        """Use first status change after creation as start date."""
        if not history_data:
            return None

        # Sort history by date
        sorted_history = sorted(history_data, key=lambda x: x.start_date)
        creation_date = sorted_history[0].start_date

        # Find first status change after creation
        for entry in sorted_history[1:]:  # Skip first entry (creation)
            if entry.start_date > creation_date:
                return entry.start_date

        # If no status change after creation, use creation date
        return creation_date


class MetricsService:
    """Service for calculating time metrics."""

    def __init__(
        self,
        ttd_strategy: StartDateStrategy = None,
        ttm_strategy: StartDateStrategy = None,
        min_status_duration_seconds: int = None,
        config_dir: str = None,
    ):
        """
        Initialize metrics service with strategies.

        Args:
            ttd_strategy: Strategy for TTD start date calculation
            ttm_strategy: Strategy for TTM start date calculation
            min_status_duration_seconds: Minimum time in status (seconds) to consider valid
            config_dir: Configuration directory path for loading status order (optional)
        """
        self.ttd_strategy = ttd_strategy or FirstChangeStrategy()
        self.ttm_strategy = ttm_strategy or FirstChangeStrategy()
        self.pause_status = "Приостановлено"  # Status that indicates pause

        # Get min status duration from parameter or environment variable
        if min_status_duration_seconds is not None:
            self.min_status_duration_seconds = min_status_duration_seconds
        else:
            self.min_status_duration_seconds = int(
                os.getenv("MIN_STATUS_DURATION_SECONDS", "300")
            )

        # Initialize ConfigService if config_dir is provided
        self.config_service = ConfigService(config_dir) if config_dir else None

    def _filter_short_status_transitions(
        self, history_data: List[StatusHistoryEntry]
    ) -> List[StatusHistoryEntry]:
        """
        Filter out status transitions where task spent less than minimum duration.
        This excludes false transitions caused by accidental clicks or errors.

        Args:
            history_data: List of status history entries

        Returns:
            Filtered list with only valid status transitions
        """
        if not history_data or self.min_status_duration_seconds <= 0:
            return history_data

        try:
            sorted_history = sorted(history_data, key=lambda x: x.start_date)
            filtered_history = []

            for i, entry in enumerate(sorted_history):
                # Always keep the first entry (task creation)
                if i == 0:
                    filtered_history.append(entry)
                    continue

                # Check if we have a next entry to calculate duration
                if i + 1 < len(sorted_history):
                    next_entry = sorted_history[i + 1]
                    # Calculate duration in seconds until next status change
                    duration_seconds = (
                        next_entry.start_date - entry.start_date
                    ).total_seconds()

                    # Keep only if duration meets minimum threshold
                    if duration_seconds >= self.min_status_duration_seconds:
                        filtered_history.append(entry)
                    else:
                        logger.debug(
                            f"Filtered out short transition: {entry.status} "
                            f"(duration: {duration_seconds:.0f}s < {self.min_status_duration_seconds}s)"
                        )
                else:
                    # This is the last status - always keep it
                    filtered_history.append(entry)

            # Remove consecutive duplicates after filtering
            final_history = []
            for i, entry in enumerate(filtered_history):
                if i == 0 or entry.status != filtered_history[i - 1].status:
                    final_history.append(entry)

            if len(final_history) != len(history_data):
                logger.debug(
                    f"Filtered history: {len(history_data)} -> {len(final_history)} entries "
                    f"(min duration: {self.min_status_duration_seconds}s)"
                )

            return final_history

        except Exception as e:
            logger.warning(f"Failed to filter short status transitions: {e}")
            return history_data

    def calculate_pause_time(self, history_data: List[StatusHistoryEntry]) -> int:
        """
        Calculate total time spent in pause status.

        Args:
            history_data: List of status history entries

        Returns:
            Total days spent in pause status
        """
        if not history_data:
            return 0

        try:
            total_pause_time = 0
            sorted_history = sorted(history_data, key=lambda x: x.start_date)

            for i, entry in enumerate(sorted_history):
                if entry.status == self.pause_status:
                    # Find the next status change to calculate pause duration
                    next_entry = None
                    for j in range(i + 1, len(sorted_history)):
                        if sorted_history[j].status != self.pause_status:
                            next_entry = sorted_history[j]
                            break

                    if next_entry:
                        pause_duration = (next_entry.start_date - entry.start_date).days
                        total_pause_time += max(0, pause_duration)

            return total_pause_time

        except Exception as e:
            logger.warning(f"Failed to calculate pause time: {e}")
            return 0

    def calculate_pause_time_up_to_date(
        self, history_data: List[StatusHistoryEntry], end_date: datetime
    ) -> int:
        """
        Calculate time spent in pause status up to a specific date.

        Args:
            history_data: List of status history entries
            end_date: Date to calculate pause time up to

        Returns:
            Total days spent in pause status up to end_date
        """
        if not history_data:
            return 0

        try:
            from datetime import timezone

            # Нормализуем end_date к timezone-aware (UTC) если он naive
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)

            total_pause_time = 0
            sorted_history = sorted(history_data, key=lambda x: x.start_date)

            for i, entry in enumerate(sorted_history):
                # Нормализуем entry.start_date к timezone-aware (UTC) если он naive
                entry_start = entry.start_date
                if entry_start.tzinfo is None:
                    entry_start = entry_start.replace(tzinfo=timezone.utc)

                if entry.status == self.pause_status and entry_start < end_date:
                    # Find the next status change to calculate pause duration
                    next_entry = None
                    for j in range(i + 1, len(sorted_history)):
                        if sorted_history[j].status != self.pause_status:
                            next_entry = sorted_history[j]
                            break

                    if next_entry:
                        # Нормализуем next_entry.start_date к timezone-aware (UTC) если он naive
                        next_start = next_entry.start_date
                        if next_start.tzinfo is None:
                            next_start = next_start.replace(tzinfo=timezone.utc)

                        if next_start <= end_date:
                            pause_duration = (next_start - entry_start).days
                            total_pause_time += max(0, pause_duration)
                        else:
                            # Pause period extends beyond end_date, calculate up to end_date
                            pause_duration = (end_date - entry_start).days
                            total_pause_time += max(0, pause_duration)
                    else:
                        # No next entry, calculate up to end_date
                        pause_duration = (end_date - entry_start).days
                        total_pause_time += max(0, pause_duration)

            return total_pause_time

        except Exception as e:
            logger.warning(f"Failed to calculate pause time up to date: {e}")
            return 0

    def calculate_pause_time_between_dates(
        self,
        history_data: List[StatusHistoryEntry],
        start_date: datetime,
        end_date: datetime,
    ) -> int:
        """
        Calculate time spent in pause status between two specific dates.

        Args:
            history_data: List of status history entries
            start_date: Start date for calculation
            end_date: End date for calculation

        Returns:
            Total days spent in pause status between start_date and end_date
        """
        if not history_data:
            return 0

        try:
            total_pause_time = 0
            sorted_history = sorted(history_data, key=lambda x: x.start_date)

            for i, entry in enumerate(sorted_history):
                if entry.status == self.pause_status:
                    # Find the next status change to get actual pause end
                    next_entry = None
                    for j in range(i + 1, len(sorted_history)):
                        if sorted_history[j].status != self.pause_status:
                            next_entry = sorted_history[j]
                            break

                    # Determine the actual pause period
                    pause_start = entry.start_date
                    if next_entry:
                        pause_end = next_entry.start_date
                    else:
                        # Pause continues to the end, use end_date as limit
                        pause_end = end_date

                    # Check if pause period overlaps with our date range
                    overlap_start = max(pause_start, start_date)
                    overlap_end = min(pause_end, end_date)

                    if overlap_start < overlap_end:
                        pause_duration = (overlap_end - overlap_start).days
                        total_pause_time += max(0, pause_duration)

            return total_pause_time

        except Exception as e:
            logger.warning(f"Failed to calculate pause time between dates: {e}")
            return 0

    def calculate_time_to_delivery(
        self, history_data: List[StatusHistoryEntry], target_statuses: List[str]
    ) -> Optional[int]:
        """
        Calculate Time To Delivery using configured strategy, excluding pause time.
        Filters out short status transitions (< min_status_duration_seconds).

        Args:
            history_data: List of status history entries
            target_statuses: List of discovery status names (ignored, we look for 'Готова к разработке')

        Returns:
            Number of days or None if not found
        """
        try:
            if not history_data:
                return None

            # History is already filtered at DataService level
            # Get start date using TTD strategy
            start_date = self.ttd_strategy.calculate_start_date(history_data)
            if start_date is None:
                return None

            # Find 'Готова к разработке' status specifically
            target_entry = None
            for entry in sorted(history_data, key=lambda x: x.start_date):
                if entry.status == "Готова к разработке":
                    target_entry = entry
                    break

            if not target_entry:
                return None

            # Calculate pause time only up to the target status
            pause_time = self.calculate_pause_time_up_to_date(
                history_data, target_entry.start_date
            )
            total_days = (target_entry.start_date - start_date).days
            effective_days = total_days - pause_time
            return max(0, effective_days)  # Ensure non-negative

        except Exception as e:
            logger.warning(f"Failed to calculate Time To Delivery: {e}")
            return None

    def calculate_time_to_market(
        self, history_data: List[StatusHistoryEntry], target_statuses: List[str]
    ) -> Optional[int]:
        """
        Calculate Time To Market using configured strategy, excluding pause time.
        Filters out short status transitions (< min_status_duration_seconds).

        Args:
            history_data: List of status history entries
            target_statuses: List of done status names

        Returns:
            Number of days or None if not found
        """
        try:
            if not history_data:
                return None

            # History is already filtered at DataService level
            # Get start date using TTM strategy
            start_date = self.ttm_strategy.calculate_start_date(history_data)
            if start_date is None:
                return None

            # Find stable done status (last stable done, or first if all unstable)
            target_entry = self._find_stable_done(history_data, target_statuses)

            if not target_entry:
                return None

            # Calculate pause time only up to the target status
            pause_time = self.calculate_pause_time_up_to_date(
                history_data, target_entry.start_date
            )
            total_days = (target_entry.start_date - start_date).days
            effective_days = total_days - pause_time
            return max(0, effective_days)  # Ensure non-negative

        except Exception as e:
            logger.warning(f"Failed to calculate Time To Market: {e}")
            return None

    def _find_stable_done(
        self, history_data: List[StatusHistoryEntry], target_statuses: List[str]
    ) -> Optional[StatusHistoryEntry]:
        """
        Find the last stable done status - one after which task didn't return to work.

        Args:
            history_data: List of status history entries
            target_statuses: List of done status names

        Returns:
            Last stable done entry or first done if all are unstable
        """
        try:
            if not history_data:
                return None

            # Filter out short status transitions first
            filtered_history = self._filter_short_status_transitions(history_data)
            if not filtered_history:
                return None

            # Sort history by date
            sorted_history = sorted(filtered_history, key=lambda x: x.start_date)

            # Find all done statuses
            done_entries = [
                entry for entry in sorted_history if entry.status in target_statuses
            ]
            if not done_entries:
                return None

            # If only one done, return it
            if len(done_entries) == 1:
                return done_entries[0]

            # Check each done status for stability (from last to first)
            for i in range(len(done_entries) - 1, -1, -1):
                done_entry = done_entries[i]
                # Find the position of this done in sorted history
                done_index = sorted_history.index(done_entry)

                # Check if there are any non-done, non-pause statuses after this done
                is_stable = True
                for j in range(done_index + 1, len(sorted_history)):
                    next_entry = sorted_history[j]

                    # If next status is done or pause, it's still stable
                    if (
                        next_entry.status in target_statuses
                        or next_entry.status == "Приостановлено"
                    ):
                        continue

                    # If next status is not-done (backlog/discovery/delivery), it's unstable
                    is_stable = False
                    break

                # If this done is stable, return it (it's the last stable one)
                if is_stable:
                    return done_entry

            # If we get here, all done statuses are unstable, return the first one
            return done_entries[0]

        except Exception as e:
            logger.warning(f"Failed to find stable done: {e}")
            # Fallback to first done
            return done_entries[0] if done_entries else None

    def calculate_tail_metric(
        self, history_data: List[StatusHistoryEntry], done_statuses: List[str]
    ) -> Optional[int]:
        """
        Calculate Tail metric: days from exiting 'МП / Внешний тест' status to any done status.
        Filters out short status transitions (< min_status_duration_seconds).

        Args:
            history_data: List of status history entries
            done_statuses: List of done status names

        Returns:
            Number of days or None if not found
        """
        try:
            if not history_data:
                return None

            # Filter out short status transitions
            filtered_history = self._filter_short_status_transitions(history_data)
            if not filtered_history:
                return None

            # Sort history by date
            sorted_history = sorted(filtered_history, key=lambda x: x.start_date)

            # Find all "МП / Внешний тест" entries
            mp_entries = [e for e in sorted_history if e.status == "МП / Внешний тест"]
            if not mp_entries:
                return None

            # Filter to find long duration entries (> 5 minutes)
            valid_mp_entries = []
            for entry in mp_entries:
                if entry.end_date is None:
                    # Open interval - consider as long duration
                    valid_mp_entries.append(entry)
                else:
                    duration = (entry.end_date - entry.start_date).total_seconds()
                    if duration >= self.min_status_duration_seconds:
                        valid_mp_entries.append(entry)

            if not valid_mp_entries:
                return None

            # Find last valid "МП / Внешний тест" (by start_date)
            last_mp_entry = max(valid_mp_entries, key=lambda x: x.start_date)

            # Find first done status after the MP/External Test status
            done_entry = None
            for entry in sorted_history:
                if (
                    entry.start_date > last_mp_entry.start_date
                    and entry.status in done_statuses
                ):
                    done_entry = entry
                    break

            if not done_entry:
                return None

            # Calculate pause time between MP/External Test start and done status
            pause_time = self.calculate_pause_time_between_dates(
                filtered_history, last_mp_entry.start_date, done_entry.start_date
            )

            total_days = (done_entry.start_date - last_mp_entry.start_date).days
            effective_days = total_days - pause_time
            return max(0, effective_days)  # Ensure non-negative

        except Exception as e:
            logger.warning(f"Failed to calculate Tail metric: {e}")
            return None

    def calculate_status_duration(
        self, history_data: List[StatusHistoryEntry], target_status: str
    ) -> int:
        """
        Calculate total time spent in a specific status.
        Filters out short status transitions (< min_status_duration_seconds).

        Args:
            history_data: List of status history entries
            target_status: Status name to calculate duration for

        Returns:
            Total days spent in the target status
        """
        if not history_data:
            return 0

        try:
            # Filter out short status transitions
            filtered_history = self._filter_short_status_transitions(history_data)
            if not filtered_history:
                return 0

            total_duration = 0
            sorted_history = sorted(filtered_history, key=lambda x: x.start_date)

            for i, entry in enumerate(filtered_history):
                if entry.status == target_status:
                    # Find the next status change to calculate duration
                    next_entry = None
                    for j in range(i + 1, len(filtered_history)):
                        if filtered_history[j].status != target_status:
                            next_entry = filtered_history[j]
                            break

                    if next_entry:
                        duration = (next_entry.start_date - entry.start_date).days
                        total_duration += max(0, duration)  # Ensure non-negative
                    # If no next entry, this is the last status - no duration to calculate

            return total_duration

        except Exception as e:
            logger.warning(
                f"Failed to calculate status duration for {target_status}: {e}"
            )
            return 0

    def calculate_dev_lead_time(
        self, history_data: List[StatusHistoryEntry]
    ) -> Optional[int]:
        """
        Calculate Development Lead Time: time from first "МП / В работе" with duration > 5 min
        to last "МП / Внешний тест" with duration > 5 min.
        If no valid "МП / Внешний тест" entries found, falls back to first valid subsequent status
        (statuses after "МП / Внешний тест" in status_order.txt).
        Filters out short status transitions (< min_status_duration_seconds).
        Does NOT exclude pause time (calendar time).

        Args:
            history_data: List of status history entries

        Returns:
            Number of days or None if start status not found or no valid end status found
        """
        try:
            if not history_data:
                return None

            # Sort history by date
            sorted_history = sorted(history_data, key=lambda x: x.start_date)

            # Find all "МП / В работе" and "МП / Внешний тест" entries
            work_entries = [e for e in sorted_history if e.status == "МП / В работе"]
            external_test_entries = [
                e for e in sorted_history if e.status == "МП / Внешний тест"
            ]

            if not work_entries:
                return None

            # Filter "МП / В работе" entries: must have end_date and duration > 5 minutes
            valid_work_entries = []
            for entry in work_entries:
                if entry.end_date is None:
                    continue  # Skip open intervals (work not completed)

                duration = (entry.end_date - entry.start_date).total_seconds()
                if duration >= self.min_status_duration_seconds:
                    valid_work_entries.append(entry)

            # Filter "МП / Внешний тест" entries: duration > 5 minutes (end_date optional)
            valid_external_test_entries = []
            for entry in external_test_entries:
                if entry.end_date is None:
                    # Open interval - consider as long duration
                    valid_external_test_entries.append(entry)
                else:
                    duration = (entry.end_date - entry.start_date).total_seconds()
                    if duration >= self.min_status_duration_seconds:
                        valid_external_test_entries.append(entry)

            # If no valid closed "МП / В работе" entries, check for open intervals (fallback)
            if not valid_work_entries:
                # Fallback: if task is still in "МП / В работе" (open interval)
                # and standard algorithm couldn't calculate DevLT, use current date
                open_work_entries = [
                    e
                    for e in work_entries
                    if e.end_date is None and e.status == "МП / В работе"
                ]

                if open_work_entries:
                    # Find first open "МП / В работе" entry
                    first_open_work_entry = min(
                        open_work_entries, key=lambda x: x.start_date
                    )

                    # Calculate days to current date (UTC)
                    from datetime import timezone

                    current_date = datetime.now(timezone.utc)

                    # Normalize start_date to UTC if needed
                    work_start = first_open_work_entry.start_date
                    if work_start.tzinfo is None:
                        work_start = work_start.replace(tzinfo=timezone.utc)

                    total_days = (current_date - work_start).days
                    return max(0, total_days)  # Ensure non-negative

                return None

            # Find first valid "МП / В работе" (by start_date)
            first_work_entry = min(valid_work_entries, key=lambda x: x.start_date)

            # Try to use valid "МП / Внешний тест" entries first
            if valid_external_test_entries:
                # Find last valid "МП / Внешний тест" (by start_date)
                last_external_test_entry = max(
                    valid_external_test_entries, key=lambda x: x.start_date
                )

                # Calculate calendar days (no pause exclusion)
                total_days = (
                    last_external_test_entry.start_date - first_work_entry.start_date
                ).days
                return max(0, total_days)  # Ensure non-negative

            # Fallback: if no valid "МП / Внешний тест", try subsequent statuses
            if self.config_service:
                subsequent_statuses = self.config_service.get_statuses_after(
                    "МП / Внешний тест"
                )
                if subsequent_statuses:
                    # Find first valid entry in any subsequent status
                    valid_subsequent_entries = []
                    for entry in sorted_history:
                        if entry.status in subsequent_statuses:
                            # Validate: open intervals OK, closed intervals >= 5 minutes
                            if entry.end_date is None:
                                # Open interval - consider as valid
                                valid_subsequent_entries.append(entry)
                            else:
                                duration = (
                                    entry.end_date - entry.start_date
                                ).total_seconds()
                                if duration >= self.min_status_duration_seconds:
                                    valid_subsequent_entries.append(entry)

                    if valid_subsequent_entries:
                        # Use first valid subsequent status entry (by start_date)
                        first_subsequent_entry = min(
                            valid_subsequent_entries, key=lambda x: x.start_date
                        )

                        # Calculate calendar days (no pause exclusion)
                        total_days = (
                            first_subsequent_entry.start_date
                            - first_work_entry.start_date
                        ).days
                        return max(0, total_days)  # Ensure non-negative

            # Fallback: if standard algorithm couldn't calculate DevLT and task is still
            # in "МП / В работе" (open interval), use current date
            open_work_entries = [
                e
                for e in work_entries
                if e.end_date is None and e.status == "МП / В работе"
            ]

            if open_work_entries:
                # Find first open "МП / В работе" entry
                first_open_work_entry = min(
                    open_work_entries, key=lambda x: x.start_date
                )

                # Calculate days to current date (UTC)
                from datetime import timezone

                current_date = datetime.now(timezone.utc)

                # Normalize start_date to UTC if needed
                work_start = first_open_work_entry.start_date
                if work_start.tzinfo is None:
                    work_start = work_start.replace(tzinfo=timezone.utc)

                total_days = (current_date - work_start).days
                return max(0, total_days)  # Ensure non-negative

            # No valid "МП / Внешний тест" and no valid subsequent statuses
            return None

        except Exception as e:
            logger.warning(f"Failed to calculate Development Lead Time: {e}")
            return None

    def calculate_statistics(self, times: List[int]) -> TimeMetrics:
        """
        Calculate statistics for a list of times.

        Args:
            times: List of time values in days

        Returns:
            TimeMetrics object
        """
        if not times:
            return TimeMetrics(times=[], mean=None, p85=None, count=0)

        try:
            mean = np.mean(times)
            p85 = np.percentile(times, 85)

            return TimeMetrics(
                times=times, mean=float(mean), p85=float(p85), count=len(times)
            )

        except Exception as e:
            logger.warning(f"Failed to calculate statistics: {e}")
            return TimeMetrics(times=times, mean=None, p85=None, count=len(times))

    def calculate_enhanced_statistics(
        self, times: List[int], pause_times: List[int]
    ) -> TimeMetrics:
        """
        Calculate enhanced statistics including pause time metrics.

        Args:
            times: List of time values in days
            pause_times: List of pause time values in days

        Returns:
            TimeMetrics object with pause time data
        """
        if not times:
            return TimeMetrics(
                times=[],
                mean=None,
                p85=None,
                count=0,
                pause_times=pause_times if pause_times else [],
                pause_mean=None,
                pause_p85=None,
            )

        try:
            # Calculate regular statistics
            mean = np.mean(times)
            p85 = np.percentile(times, 85)

            # Calculate pause statistics
            pause_mean = None
            pause_p85 = None
            if pause_times:
                pause_mean = float(np.mean(pause_times))
                pause_p85 = float(np.percentile(pause_times, 85))

            return TimeMetrics(
                times=times,
                mean=float(mean),
                p85=float(p85),
                count=len(times),
                pause_times=pause_times if pause_times else [],
                pause_mean=pause_mean,
                pause_p85=pause_p85,
            )

        except Exception as e:
            logger.warning(f"Failed to calculate enhanced statistics: {e}")
            return TimeMetrics(
                times=times,
                mean=None,
                p85=None,
                count=len(times),
                pause_times=pause_times if pause_times else [],
                pause_mean=None,
                pause_p85=None,
            )

    def calculate_enhanced_statistics_with_status_durations(
        self,
        times: List[int],
        pause_times: List[int],
        discovery_backlog_times: List[int],
        ready_for_dev_times: List[int],
    ) -> TimeMetrics:
        """
        Calculate enhanced statistics including pause time and status duration metrics.

        Args:
            times: List of time values in days
            pause_times: List of pause time values in days
            discovery_backlog_times: List of discovery backlog duration values in days
            ready_for_dev_times: List of ready for development duration values in days

        Returns:
            TimeMetrics object with all metrics data
        """
        if not times:
            return TimeMetrics(
                times=[],
                mean=None,
                p85=None,
                count=0,
                pause_times=pause_times if pause_times else [],
                pause_mean=None,
                pause_p85=None,
                discovery_backlog_times=discovery_backlog_times
                if discovery_backlog_times
                else [],
                discovery_backlog_mean=None,
                discovery_backlog_p85=None,
                ready_for_dev_times=ready_for_dev_times if ready_for_dev_times else [],
                ready_for_dev_mean=None,
                ready_for_dev_p85=None,
            )

        try:
            # Calculate regular statistics
            mean = np.mean(times)
            p85 = np.percentile(times, 85)

            # Calculate pause statistics
            pause_mean = None
            pause_p85 = None
            if pause_times:
                pause_mean = float(np.mean(pause_times))
                pause_p85 = float(np.percentile(pause_times, 85))

            # Calculate discovery backlog duration statistics
            discovery_backlog_mean = None
            discovery_backlog_p85 = None
            if discovery_backlog_times:
                discovery_backlog_mean = float(np.mean(discovery_backlog_times))
                discovery_backlog_p85 = float(
                    np.percentile(discovery_backlog_times, 85)
                )

            # Calculate ready for development duration statistics
            ready_for_dev_mean = None
            ready_for_dev_p85 = None
            if ready_for_dev_times:
                ready_for_dev_mean = float(np.mean(ready_for_dev_times))
                ready_for_dev_p85 = float(np.percentile(ready_for_dev_times, 85))

            return TimeMetrics(
                times=times,
                mean=float(mean),
                p85=float(p85),
                count=len(times),
                pause_times=pause_times if pause_times else [],
                pause_mean=pause_mean,
                pause_p85=pause_p85,
                discovery_backlog_times=discovery_backlog_times
                if discovery_backlog_times
                else [],
                discovery_backlog_mean=discovery_backlog_mean,
                discovery_backlog_p85=discovery_backlog_p85,
                ready_for_dev_times=ready_for_dev_times if ready_for_dev_times else [],
                ready_for_dev_mean=ready_for_dev_mean,
                ready_for_dev_p85=ready_for_dev_p85,
            )

        except Exception as e:
            logger.warning(
                f"Failed to calculate enhanced statistics with status durations: {e}"
            )
            return TimeMetrics(
                times=times,
                mean=None,
                p85=None,
                count=len(times),
                pause_times=pause_times if pause_times else [],
                pause_mean=None,
                pause_p85=None,
                discovery_backlog_times=discovery_backlog_times
                if discovery_backlog_times
                else [],
                discovery_backlog_mean=None,
                discovery_backlog_p85=None,
                ready_for_dev_times=ready_for_dev_times if ready_for_dev_times else [],
                ready_for_dev_mean=None,
                ready_for_dev_p85=None,
            )

    def calculate_group_metrics(
        self,
        group_name: str,
        ttd_times: List[int],
        ttm_times: List[int],
        tail_times: List[int],
    ) -> GroupMetrics:
        """
        Calculate metrics for a specific group.

        Args:
            group_name: Name of the group
            ttd_times: List of TTD times
            ttm_times: List of TTM times
            tail_times: List of Tail times

        Returns:
            GroupMetrics object
        """
        ttd_metrics = self.calculate_statistics(ttd_times)
        ttm_metrics = self.calculate_statistics(ttm_times)
        tail_metrics = self.calculate_statistics(tail_times)

        return GroupMetrics(
            group_name=group_name,
            ttd_metrics=ttd_metrics,
            ttm_metrics=ttm_metrics,
            tail_metrics=tail_metrics,
            total_tasks=ttd_metrics.count + ttm_metrics.count,
        )

    def calculate_enhanced_group_metrics(
        self,
        group_name: str,
        ttd_times: List[int],
        ttd_pause_times: List[int],
        ttm_times: List[int],
        ttm_pause_times: List[int],
        tail_times: List[int],
    ) -> GroupMetrics:
        """
        Calculate enhanced metrics for a specific group including pause time.

        Args:
            group_name: Name of the group
            ttd_times: List of TTD times
            ttd_pause_times: List of TTD pause times
            ttm_times: List of TTM times
            ttm_pause_times: List of TTM pause times
            tail_times: List of Tail times

        Returns:
            GroupMetrics object with pause time data
        """
        ttd_metrics = self.calculate_enhanced_statistics(ttd_times, ttd_pause_times)
        ttm_metrics = self.calculate_enhanced_statistics(ttm_times, ttm_pause_times)
        tail_metrics = self.calculate_statistics(tail_times)

        return GroupMetrics(
            group_name=group_name,
            ttd_metrics=ttd_metrics,
            ttm_metrics=ttm_metrics,
            tail_metrics=tail_metrics,
            total_tasks=ttd_metrics.count + ttm_metrics.count,
        )

    def calculate_enhanced_group_metrics_with_status_durations(
        self,
        group_name: str,
        ttd_times: List[int],
        ttd_pause_times: List[int],
        ttd_discovery_backlog_times: List[int],
        ttd_ready_for_dev_times: List[int],
        ttm_times: List[int],
        ttm_pause_times: List[int],
        ttm_discovery_backlog_times: List[int],
        ttm_ready_for_dev_times: List[int],
        tail_times: List[int],
    ) -> GroupMetrics:
        """
        Calculate enhanced metrics for a specific group including pause time and status duration metrics.

        Args:
            group_name: Name of the group
            ttd_times: List of TTD times
            ttd_pause_times: List of TTD pause times
            ttd_discovery_backlog_times: List of TTD discovery backlog duration times
            ttd_ready_for_dev_times: List of TTD ready for development duration times
            ttm_times: List of TTM times
            ttm_pause_times: List of TTM pause times
            ttm_discovery_backlog_times: List of TTM discovery backlog duration times
            ttm_ready_for_dev_times: List of TTM ready for development duration times
            tail_times: List of Tail times

        Returns:
            GroupMetrics object with all metrics data
        """
        ttd_metrics = self.calculate_enhanced_statistics_with_status_durations(
            ttd_times,
            ttd_pause_times,
            ttd_discovery_backlog_times,
            ttd_ready_for_dev_times,
        )
        ttm_metrics = self.calculate_enhanced_statistics_with_status_durations(
            ttm_times,
            ttm_pause_times,
            ttm_discovery_backlog_times,
            ttm_ready_for_dev_times,
        )
        tail_metrics = self.calculate_statistics(tail_times)

        return GroupMetrics(
            group_name=group_name,
            ttd_metrics=ttd_metrics,
            ttm_metrics=ttm_metrics,
            tail_metrics=tail_metrics,
            total_tasks=ttd_metrics.count + ttm_metrics.count,
        )
