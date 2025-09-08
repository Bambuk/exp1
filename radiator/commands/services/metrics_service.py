"""Metrics calculation service for Time To Market report."""

from typing import List, Optional
import numpy as np
from radiator.core.logging import logger
from radiator.commands.models.time_to_market_models import (
    TimeMetrics, GroupMetrics, StatusHistoryEntry, TaskData, StatusMapping
)


class MetricsService:
    """Service for calculating time metrics."""
    
    def calculate_time_to_delivery(
        self, 
        history_data: List[StatusHistoryEntry], 
        target_statuses: List[str]
    ) -> Optional[int]:
        """
        Calculate Time To Delivery (days from creation to first discovery status).
        
        Args:
            history_data: List of status history entries
            target_statuses: List of discovery status names
            
        Returns:
            Number of days or None if not found
        """
        try:
            if not history_data:
                return None
            
            # Find the earliest date in history (actual task creation)
            earliest_date = min(entry.start_date for entry in history_data)
            
            for entry in history_data:
                if entry.status in target_statuses:
                    # Calculate days between earliest date and first discovery status
                    days = (entry.start_date - earliest_date).days
                    return max(0, days)  # Ensure non-negative
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to calculate Time To Delivery: {e}")
            return None
    
    def calculate_time_to_market(
        self, 
        history_data: List[StatusHistoryEntry], 
        target_statuses: List[str]
    ) -> Optional[int]:
        """
        Calculate Time To Market (days from creation to first done status).
        
        Args:
            history_data: List of status history entries
            target_statuses: List of done status names
            
        Returns:
            Number of days or None if not found
        """
        try:
            if not history_data:
                return None
            
            # Find the earliest date in history (actual task creation)
            earliest_date = min(entry.start_date for entry in history_data)
            
            for entry in history_data:
                if entry.status in target_statuses:
                    # Calculate days between earliest date and first done status
                    days = (entry.start_date - earliest_date).days
                    return max(0, days)  # Ensure non-negative
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to calculate Time To Market: {e}")
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
                times=times,
                mean=float(mean),
                p85=float(p85),
                count=len(times)
            )
            
        except Exception as e:
            logger.warning(f"Failed to calculate statistics: {e}")
            return TimeMetrics(times=times, mean=None, p85=None, count=len(times))
    
    def calculate_group_metrics(
        self,
        group_name: str,
        ttd_times: List[int],
        ttm_times: List[int]
    ) -> GroupMetrics:
        """
        Calculate metrics for a specific group.
        
        Args:
            group_name: Name of the group
            ttd_times: List of TTD times
            ttm_times: List of TTM times
            
        Returns:
            GroupMetrics object
        """
        ttd_metrics = self.calculate_statistics(ttd_times)
        ttm_metrics = self.calculate_statistics(ttm_times)
        
        return GroupMetrics(
            group_name=group_name,
            ttd_metrics=ttd_metrics,
            ttm_metrics=ttm_metrics,
            total_tasks=ttd_metrics.count + ttm_metrics.count
        )
