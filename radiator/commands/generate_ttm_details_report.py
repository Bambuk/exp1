"""TTM Details Report generator for Time To Market metrics."""

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from radiator.commands.models.time_to_market_models import Quarter, TaskData
from radiator.commands.models.ttm_details_columns import TTMDetailsColumns
from radiator.commands.services.author_team_mapping_service import (
    AuthorTeamMappingService,
)
from radiator.commands.services.config_service import ConfigService
from radiator.commands.services.data_service import DataService
from radiator.commands.services.metrics_service import MetricsService
from radiator.commands.services.team_lead_mapping_service import TeamLeadMappingService
from radiator.commands.services.testing_returns_service import TestingReturnsService
from radiator.core.logging import logger


class TTMDetailsReportGenerator:
    """Generator for TTM Details CSV report."""

    def __init__(self, db: Session, config_dir: str = "data/config"):
        """
        Initialize TTM Details Report generator.

        Args:
            db: Database session
            config_dir: Configuration directory path
        """
        self.db = db
        self.config_dir = config_dir
        self.config_service = ConfigService(config_dir)
        self.data_service = DataService(db)
        self.metrics_service = MetricsService(config_dir=config_dir)
        self.author_team_mapping_service = AuthorTeamMappingService(
            f"{config_dir}/cpo_authors.txt"
        )
        self.team_lead_mapping_service = TeamLeadMappingService(
            f"{config_dir}/teamsleads.txt"
        )
        self.testing_returns_service = TestingReturnsService(db)

    def _load_quarters(self) -> List[Quarter]:
        """
        Load quarters from configuration.

        Returns:
            List of Quarter objects
        """
        return self.config_service.load_quarters()

    def _load_done_statuses(self) -> List[str]:
        """
        Load done statuses from configuration.

        Returns:
            List of done status names
        """
        status_mapping = self.config_service.load_status_mapping()
        return status_mapping.done_statuses

    def _get_ttm_tasks_for_quarter(self, quarter: Quarter) -> List[TaskData]:
        """
        Get TTM tasks for a specific quarter.

        Args:
            quarter: Quarter object

        Returns:
            List of TaskData objects
        """
        from radiator.commands.models.time_to_market_models import GroupBy

        status_mapping = self.config_service.load_status_mapping()
        return self.data_service.get_tasks_for_period(
            start_date=quarter.start_date,
            end_date=quarter.end_date,
            group_by=GroupBy.AUTHOR,  # Default to author grouping
            status_mapping=status_mapping,
            metric_type="ttm",
        )

    def _calculate_ttm(
        self, task_id: int, done_statuses: List[str], history: Optional[List] = None
    ) -> Optional[int]:
        """
        Calculate TTM metric for a task.

        Args:
            task_id: Task ID
            done_statuses: List of done status names
            history: Optional pre-loaded task history

        Returns:
            TTM value in days or None if not found
        """
        if history is None:
            history = self.data_service.get_task_history(task_id)
        if not history:
            return None

        return self.metrics_service.calculate_time_to_market(history, done_statuses)

    def _calculate_ttm_unfinished(
        self, history: List, done_statuses: List[str]
    ) -> Optional[int]:
        """
        Calculate TTM metric for unfinished task (up to current date).

        Args:
            history: Task history entries
            done_statuses: List of done status names (not used but kept for consistency with _calculate_ttm)

        Returns:
            TTM value in days or None if not found
        """
        if not history:
            return None

        try:
            # Get start date using TTM strategy (same as calculate_time_to_market)
            start_date = self.metrics_service.ttm_strategy.calculate_start_date(history)
            if start_date is None:
                return None

            # Нормализуем start_date к timezone-aware (UTC) если он naive
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)

            # Use current date as end date for unfinished tasks
            current_date = datetime.now(timezone.utc)

            # Calculate pause time up to current date
            pause_time = self.metrics_service.calculate_pause_time_up_to_date(
                history, current_date
            )

            # Calculate total days from start to current date
            total_days = (current_date - start_date).days
            effective_days = total_days - pause_time
            return max(0, effective_days)  # Ensure non-negative

        except Exception as e:
            logger.warning(f"Failed to calculate TTM for unfinished task: {e}")
            return None

    def _get_ttm_tasks_for_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[TaskData]:
        """
        Get all TTM tasks within date range in one query.

        Args:
            start_date: Start date of range
            end_date: End date of range

        Returns:
            List of TaskData objects
        """
        return self.data_service.get_tasks_by_date_range(start_date, end_date)

    def _get_ttm_tasks_for_date_range_corrected(
        self, start_date: datetime, end_date: datetime
    ) -> List[TaskData]:
        """
        Get TTM tasks within date range using the same logic as quarter-based approach.

        Args:
            start_date: Start date of range
            end_date: End date of range

        Returns:
            List of TaskData objects (already filtered by TTM)
        """
        from radiator.commands.models.time_to_market_models import GroupBy

        status_mapping = self.config_service.load_status_mapping()
        return self.data_service.get_tasks_for_period(
            start_date=start_date,
            end_date=end_date,
            group_by=GroupBy.AUTHOR,
            status_mapping=status_mapping,
            metric_type="ttm",  # Ключевое отличие - фильтрация по TTM
        )

    def _determine_quarter_for_ttm(
        self, history: List, quarters: List[Quarter], done_statuses: List[str]
    ) -> Optional[str]:
        """
        Determine which quarter a task belongs to based on its stable done date.

        Args:
            history: Task history
            quarters: List of quarters
            done_statuses: List of done status names

        Returns:
            Quarter name or None
        """
        # Find stable done date using existing logic
        stable_done = self.metrics_service._find_stable_done(history, done_statuses)
        if not stable_done:
            return None

        done_date = stable_done.start_date

        # Find matching quarter
        for quarter in quarters:
            if quarter.start_date <= done_date <= quarter.end_date:
                return quarter.name

        return None

    def _calculate_ttd_quarter(
        self, history: List, quarters: List[Quarter]
    ) -> Optional[str]:
        """
        Calculate TTD quarter based on ready status date.

        Args:
            history: Task history
            quarters: List of quarters

        Returns:
            Quarter name or None
        """
        ttd_target_date = self._get_ttd_target_date(history)
        if not ttd_target_date:
            return None

        return self._determine_quarter_for_date(ttd_target_date, quarters)

    def _calculate_all_returns_batched(
        self, cpo_task_keys: List[str]
    ) -> Dict[str, tuple[int, int]]:
        """
        Calculate testing returns for all CPO tasks in one batch.

        Args:
            cpo_task_keys: List of CPO task keys

        Returns:
            Dict mapping CPO key to (testing_returns, external_returns)
        """
        logger.info(f"Calculating returns for {len(cpo_task_keys)} tasks...")

        # Step 1: Build full FULLSTACK hierarchy for all CPO tasks
        cpo_to_fullstack = (
            self.testing_returns_service.build_fullstack_hierarchy_batched(
                cpo_task_keys
            )
        )

        # Step 2: Collect ALL unique FULLSTACK keys
        all_fullstack_keys = set()
        for fullstack_keys in cpo_to_fullstack.values():
            all_fullstack_keys.update(fullstack_keys)

        logger.info(
            f"Loading histories for {len(all_fullstack_keys)} FULLSTACK tasks..."
        )

        # Step 3: Batch load ALL histories at once
        all_histories = self.data_service.get_task_histories_by_keys_batch(
            list(all_fullstack_keys)
        )

        # Step 4: Calculate returns for each CPO task using in-memory data
        result = {}
        for cpo_key, fullstack_keys in cpo_to_fullstack.items():
            if not fullstack_keys:
                result[cpo_key] = (0, 0)
                continue

            total_testing_returns = 0
            total_external_returns = 0

            for fullstack_key in fullstack_keys:
                history = all_histories.get(fullstack_key, [])
                if not history:
                    continue

                (
                    testing_returns,
                    external_returns,
                ) = self.testing_returns_service.calculate_testing_returns_for_task(
                    fullstack_key, history
                )

                total_testing_returns += testing_returns
                total_external_returns += external_returns

            result[cpo_key] = (total_testing_returns, total_external_returns)

        logger.info(f"Completed returns calculation for {len(result)} CPO tasks")
        return result

    def _calculate_ttd(
        self,
        task_id: int,
        discovery_statuses: List[str],
        history: Optional[List] = None,
    ) -> Optional[int]:
        """
        Calculate TTD metric for a task.

        Args:
            task_id: Task ID
            discovery_statuses: List of discovery status names
            history: Optional pre-loaded task history

        Returns:
            TTD value in days or None if not found
        """
        if history is None:
            history = self.data_service.get_task_history(task_id)
        if not history:
            return None

        return self.metrics_service.calculate_time_to_delivery(
            history, discovery_statuses
        )

    def _get_ttd_target_date(self, history: List) -> Optional[datetime]:
        """
        Get the date when task first transitioned to "Готова к разработке" status.

        Args:
            history: Task history entries

        Returns:
            Date of first "Готова к разработке" transition or None if not found
        """
        if not history:
            return None

        # Sort history by start_date to ensure chronological order
        sorted_history = sorted(history, key=lambda x: x.start_date)

        # Find first "Готова к разработке" status
        for entry in sorted_history:
            if entry.status == "Готова к разработке":
                return entry.start_date

        return None

    def _determine_quarter_for_date(
        self, date: datetime, quarters: List[Quarter]
    ) -> Optional[str]:
        """
        Determine which quarter a date falls into.

        Args:
            date: Date to check
            quarters: List of Quarter objects

        Returns:
            Quarter name or None if date doesn't fall into any quarter
        """
        for quarter in quarters:
            if quarter.start_date <= date <= quarter.end_date:
                return quarter.name
        return None

    def _calculate_tail(
        self, task_id: int, done_statuses: List[str], history: Optional[List] = None
    ) -> Optional[int]:
        """
        Calculate Tail metric for a task.

        Args:
            task_id: Task ID
            done_statuses: List of done status names
            history: Optional pre-loaded task history

        Returns:
            Tail value in days or None if not found
        """
        if history is None:
            history = self.data_service.get_task_history(task_id)
        if not history:
            return None

        return self.metrics_service.calculate_tail_metric(history, done_statuses)

    def _calculate_devlt(
        self, task_id: int, history: Optional[List] = None
    ) -> Optional[int]:
        """
        Calculate DevLT metric for a task.

        Args:
            task_id: Task ID
            history: Optional pre-loaded task history

        Returns:
            DevLT value in days or None if not found
        """
        if history is None:
            history = self.data_service.get_task_history(task_id)
        if not history:
            return None

        return self.metrics_service.calculate_dev_lead_time(history)

    def _calculate_pause(
        self, task_id: int, history: Optional[List] = None
    ) -> Optional[int]:
        """
        Calculate pause time for a task.

        Args:
            task_id: Task ID
            history: Optional pre-loaded task history

        Returns:
            Pause time in days or None if not found
        """
        if history is None:
            history = self.data_service.get_task_history(task_id)
        if not history:
            return None

        return self.metrics_service.calculate_pause_time(history)

    def _calculate_ttd_pause(
        self, task_id: int, history: Optional[List] = None
    ) -> Optional[int]:
        """
        Calculate TTD pause time (pause time up to 'Готова к разработке' status).

        Args:
            task_id: Task ID
            history: Optional pre-loaded task history

        Returns:
            TTD pause time in days or None if not found
        """
        if history is None:
            history = self.data_service.get_task_history(task_id)
        if not history:
            return None

        # Find 'Готова к разработке' status
        ready_date = self._get_ttd_target_date(history)
        if not ready_date:
            return None

        return self.metrics_service.calculate_pause_time_up_to_date(history, ready_date)

    def _calculate_discovery_backlog_days(
        self, task_id: int, history: Optional[List] = None
    ) -> Optional[int]:
        """
        Calculate time spent in 'Discovery backlog' status.

        Args:
            task_id: Task ID
            history: Optional pre-loaded task history

        Returns:
            Time in days spent in Discovery backlog or None if not found
        """
        if history is None:
            history = self.data_service.get_task_history(task_id)
        if not history:
            return None

        return self.metrics_service.calculate_status_duration(
            history, "Discovery backlog"
        )

    def _calculate_ready_for_dev_days(
        self, task_id: int, history: Optional[List] = None
    ) -> Optional[int]:
        """
        Calculate time spent in 'Готова к разработке' status.

        Args:
            task_id: Task ID
            history: Optional pre-loaded task history

        Returns:
            Time in days spent in Готова к разработке or None if not found
        """
        if history is None:
            history = self.data_service.get_task_history(task_id)
        if not history:
            return None

        return self.metrics_service.calculate_status_duration(
            history, "Готова к разработке"
        )

    def _get_last_discovery_backlog_exit_date(
        self, history: List
    ) -> Optional[datetime]:
        """
        Get the date of last exit from Discovery backlog status.

        Args:
            history: Task history entries

        Returns:
            Date of last exit from Discovery backlog or None if not found
        """
        if not history:
            return None

        # Sort history by start_date to ensure chronological order
        sorted_history = sorted(history, key=lambda x: x.start_date)

        # Find all Discovery backlog entries
        discovery_backlog_entries = [
            entry for entry in sorted_history if entry.status == "Discovery backlog"
        ]

        if not discovery_backlog_entries:
            return None

        # Get the last Discovery backlog entry
        last_entry = discovery_backlog_entries[-1]

        # Return end_date if it exists (means task exited from Discovery backlog)
        return last_entry.end_date if last_entry.end_date else None

    def _get_team_by_author(self, task: TaskData) -> str:
        """
        Get team for task using AuthorTeamMappingService if task.team is None.

        Args:
            task: Task data

        Returns:
            Team name or empty string
        """
        # Use existing team if available
        if task.team:
            return task.team

        # Get team from AuthorTeamMappingService if task.team is None
        if task.author:
            return self.author_team_mapping_service.get_team_by_author(task.author)

        return ""

    def _get_pm_lead_by_team(self, team: str) -> str:
        """
        Get PM Lead for team using TeamLeadMappingService.

        Args:
            team: Team name

        Returns:
            PM Lead name or "Без команды" if team not found
        """
        if not team:
            return "Без команды"
        return self.team_lead_mapping_service.get_lead_by_team(team)

    def _has_valid_work_status(
        self, task_id: int, history: Optional[List] = None
    ) -> bool:
        """
        Check if task has valid 'МП / В работе' status entry (>= 5 minutes).

        Args:
            task_id: Task ID
            history: Optional pre-loaded task history

        Returns:
            True if task has valid 'МП / В работе' entry, False otherwise
        """
        if history is None:
            history = self.data_service.get_task_history(task_id)
        if not history:
            return False

        # Sort history by date
        sorted_history = sorted(history, key=lambda x: x.start_date)

        # Find all "МП / В работе" entries
        work_entries = [e for e in sorted_history if e.status == "МП / В работе"]

        if not work_entries:
            return False

        # Filter "МП / В работе" entries: must have end_date and duration > 5 minutes
        # Same validation logic as in calculate_dev_lead_time
        for entry in work_entries:
            if entry.end_date is None:
                continue  # Skip open intervals (work not completed)

            duration = (entry.end_date - entry.start_date).total_seconds()
            if duration >= self.metrics_service.min_status_duration_seconds:
                return True  # Found at least one valid entry

        return False  # No valid entries found

    def _calculate_testing_returns(self, task_key: str) -> tuple[int, int]:
        """
        Calculate testing returns for a task.

        Args:
            task_key: Task key

        Returns:
            Tuple of (testing_returns, external_returns)
        """
        try:
            return self.testing_returns_service.calculate_testing_returns_for_cpo_task_batched(
                task_key, self.data_service.get_task_histories_by_keys_batch
            )
        except Exception as e:
            logger.warning(f"Failed to calculate testing returns for {task_key}: {e}")
            return 0, 0

    def _get_unfinished_tasks(self) -> List[TaskData]:
        """
        Get unfinished tasks (tasks that transitioned to 'Готова к разработке' but don't have stable_done).

        Returns:
            List of TaskData objects for unfinished tasks
        """
        quarters = self._load_quarters()
        done_statuses = self._load_done_statuses()

        # Берем диапазон от начала первого до конца последнего квартала
        # Но для незавершенных задач нужно расширить до текущей даты
        start_date = min(q.start_date for q in quarters)
        end_date = max(q.end_date for q in quarters)
        # Нормализуем даты к timezone-aware (UTC) если они naive
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        # Расширяем до текущей даты для незавершенных задач
        current_date = datetime.now(timezone.utc)
        if current_date > end_date:
            end_date = current_date

        # Получаем все задачи, которые перешли в "Готова к разработке"
        from radiator.commands.models.time_to_market_models import GroupBy

        status_mapping = self.config_service.load_status_mapping()
        all_ready_tasks = self.data_service.get_tasks_for_period(
            start_date=start_date,
            end_date=end_date,
            group_by=GroupBy.AUTHOR,
            status_mapping=status_mapping,
            metric_type="ttd",  # Получаем задачи с переходом в "Готова к разработке"
        )

        # Фильтруем задачи, у которых нет stable_done
        unfinished_tasks = []
        for task in all_ready_tasks:
            history = self.data_service.get_task_history(task.id)
            stable_done = self.metrics_service._find_stable_done(history, done_statuses)
            if not stable_done:
                unfinished_tasks.append(task)

        return unfinished_tasks

    def _calculate_task_metrics(
        self,
        task: TaskData,
        history: List,
        done_statuses: List[str],
        quarters: List[Quarter],
        stable_done: Optional[object] = None,
        is_finished: bool = True,
    ) -> dict:
        """
        Calculate all metrics for a task (finished or unfinished).

        Args:
            task: Task data
            history: Task history entries
            done_statuses: List of done status names
            quarters: List of Quarter objects
            stable_done: Optional stable_done entry (for finished tasks)
            is_finished: Whether task is finished

        Returns:
            Dictionary with task metrics
        """
        # Calculate TTM based on task status
        if is_finished:
            ttm = self._calculate_ttm(task.id, done_statuses, history)
        else:
            ttm = self._calculate_ttm_unfinished(history, done_statuses)

        # Determine quarter name
        quarter_name = ""
        if stable_done:
            done_date = stable_done.start_date
            for quarter in quarters:
                if quarter.start_date <= done_date <= quarter.end_date:
                    quarter_name = quarter.name
                    break

        return {
            "task": task,
            "quarter_name": quarter_name,
            "ttm": ttm,
            "tail": self._calculate_tail(task.id, done_statuses, history),
            "devlt": self._calculate_devlt(task.id, history),
            "ttd": self._calculate_ttd(task.id, ["Готова к разработке"], history),
            "ttd_quarter": self._calculate_ttd_quarter(history, quarters),
            "pause": self._calculate_pause(task.id, history),
            "ttd_pause": self._calculate_ttd_pause(task.id, history),
            "discovery_backlog_days": self._calculate_discovery_backlog_days(
                task.id, history
            ),
            "ready_for_dev_days": self._calculate_ready_for_dev_days(task.id, history),
            "created_at": task.created_at,
            "last_discovery_backlog_exit_date": self._get_last_discovery_backlog_exit_date(
                history
            ),
            "stable_done_date": stable_done.start_date if stable_done else None,
            "has_development": self._has_valid_work_status(task.id, history),
            "is_finished": is_finished,
        }

    def _collect_csv_rows(self) -> List[dict]:
        """
        Collect CSV rows data with optimized batch processing.

        Returns:
            List of dictionaries with CSV row data
        """
        rows = []
        quarters = self._load_quarters()
        done_statuses = self._load_done_statuses()

        # Берем диапазон от начала первого до конца последнего квартала
        start_date = min(q.start_date for q in quarters)
        end_date = max(q.end_date for q in quarters)

        # Получаем ВСЕ задачи одним запросом (с правильной фильтрацией по TTM)
        all_tasks = self._get_ttm_tasks_for_date_range_corrected(start_date, end_date)

        # Собираем все метрики КРОМЕ возвратов
        # Задачи уже отфильтрованы по TTM в _get_ttm_tasks_for_date_range_corrected
        tasks_data = []
        for task in all_tasks:
            history = self.data_service.get_task_history(task.id)

            # Находим stable_done один раз для использования в нескольких местах
            stable_done = self.metrics_service._find_stable_done(history, done_statuses)

            # Определяем квартал для задачи (TTM уже есть)
            quarter_name = None
            if stable_done:
                done_date = stable_done.start_date
                # Find matching quarter
                for quarter in quarters:
                    if quarter.start_date <= done_date <= quarter.end_date:
                        quarter_name = quarter.name
                        break

            if not quarter_name:
                continue

            # Собираем все метрики кроме возвратов
            task_metrics = self._calculate_task_metrics(
                task, history, done_statuses, quarters, stable_done, is_finished=True
            )
            tasks_data.append(task_metrics)

        # Добавляем незавершенные задачи
        unfinished_tasks = self._get_unfinished_tasks()
        for task in unfinished_tasks:
            history = self.data_service.get_task_history(task.id)

            # Проверяем, что задача действительно незавершенная (нет stable_done)
            stable_done = self.metrics_service._find_stable_done(history, done_statuses)
            if stable_done:
                continue  # Пропускаем, если есть stable_done

            # Собираем все метрики для незавершенной задачи
            task_metrics = self._calculate_task_metrics(
                task,
                history,
                done_statuses,
                quarters,
                stable_done=None,
                is_finished=False,
            )
            tasks_data.append(task_metrics)

        # Шаг 2: Собираем все ключи CPO задач для расчета возвратов
        cpo_task_keys = [td["task"].key for td in tasks_data]

        # Шаг 3: Batch-расчет возвратов для всех задач сразу
        returns_data = self._calculate_all_returns_batched(cpo_task_keys)

        # Шаг 4: Формируем финальные строки отчета
        for task_metrics in tasks_data:
            task_key = task_metrics["task"].key
            testing_returns, external_returns = returns_data.get(task_key, (0, 0))

            row = self._format_task_row(
                task_metrics["task"],
                task_metrics["ttm"],
                task_metrics["quarter_name"],
                task_metrics["tail"],
                task_metrics["devlt"],
                task_metrics["ttd"],
                task_metrics["ttd_quarter"],
                task_metrics["pause"],
                task_metrics["ttd_pause"],
                task_metrics["discovery_backlog_days"],
                task_metrics["ready_for_dev_days"],
                testing_returns,
                external_returns,
                testing_returns + external_returns,
                task_metrics["created_at"],
                task_metrics["last_discovery_backlog_exit_date"],
                task_metrics["stable_done_date"],
                task_metrics["has_development"],
                task_metrics.get(
                    "is_finished", True
                ),  # По умолчанию True для обратной совместимости
            )
            rows.append(row)

        return rows

    def _format_task_row(
        self,
        task: TaskData,
        ttm: int,
        quarter_name: str,
        tail: Optional[int] = None,
        devlt: Optional[int] = None,
        ttd: Optional[int] = None,
        ttd_quarter: Optional[str] = None,
        pause: Optional[int] = None,
        ttd_pause: Optional[int] = None,
        discovery_backlog_days: Optional[int] = None,
        ready_for_dev_days: Optional[int] = None,
        testing_returns: Optional[int] = None,
        external_returns: Optional[int] = None,
        total_returns: Optional[int] = None,
        created_at: Optional[datetime] = None,
        last_discovery_backlog_exit_date: Optional[datetime] = None,
        stable_done_date: Optional[datetime] = None,
        has_development: bool = False,
        is_finished: bool = True,
    ) -> dict:
        """
        Format task data into CSV row dictionary.

        Args:
            task: Task data
            ttm: TTM value in days
            quarter_name: Quarter name
            tail: Tail value in days (optional)
            devlt: DevLT value in days (optional)

        Returns:
            Dictionary with CSV row data
        """
        # Get team using the dedicated method
        team = self._get_team_by_author(task)
        # Get PM Lead using TeamLeadMappingService
        pm_lead = self._get_pm_lead_by_team(team)

        return {
            "Ключ задачи": task.key,
            "Название": task.summary or "",
            "Автор": task.author or "",
            "Команда": team,
            "PM Lead": pm_lead,
            "Квартал": quarter_name,
            "TTM": ttm,
            "Пауза": pause if pause is not None else "",
            "Tail": tail if tail is not None else "",
            "DevLT": devlt if devlt is not None else "",
            "TTD": ttd if ttd is not None else "",
            "TTD Pause": ttd_pause if ttd_pause is not None else "",
            "Discovery backlog (дни)": discovery_backlog_days
            if discovery_backlog_days is not None
            else "",
            "Готова к разработке (дни)": ready_for_dev_days
            if ready_for_dev_days is not None
            else "",
            "Возвраты с Testing": testing_returns
            if testing_returns is not None
            else "",
            "Возвраты с Внешний тест": external_returns
            if external_returns is not None
            else "",
            "Всего возвратов": total_returns if total_returns is not None else "",
            "Квартал TTD": ttd_quarter or "",
            "Создана": created_at.strftime("%Y-%m-%d") if created_at else "",
            "Начало работы": last_discovery_backlog_exit_date.strftime("%Y-%m-%d")
            if last_discovery_backlog_exit_date
            else "",
            "Завершено": stable_done_date.strftime("%Y-%m-%d")
            if stable_done_date
            else "",
            "Разработка": 1 if has_development else 0,
            "Завершена": 1 if is_finished else 0,
        }

    def generate_csv(self, output_path: str) -> str:
        """
        Generate TTM Details CSV report.

        Args:
            output_path: Path to output CSV file

        Returns:
            Path to generated CSV file
        """
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Collect CSV rows data
            rows = self._collect_csv_rows()

            # Create CSV with data
            with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = TTMDetailsColumns.COLUMN_NAMES
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            logger.info(
                f"TTM Details CSV generated: {output_path} with {len(rows)} rows"
            )
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate TTM Details CSV: {e}")
            raise


def main():
    """Main function for command line execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate TTM Details CSV report")
    parser.add_argument("--output", required=True, help="Output CSV file path")
    parser.add_argument(
        "--config-dir",
        default="data/config",
        help="Configuration directory path (default: data/config)",
    )

    args = parser.parse_args()

    try:
        from radiator.core.database import SessionLocal

        with SessionLocal() as db:
            generator = TTMDetailsReportGenerator(db=db, config_dir=args.config_dir)
            csv_path = generator.generate_csv(args.output)
            print(f"TTM Details report generated: {csv_path}")

    except Exception as e:
        logger.error(f"Failed to generate TTM Details report: {e}")
        import sys

        sys.exit(1)


if __name__ == "__main__":
    main()
