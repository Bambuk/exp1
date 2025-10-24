"""TTM Details Report generator for Time To Market metrics."""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from radiator.commands.models.time_to_market_models import Quarter, TaskData
from radiator.commands.services.author_team_mapping_service import (
    AuthorTeamMappingService,
)
from radiator.commands.services.config_service import ConfigService
from radiator.commands.services.data_service import DataService
from radiator.commands.services.metrics_service import MetricsService
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
        self.metrics_service = MetricsService()
        self.author_team_mapping_service = AuthorTeamMappingService(
            f"{config_dir}/cpo_authors.txt"
        )

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

    def _collect_csv_rows(self) -> List[dict]:
        """
        Collect CSV rows data for all quarters.

        Returns:
            List of dictionaries with CSV row data
        """
        rows = []
        quarters = self._load_quarters()
        done_statuses = self._load_done_statuses()

        for quarter in quarters:
            tasks = self._get_ttm_tasks_for_quarter(quarter)

            for task in tasks:
                # Load history once and reuse for TTM, Tail, DevLT, and TTD calculations
                history = self.data_service.get_task_history(task.id)

                ttm = self._calculate_ttm(task.id, done_statuses, history)
                tail = self._calculate_tail(task.id, done_statuses, history)
                devlt = self._calculate_devlt(task.id, history)

                # Calculate TTD and its quarter
                ttd = self._calculate_ttd(task.id, ["Готова к разработке"], history)
                ttd_quarter = None
                if ttd is not None:
                    ttd_target_date = self._get_ttd_target_date(history)
                    if ttd_target_date:
                        ttd_quarter = self._determine_quarter_for_date(
                            ttd_target_date, quarters
                        )

                # Calculate pause metrics
                pause = self._calculate_pause(task.id, history)
                ttd_pause = self._calculate_ttd_pause(task.id, history)

                # Calculate status duration metrics
                discovery_backlog_days = self._calculate_discovery_backlog_days(
                    task.id, history
                )
                ready_for_dev_days = self._calculate_ready_for_dev_days(
                    task.id, history
                )

                # Only include tasks with valid TTM
                if ttm is not None:
                    row = self._format_task_row(
                        task,
                        ttm,
                        quarter.name,
                        tail,
                        devlt,
                        ttd,
                        ttd_quarter,
                        pause,
                        ttd_pause,
                        discovery_backlog_days,
                        ready_for_dev_days,
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

        return {
            "Ключ задачи": task.key,
            "Название": task.summary or "",
            "Автор": task.author or "",
            "Команда": team,
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
            "Квартал TTD": ttd_quarter or "",
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
                fieldnames = [
                    "Ключ задачи",
                    "Название",
                    "Автор",
                    "Команда",
                    "Квартал",
                    "TTM",
                    "Пауза",
                    "Tail",
                    "DevLT",
                    "TTD",
                    "TTD Pause",
                    "Discovery backlog (дни)",
                    "Готова к разработке (дни)",
                    "Квартал TTD",
                ]
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
