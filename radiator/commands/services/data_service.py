"""Data service for Time To Market report."""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from radiator.commands.models.time_to_market_models import (
    GroupBy,
    StatusHistoryEntry,
    StatusMapping,
    TaskData,
)
from radiator.commands.services.author_team_mapping_service import (
    AuthorTeamMappingService,
)
from radiator.commands.services.metrics_service import MetricsService
from radiator.core.logging import logger

# CRUD operations removed - using direct SQLAlchemy queries
from radiator.models.tracker import TrackerTask, TrackerTaskHistory


class DataService:
    """Service for data operations."""

    def __init__(
        self,
        db: Session,
        author_team_mapping_service: Optional[AuthorTeamMappingService] = None,
    ):
        """
        Initialize data service.

        Args:
            db: Database session
            author_team_mapping_service: Service for author-team mapping
        """
        self.db = db
        self.author_team_mapping_service = author_team_mapping_service
        self.metrics_service = MetricsService()

    def _filter_short_transitions(
        self, history_data: List[StatusHistoryEntry]
    ) -> List[StatusHistoryEntry]:
        """
        Filter out status transitions shorter than minimum duration.

        Args:
            history_data: List of status history entries

        Returns:
            Filtered list with only valid status transitions
        """
        return self.metrics_service._filter_short_status_transitions(history_data)

    def get_task_history_unfiltered(self, task_id: int) -> List[StatusHistoryEntry]:
        """
        Get unfiltered status history for a specific task (for testing purposes).

        Args:
            task_id: Task ID

        Returns:
            List of StatusHistoryEntry objects (unfiltered)
        """
        try:
            history_query = (
                self.db.query(
                    TrackerTaskHistory.status,
                    TrackerTaskHistory.status_display,
                    TrackerTaskHistory.start_date,
                    TrackerTaskHistory.end_date,
                )
                .filter(TrackerTaskHistory.task_id == task_id)
                .order_by(TrackerTaskHistory.start_date)
            )

            history = history_query.all()

            result = []
            for status, status_display, start_date, end_date in history:
                result.append(
                    StatusHistoryEntry(
                        status=status,
                        status_display=status_display,
                        start_date=start_date,
                        end_date=end_date,
                    )
                )

            return result

        except Exception as e:
            logger.error(
                f"Failed to get unfiltered task history for task_id {task_id}: {e}"
            )
            self.db.rollback()
            return []

    def get_tasks_for_period(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: GroupBy,
        status_mapping: StatusMapping,
        metric_type: str = "both",
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
            else:  # TEAM - use author field and map to team via AuthorTeamMappingService
                if not self.author_team_mapping_service:
                    logger.error(
                        "AuthorTeamMappingService is required for team grouping"
                    )
                    return []
                group_field = TrackerTask.author
                filter_condition = TrackerTask.author.isnot(None)

            # Determine target statuses based on metric type
            if metric_type == "ttd":
                target_statuses = [
                    "Готова к разработке"
                ]  # Only this specific status for TTD
                logger.info(
                    f"Getting tasks for TTD (Готова к разработке) in period {start_date.date()} - {end_date.date()}"
                )
            elif metric_type == "ttm":
                target_statuses = (
                    status_mapping.done_statuses
                )  # Only done statuses for TTM
                logger.info(
                    f"Getting tasks for TTM (done statuses) in period {start_date.date()} - {end_date.date()}"
                )
            else:  # "both" - legacy behavior for backward compatibility
                target_statuses = status_mapping.all_target_statuses
                logger.info(
                    f"Getting tasks for both TTD/TTM (all target statuses) in period {start_date.date()} - {end_date.date()}"
                )

            if not target_statuses:
                logger.warning("No target statuses found")
                return []

            # Get tasks that have target status transitions in the period using JOIN
            tasks_query = (
                self.db.query(
                    TrackerTask.id,
                    TrackerTask.key,
                    group_field,
                    TrackerTask.created_at,
                    TrackerTask.summary,
                )
                .join(TrackerTaskHistory, TrackerTask.id == TrackerTaskHistory.task_id)
                .filter(
                    filter_condition,
                    TrackerTask.key.like("CPO-%"),
                    TrackerTaskHistory.status.in_(target_statuses),
                    TrackerTaskHistory.start_date >= start_date,
                    TrackerTaskHistory.start_date <= end_date,
                )
                .distinct()
            )

            tasks = tasks_query.all()
            logger.info(
                f"Found {len(tasks)} CPO tasks with {metric_type} transitions in period {start_date.date()} - {end_date.date()}"
            )

            result = []
            for task_id, key, group_value, created_at, summary in tasks:
                if group_value:  # Double check group value is not None
                    try:
                        # Handle potential encoding issues
                        if isinstance(group_value, bytes):
                            group_value = group_value.decode("utf-8", errors="replace")
                        elif isinstance(group_value, str):
                            # Ensure it's valid UTF-8
                            group_value.encode("utf-8").decode("utf-8")

                        # Determine final group value based on grouping type
                        if group_by == GroupBy.AUTHOR:
                            final_group_value = group_value
                            author = group_value
                            team = None
                        else:  # TEAM
                            # Map author to team using AuthorTeamMappingService
                            team = self.author_team_mapping_service.get_team_by_author(
                                group_value
                            )
                            final_group_value = team
                            author = group_value

                        result.append(
                            TaskData(
                                id=task_id,
                                key=key,
                                group_value=final_group_value,
                                author=author,
                                team=team,
                                created_at=created_at,
                                summary=summary,
                            )
                        )

                    except (UnicodeDecodeError, UnicodeEncodeError) as e:
                        logger.warning(
                            f"Skipping task with encoding issue: {e}, task_id: {task_id}"
                        )
                        continue

            return result

        except Exception as e:
            logger.error(f"Failed to get tasks for period: {e}")
            self.db.rollback()
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
            history_query = (
                self.db.query(
                    TrackerTaskHistory.status,
                    TrackerTaskHistory.status_display,
                    TrackerTaskHistory.start_date,
                    TrackerTaskHistory.end_date,
                )
                .filter(TrackerTaskHistory.task_id == task_id)
                .order_by(TrackerTaskHistory.start_date)
            )

            history = history_query.all()

            result = []
            for status, status_display, start_date, end_date in history:
                result.append(
                    StatusHistoryEntry(
                        status=status,
                        status_display=status_display,
                        start_date=start_date,
                        end_date=end_date,
                    )
                )

            # Apply filtering for short status transitions
            filtered_result = self._filter_short_transitions(result)
            return filtered_result

        except Exception as e:
            logger.error(f"Failed to get task history for task_id {task_id}: {e}")
            self.db.rollback()
            return []

    def get_task_history_by_key(self, task_key: str) -> List[StatusHistoryEntry]:
        """
        Get status history for a specific task by key.

        Args:
            task_key: Task key (e.g., 'FULLSTACK-123')

        Returns:
            List of StatusHistoryEntry objects
        """
        try:
            # First get the task to find its ID
            task = (
                self.db.query(TrackerTask).filter(TrackerTask.key == task_key).first()
            )

            if not task:
                logger.warning(f"Task not found: {task_key}")
                return []

            return self.get_task_history(task.id)

        except Exception as e:
            logger.error(f"Failed to get task history for task_key {task_key}: {e}")
            self.db.rollback()
            return []

    def get_task_histories_batch(
        self, task_ids: List[int]
    ) -> Dict[int, List[StatusHistoryEntry]]:
        """
        Batch load histories for multiple tasks in one SQL query.

        Args:
            task_ids: List of task IDs to load histories for

        Returns:
            Dictionary mapping task_id to list of StatusHistoryEntry objects
        """
        if not task_ids:
            return {}

        try:
            history_query = (
                self.db.query(
                    TrackerTaskHistory.task_id,
                    TrackerTaskHistory.status,
                    TrackerTaskHistory.status_display,
                    TrackerTaskHistory.start_date,
                    TrackerTaskHistory.end_date,
                )
                .filter(TrackerTaskHistory.task_id.in_(task_ids))
                .order_by(TrackerTaskHistory.task_id, TrackerTaskHistory.start_date)
            )

            history_records = history_query.all()

            result = {}
            for task_id in task_ids:
                result[task_id] = []

            for (
                task_id,
                status,
                status_display,
                start_date,
                end_date,
            ) in history_records:
                result[task_id].append(
                    StatusHistoryEntry(
                        status=status,
                        status_display=status_display,
                        start_date=start_date,
                        end_date=end_date,
                    )
                )

            return result

        except Exception as e:
            logger.error(f"Failed to batch load task histories: {e}")
            self.db.rollback()
            return {task_id: [] for task_id in task_ids}

    def get_task_histories_by_keys_batch(
        self, task_keys: List[str]
    ) -> Dict[str, List[StatusHistoryEntry]]:
        """
        Batch load histories for multiple tasks by keys with JOIN in one query.

        Args:
            task_keys: List of task keys to load histories for

        Returns:
            Dictionary mapping task_key to list of StatusHistoryEntry objects
        """
        if not task_keys:
            return {}

        try:
            history_query = (
                self.db.query(
                    TrackerTask.key,
                    TrackerTaskHistory.status,
                    TrackerTaskHistory.status_display,
                    TrackerTaskHistory.start_date,
                    TrackerTaskHistory.end_date,
                )
                .join(TrackerTaskHistory, TrackerTask.id == TrackerTaskHistory.task_id)
                .filter(TrackerTask.key.in_(task_keys))
                .order_by(TrackerTask.key, TrackerTaskHistory.start_date)
            )

            history_records = history_query.all()

            result = {}
            for task_key in task_keys:
                result[task_key] = []

            for (
                task_key,
                status,
                status_display,
                start_date,
                end_date,
            ) in history_records:
                result[task_key].append(
                    StatusHistoryEntry(
                        status=status,
                        status_display=status_display,
                        start_date=start_date,
                        end_date=end_date,
                    )
                )

            return result

        except Exception as e:
            logger.error(f"Failed to batch load task histories by keys: {e}")
            self.db.rollback()
            return {task_key: [] for task_key in task_keys}

    def get_tasks_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[TaskData]:
        """
        Get all tasks within date range in one query.

        Args:
            start_date: Start date of range
            end_date: End date of range

        Returns:
            List of TaskData objects
        """
        try:
            tasks = (
                self.db.query(TrackerTask)
                .filter(
                    TrackerTask.created_at >= start_date,
                    TrackerTask.created_at <= end_date,
                    TrackerTask.key.like("CPO-%"),
                )
                .all()
            )

            result = []
            for task in tasks:
                result.append(
                    TaskData(
                        id=task.id,
                        key=task.key,
                        group_value=task.author,
                        author=task.author,
                        team=task.team,
                        summary=task.summary,
                        created_at=task.created_at,
                    )
                )

            logger.info(
                f"Loaded {len(result)} tasks for date range {start_date} - {end_date}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to load tasks by date range: {e}")
            self.db.rollback()
            return []

    def get_tasks_by_queue(
        self, queue: str, created_since: Optional[datetime] = None
    ) -> List[TaskData]:
        """
        Get tasks filtered by queue prefix and optional created date.

        Args:
            queue: Tracker queue name (e.g. "CPO")
            created_since: Optional date filter (inclusive)

        Returns:
            List of TaskData objects
        """
        try:
            query = self.db.query(TrackerTask).filter(
                TrackerTask.key.like(f"{queue}-%")
            )

            if created_since:
                query = query.filter(TrackerTask.created_at >= created_since)

            tasks = query.all()

            result = []
            for task in tasks:
                result.append(
                    TaskData(
                        id=task.id,
                        key=task.key,
                        group_value=task.author,
                        author=task.author,
                        team=task.team,
                        summary=task.summary,
                        created_at=task.created_at,
                        status=task.status,
                    )
                )

            return result

        except Exception as e:
            logger.error(f"Failed to load tasks by queue {queue}: {e}")
            self.db.rollback()
            return []
