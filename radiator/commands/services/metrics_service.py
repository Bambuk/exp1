"""Metrics calculation service for Time To Market report."""

from typing import List, Optional, Protocol
from abc import ABC, abstractmethod
from datetime import datetime
import numpy as np
from radiator.core.logging import logger
from radiator.commands.models.time_to_market_models import (
    TimeMetrics, GroupMetrics, StatusHistoryEntry, TaskData, StatusMapping
)


class StartDateStrategy(Protocol):
    """Protocol for start date calculation strategies."""
    
    def calculate_start_date(self, history_data: List[StatusHistoryEntry]) -> Optional[datetime]:
        """
        Calculate start date for time metrics.
        
        Args:
            history_data: List of status history entries
            
        Returns:
            Start date or None if not found
        """


class CreationDateStrategy:
    """Strategy: Use task creation date as start date."""
    
    def calculate_start_date(self, history_data: List[StatusHistoryEntry]) -> Optional[datetime]:
        """Use the earliest date in history as start date."""
        if not history_data:
            return None
        return min(entry.start_date for entry in history_data)


class FirstChangeStrategy:
    """Strategy: Use first status change after creation as start date."""
    
    def calculate_start_date(self, history_data: List[StatusHistoryEntry]) -> Optional[datetime]:
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


class ReadyForDevelopmentStrategy:
    """Strategy: Use first status change after creation as start date, but find 'Готова к разработке' as target."""
    
    def calculate_start_date(self, history_data: List[StatusHistoryEntry]) -> Optional[datetime]:
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
    
    def __init__(self, ttd_strategy: StartDateStrategy = None, ttm_strategy: StartDateStrategy = None):
        """
        Initialize metrics service with strategies.
        
        Args:
            ttd_strategy: Strategy for TTD start date calculation
            ttm_strategy: Strategy for TTM start date calculation
        """
        self.ttd_strategy = ttd_strategy or FirstChangeStrategy()
        self.ttm_strategy = ttm_strategy or FirstChangeStrategy()
    
    def calculate_time_to_delivery(
        self, 
        history_data: List[StatusHistoryEntry], 
        target_statuses: List[str]
    ) -> Optional[int]:
        """
        Calculate Time To Delivery using configured strategy.
        
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
            for entry in sorted(history_data, key=lambda x: x.start_date):
                if entry.status == 'Готова к разработке':
                    days = (entry.start_date - start_date).days
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
        Calculate Time To Market using configured strategy.
        
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
            for entry in sorted(history_data, key=lambda x: x.start_date):
                if entry.status in target_statuses:
                    days = (entry.start_date - start_date).days
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
