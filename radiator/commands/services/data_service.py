"""Data service for Time To Market report."""

from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from radiator.core.logging import logger
from radiator.crud.tracker import tracker_task, tracker_task_history
from radiator.models.tracker import TrackerTask, TrackerTaskHistory
from radiator.commands.models.time_to_market_models import (
    TaskData, StatusHistoryEntry, GroupBy, StatusMapping
)


class DataService:
    """Service for data operations."""
    
    def __init__(self, db: Session):
        """
        Initialize data service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_tasks_for_period(
        self, 
        start_date: datetime, 
        end_date: datetime, 
        group_by: GroupBy,
        status_mapping: StatusMapping,
        metric_type: str = "both"
    ) -> List[TaskData]:
        """
        Get CPO tasks that reached target statuses within the specified period.
        
        Args:
            start_date: Period start date
            end_date: Period end date
            group_by: Grouping type
            status_mapping: Status mapping configuration
            metric_type: Type of metric - "ttd", "ttm", or "both"
            
        Returns:
            List of TaskData objects
        """
        try:
            if group_by == GroupBy.AUTHOR:
                group_field = TrackerTask.author
                filter_condition = TrackerTask.author.isnot(None)
            else:  # TEAM
                group_field = TrackerTask.team
                filter_condition = TrackerTask.team.isnot(None)
            
            # Determine target statuses based on metric type
            if metric_type == "ttd":
                target_statuses = ["Готова к разработке"]  # Only this specific status for TTD
                logger.info(f"Getting tasks for TTD (Готова к разработке) in period {start_date.date()} - {end_date.date()}")
            elif metric_type == "ttm":
                target_statuses = status_mapping.done_statuses  # Only done statuses for TTM
                logger.info(f"Getting tasks for TTM (done statuses) in period {start_date.date()} - {end_date.date()}")
            else:  # "both" - legacy behavior for backward compatibility
                target_statuses = status_mapping.all_target_statuses
                logger.info(f"Getting tasks for both TTD/TTM (all target statuses) in period {start_date.date()} - {end_date.date()}")
            
            if not target_statuses:
                logger.warning("No target statuses found")
                return []
            
            # Get tasks that have target status transitions in the period using JOIN
            tasks_query = self.db.query(
                TrackerTask.id,
                TrackerTask.key,
                group_field,
                TrackerTask.created_at
            ).join(
                TrackerTaskHistory, TrackerTask.id == TrackerTaskHistory.task_id
            ).filter(
                filter_condition,
                TrackerTask.key.like('CPO-%'),
                TrackerTaskHistory.status.in_(target_statuses),
                TrackerTaskHistory.start_date >= start_date,
                TrackerTaskHistory.start_date <= end_date
            ).distinct()
            
            tasks = tasks_query.all()
            logger.info(f"Found {len(tasks)} CPO tasks with {metric_type} transitions in period {start_date.date()} - {end_date.date()}")
            
            result = []
            for task_id, key, group_value, created_at in tasks:
                if group_value:  # Double check group value is not None
                    try:
                        # Handle potential encoding issues
                        if isinstance(group_value, bytes):
                            group_value = group_value.decode('utf-8', errors='replace')
                        elif isinstance(group_value, str):
                            # Ensure it's valid UTF-8
                            group_value.encode('utf-8').decode('utf-8')
                        
                        result.append(TaskData(
                            id=task_id,
                            key=key,
                            group_value=group_value,
                            author=group_value if group_by == GroupBy.AUTHOR else None,
                            team=group_value if group_by == GroupBy.TEAM else None,
                            created_at=created_at
                        ))
                        
                    except (UnicodeDecodeError, UnicodeEncodeError) as e:
                        logger.warning(f"Skipping task with encoding issue: {e}, task_id: {task_id}")
                        continue
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get tasks for period: {e}")
            return []
    
    def get_task_history(self, task_id: int) -> List[StatusHistoryEntry]:
        """
        Get status history for a specific task.
        
        Args:
            task_id: Task ID
            
        Returns:
            List of StatusHistoryEntry objects
        """
        try:
            history_query = self.db.query(
                TrackerTaskHistory.status,
                TrackerTaskHistory.status_display,
                TrackerTaskHistory.start_date,
                TrackerTaskHistory.end_date
            ).filter(
                TrackerTaskHistory.task_id == task_id
            ).order_by(
                TrackerTaskHistory.start_date
            )
            
            history = history_query.all()
            
            result = []
            for status, status_display, start_date, end_date in history:
                result.append(StatusHistoryEntry(
                    status=status,
                    status_display=status_display,
                    start_date=start_date,
                    end_date=end_date
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get task history for task_id {task_id}: {e}")
            return []
