"""Metrics calculation service for Time To Market report."""

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
    ):
        """
        Initialize metrics service with strategies.

        Args:
            ttd_strategy: Strategy for TTD start date calculation
            ttm_strategy: Strategy for TTM start date calculation
        """
        self.ttd_strategy = ttd_strategy or FirstChangeStrategy()
        self.ttm_strategy = ttm_strategy or FirstChangeStrategy()
        self.pause_status = "Приостановлено"  # Status that indicates pause

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
            total_pause_time = 0
            sorted_history = sorted(history_data, key=lambda x: x.start_date)

            for i, entry in enumerate(sorted_history):
                if entry.status == self.pause_status and entry.start_date < end_date:
                    # Find the next status change to calculate pause duration
                    next_entry = None
                    for j in range(i + 1, len(sorted_history)):
                        if sorted_history[j].status != self.pause_status:
                            next_entry = sorted_history[j]
                            break

                    if next_entry and next_entry.start_date <= end_date:
                        pause_duration = (next_entry.start_date - entry.start_date).days
                        total_pause_time += max(0, pause_duration)
                    elif not next_entry or next_entry.start_date > end_date:
                        # Pause period extends beyond end_date, calculate up to end_date
                        pause_duration = (end_date - entry.start_date).days
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

        Args:
            history_data: List of status history entries
            target_statuses: List of discovery status names (ignored, we look for 'Готова к разработке')

        Returns:
            Number of days or None if not found
        """
        try:
            if not history_data:
                return None

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

        Args:
            history_data: List of status history entries
            target_statuses: List of done status names

        Returns:
            Number of days or None if not found
        """
        try:
            if not history_data:
                return None

            # Get start date using TTM strategy
            start_date = self.ttm_strategy.calculate_start_date(history_data)
            if start_date is None:
                return None

            # Find first target status
            target_entry = None
            for entry in sorted(history_data, key=lambda x: x.start_date):
                if entry.status in target_statuses:
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
            logger.warning(f"Failed to calculate Time To Market: {e}")
            return None

    def calculate_tail_metric(
        self, history_data: List[StatusHistoryEntry], done_statuses: List[str]
    ) -> Optional[int]:
        """
        Calculate Tail metric: days from exiting 'МП / Внешний тест' status to any done status.

        Args:
            history_data: List of status history entries
            done_statuses: List of done status names

        Returns:
            Number of days or None if not found
        """
        try:
            if not history_data:
                return None

            # Sort history by date
            sorted_history = sorted(history_data, key=lambda x: x.start_date)

            # Find the last occurrence of 'МП / Внешний тест' status
            last_mp_entry = None
            for entry in sorted_history:
                if entry.status == "МП / Внешний тест":
                    last_mp_entry = entry

            if last_mp_entry is None:
                return None

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
                history_data, last_mp_entry.start_date, done_entry.start_date
            )

            total_days = (done_entry.start_date - last_mp_entry.start_date).days
            effective_days = total_days - pause_time
            return max(0, effective_days)  # Ensure non-negative

        except Exception as e:
            logger.warning(f"Failed to calculate Tail metric: {e}")
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
