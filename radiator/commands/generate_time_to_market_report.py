"""Refactored command for generating Time To Delivery and Time To Market report for CPO tasks by authors/teams over defined periods."""

import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.commands.models.time_to_market_models import (
    GroupBy,
    GroupMetrics,
    QuarterReport,
    ReportType,
    TaskData,
    TimeToMarketReport,
)
from radiator.commands.renderers.console_renderer import ConsoleRenderer
from radiator.commands.renderers.csv_renderer import CSVRenderer
from radiator.commands.renderers.table_renderer import TableRenderer
from radiator.commands.services.author_team_mapping_service import (
    AuthorTeamMappingService,
)
from radiator.commands.services.config_service import ConfigService
from radiator.commands.services.data_service import DataService
from radiator.commands.services.metrics_service import MetricsService
from radiator.commands.services.testing_returns_metrics import (
    calculate_enhanced_group_metrics_with_testing_returns,
)
from radiator.commands.services.testing_returns_service import TestingReturnsService
from radiator.core.database import SessionLocal
from radiator.core.logging import logger


class GenerateTimeToMarketReportCommand:
    """Refactored command for generating Time To Delivery and Time To Market report."""

    def __init__(
        self,
        group_by: GroupBy = GroupBy.AUTHOR,
        config_dir: str = "data/config",
        output_dir: str = None,
    ):
        """
        Initialize command with grouping preference.

        Args:
            group_by: Grouping type - AUTHOR or TEAM
            config_dir: Configuration directory path
            output_dir: Output directory for reports (optional, uses settings if not provided)
        """
        self.group_by = group_by
        self.config_dir = config_dir
        self.db = SessionLocal()

        # Set output directory
        if output_dir is not None:
            self.output_dir = output_dir
        else:
            # Use settings to determine output directory
            from radiator.core.config import settings

            self.output_dir = settings.REPORTS_DIR

        # Initialize services
        self.config_service = ConfigService(config_dir)
        self.author_team_mapping_service = AuthorTeamMappingService(
            f"{config_dir}/cpo_authors.txt"
        )
        self.data_service = DataService(self.db, self.author_team_mapping_service)
        self.metrics_service = MetricsService()
        self.testing_returns_service = TestingReturnsService(self.db)

        # Report data
        self.report: Optional[TimeToMarketReport] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()

    def generate_report_data(self) -> TimeToMarketReport:
        """
        Generate report data for all quarters.

        Returns:
            TimeToMarketReport object
        """
        try:
            # Load configuration
            quarters = self.config_service.load_quarters()
            status_mapping = self.config_service.load_status_mapping()

            if not quarters:
                logger.warning("No quarters found, returning empty report")
                return TimeToMarketReport(
                    quarters=[],
                    status_mapping=status_mapping,
                    group_by=self.group_by,
                    quarter_reports={},
                )

            if (
                not status_mapping.discovery_statuses
                or not status_mapping.done_statuses
            ):
                logger.warning("No target statuses found, returning empty report")
                return TimeToMarketReport(
                    quarters=quarters,
                    status_mapping=status_mapping,
                    group_by=self.group_by,
                    quarter_reports={},
                )

            quarter_reports = {}

            for quarter in quarters:
                logger.info(f"Processing quarter: {quarter.name}")

                # Get tasks for TTD (only "Готова к разработке" transitions)
                ttd_tasks = self.data_service.get_tasks_for_period(
                    quarter.start_date,
                    quarter.end_date,
                    self.group_by,
                    status_mapping,
                    metric_type="ttd",
                )

                # Get tasks for TTM (only done status transitions)
                ttm_tasks = self.data_service.get_tasks_for_period(
                    quarter.start_date,
                    quarter.end_date,
                    self.group_by,
                    status_mapping,
                    metric_type="ttm",
                )

                # Group tasks by author/team
                group_data = defaultdict(
                    lambda: {
                        "ttd_times": [],
                        "ttd_pause_times": [],
                        "ttd_discovery_backlog_times": [],
                        "ttd_ready_for_dev_times": [],
                        "ttm_times": [],
                        "ttm_pause_times": [],
                        "ttm_discovery_backlog_times": [],
                        "ttm_ready_for_dev_times": [],
                        "tail_times": [],
                        "testing_returns": [],
                        "external_test_returns": [],
                    }
                )

                # Process TTD tasks
                for task in ttd_tasks:
                    group_value = task.group_value
                    task_id = task.id

                    # Get task history
                    history = self.data_service.get_task_history(task_id)

                    if not history:
                        logger.debug(f"No history found for task {task.key}")
                        continue

                    # Calculate Time To Delivery (only for TTD tasks)
                    ttd = self.metrics_service.calculate_time_to_delivery(
                        history, status_mapping.discovery_statuses
                    )
                    if ttd is not None:
                        # Find the date when task reached "Готова к разработке"
                        sorted_history = sorted(history, key=lambda x: x.start_date)
                        ttd_target_date = None
                        for entry in sorted_history:
                            if entry.status == "Готова к разработке":
                                ttd_target_date = entry.start_date
                                break

                        # Calculate pause time only up to TTD target status
                        pause_time = (
                            self.metrics_service.calculate_pause_time_up_to_date(
                                history, ttd_target_date
                            )
                            if ttd_target_date
                            else 0
                        )

                        # Calculate status duration metrics for TTD
                        discovery_backlog_duration = (
                            self.metrics_service.calculate_status_duration(
                                history, "Discovery backlog"
                            )
                        )
                        ready_for_dev_duration = (
                            self.metrics_service.calculate_status_duration(
                                history, "Готова к разработке"
                            )
                        )

                        group_data[group_value]["ttd_times"].append(ttd)
                        group_data[group_value]["ttd_pause_times"].append(pause_time)
                        group_data[group_value]["ttd_discovery_backlog_times"].append(
                            discovery_backlog_duration
                        )
                        group_data[group_value]["ttd_ready_for_dev_times"].append(
                            ready_for_dev_duration
                        )

                # Process TTM tasks
                for task in ttm_tasks:
                    group_value = task.group_value
                    task_id = task.id

                    # Get task history
                    history = self.data_service.get_task_history(task_id)

                    if not history:
                        logger.debug(f"No history found for task {task.key}")
                        continue

                    # Calculate Time To Market (only for TTM tasks)
                    ttm = self.metrics_service.calculate_time_to_market(
                        history, status_mapping.done_statuses
                    )
                    if ttm is not None:
                        # Find the date when task reached first done status
                        sorted_history = sorted(history, key=lambda x: x.start_date)
                        ttm_target_date = None
                        for entry in sorted_history:
                            if entry.status in status_mapping.done_statuses:
                                ttm_target_date = entry.start_date
                                break

                        # Calculate pause time only up to TTM target status
                        pause_time = (
                            self.metrics_service.calculate_pause_time_up_to_date(
                                history, ttm_target_date
                            )
                            if ttm_target_date
                            else 0
                        )

                        # Calculate status duration metrics for TTM
                        discovery_backlog_duration = (
                            self.metrics_service.calculate_status_duration(
                                history, "Discovery backlog"
                            )
                        )
                        ready_for_dev_duration = (
                            self.metrics_service.calculate_status_duration(
                                history, "Готова к разработке"
                            )
                        )

                        group_data[group_value]["ttm_times"].append(ttm)
                        group_data[group_value]["ttm_pause_times"].append(pause_time)
                        group_data[group_value]["ttm_discovery_backlog_times"].append(
                            discovery_backlog_duration
                        )
                        group_data[group_value]["ttm_ready_for_dev_times"].append(
                            ready_for_dev_duration
                        )

                    # Calculate Tail metric (only for TTM tasks)
                    try:
                        tail = self.metrics_service.calculate_tail_metric(
                            history, status_mapping.done_statuses
                        )
                        if tail is not None:
                            group_data[group_value]["tail_times"].append(tail)
                    except Exception as e:
                        logger.warning(
                            f"Error calculating tail metric for task {task.key}: {e}"
                        )
                        # Continue without tail metric

                    # Calculate testing returns for TTM tasks
                    try:
                        (
                            testing_returns,
                            external_returns,
                        ) = self.testing_returns_service.calculate_testing_returns_for_cpo_task(
                            task.key, self.data_service.get_task_history_by_key
                        )
                        group_data[group_value]["testing_returns"].append(
                            testing_returns
                        )
                        group_data[group_value]["external_test_returns"].append(
                            external_returns
                        )
                    except Exception as e:
                        logger.warning(
                            f"Error calculating testing returns for task {task.key}: {e}"
                        )
                        # Continue without testing returns
                        group_data[group_value]["testing_returns"].append(0)
                        group_data[group_value]["external_test_returns"].append(0)

                # Calculate metrics for each group
                groups = {}
                for group_value, data in group_data.items():
                    if data["ttd_times"] or data["ttm_times"] or data["tail_times"]:
                        groups[
                            group_value
                        ] = calculate_enhanced_group_metrics_with_testing_returns(
                            self.metrics_service,
                            group_value,
                            data["ttd_times"],
                            data["ttd_pause_times"],
                            data["ttd_discovery_backlog_times"],
                            data["ttd_ready_for_dev_times"],
                            data["ttm_times"],
                            data["ttm_pause_times"],
                            data["ttm_discovery_backlog_times"],
                            data["ttm_ready_for_dev_times"],
                            data["tail_times"],
                            data["testing_returns"],
                            data["external_test_returns"],
                        )

                if groups:
                    quarter_reports[quarter.name] = QuarterReport(
                        quarter=quarter, groups=groups
                    )

            self.report = TimeToMarketReport(
                quarters=quarters,
                status_mapping=status_mapping,
                group_by=self.group_by,
                quarter_reports=quarter_reports,
            )

            logger.info(f"Generated report data for {len(quarter_reports)} quarters")
            return self.report

        except Exception as e:
            logger.error(f"Failed to generate report data: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return TimeToMarketReport(
                quarters=[],
                status_mapping=self.config_service.load_status_mapping(),
                group_by=self.group_by,
                quarter_reports={},
            )

    def generate_csv(
        self,
        filepath: Optional[str] = None,
        report_type: ReportType = ReportType.BOTH,
        csv_format: str = "wide",
    ) -> str:
        """
        Generate CSV report.

        Args:
            filepath: Output file path (optional)
            report_type: Type of report to generate
            csv_format: CSV format - "wide" (quarters as columns) or "long" (quarters as rows)

        Returns:
            Path to generated CSV file
        """
        if not self.report:
            logger.warning(
                "No report data available. Run generate_report_data() first."
            )
            return ""

        renderer = CSVRenderer(self.report, self.output_dir)
        return renderer.render(filepath, report_type, csv_format)

    def generate_table(
        self, filepath: Optional[str] = None, report_type: ReportType = ReportType.BOTH
    ) -> str:
        """
        Generate table report.

        Args:
            filepath: Output file path (optional)
            report_type: Type of report to generate

        Returns:
            Path to generated table file
        """
        if not self.report:
            logger.warning(
                "No report data available. Run generate_report_data() first."
            )
            return ""

        renderer = TableRenderer(self.report, self.output_dir)
        return renderer.render(filepath, report_type)

    def generate_task_details_csv(self, filepath: Optional[str] = None) -> str:
        """
        Generate detailed CSV with individual task metrics.

        Args:
            filepath: Output file path (optional)

        Returns:
            Path to generated CSV file
        """
        if not self.report:
            logger.warning(
                "No report data available. Run generate_report_data() first."
            )
            return ""

        # Reconnect to database in case of previous transaction errors
        try:
            self.db.rollback()
        except Exception:
            pass  # Ignore rollback errors

        task_details = []

        try:
            import csv
            from datetime import datetime

            # Generate filename if not provided
            if not filepath:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = f"{self.output_dir}/details_{timestamp}.csv"

            # Ensure reports directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            # Process each quarter
            for quarter in self.report.quarters:
                logger.info(f"Processing task details for quarter: {quarter.name}")

                # Get tasks for TTD and TTM
                try:
                    ttd_tasks = self.data_service.get_tasks_for_period(
                        quarter.start_date,
                        quarter.end_date,
                        self.group_by,
                        self.report.status_mapping,
                        metric_type="ttd",
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to get TTD tasks for quarter {quarter.name}: {e}"
                    )
                    ttd_tasks = []

                try:
                    ttm_tasks = self.data_service.get_tasks_for_period(
                        quarter.start_date,
                        quarter.end_date,
                        self.group_by,
                        self.report.status_mapping,
                        metric_type="ttm",
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to get TTM tasks for quarter {quarter.name}: {e}"
                    )
                    ttm_tasks = []

                # Combine tasks for processing
                all_tasks_in_quarter = {
                    task.key: task for task in ttd_tasks + ttm_tasks
                }

                for task_key, task in all_tasks_in_quarter.items():
                    try:
                        history = self.data_service.get_task_history(task.id)
                        if not history:
                            logger.debug(f"No history found for task {task.key}")
                            continue
                    except Exception as e:
                        logger.warning(
                            f"Failed to get history for task {task.key}: {e}"
                        )
                        continue

                    ttd = self.metrics_service.calculate_time_to_delivery(
                        history, self.report.status_mapping.discovery_statuses
                    )
                    ttm = self.metrics_service.calculate_time_to_market(
                        history, self.report.status_mapping.done_statuses
                    )
                    tail = self.metrics_service.calculate_tail_metric(
                        history, self.report.status_mapping.done_statuses
                    )
                    pause_time = self.metrics_service.calculate_pause_time(history)

                    # Calculate status duration metrics
                    discovery_backlog_duration = (
                        self.metrics_service.calculate_status_duration(
                            history, "Discovery backlog"
                        )
                    )
                    ready_for_dev_duration = (
                        self.metrics_service.calculate_status_duration(
                            history, "Готова к разработке"
                        )
                    )

                    # Calculate TTD pause time
                    ttd_pause = self._calculate_ttd_pause(task)

                    # Calculate testing returns
                    testing_returns = 0
                    external_returns = 0
                    try:
                        (
                            testing_returns,
                            external_returns,
                        ) = self.testing_returns_service.calculate_testing_returns_for_cpo_task(
                            task.key, self.data_service.get_task_history_by_key
                        )
                    except Exception as e:
                        logger.warning(
                            f"Error calculating testing returns for task {task.key}: {e}"
                        )

                    task_details.append(
                        {
                            "Автор": task.author,
                            "Команда": task.team,
                            "Ключ задачи": task.key,
                            "Название": task.summary,
                            "TTD": ttd if ttd is not None else "",
                            "TTM": ttm if ttm is not None else "",
                            "Tail": tail if tail is not None else "",
                            "Пауза": pause_time if pause_time is not None else "",
                            "TTD Pause": ttd_pause,
                            "Discovery backlog (дни)": discovery_backlog_duration,
                            "Готова к разработке (дни)": ready_for_dev_duration,
                            "Возвраты с Testing": testing_returns,
                            "Возвраты с Внешний тест": external_returns,
                            "Всего возвратов": testing_returns + external_returns,
                            "Квартал": quarter.name,
                        }
                    )

            # Write to CSV
            if task_details:
                with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                    fieldnames = [
                        "Автор",
                        "Команда",
                        "Ключ задачи",
                        "Название",
                        "TTD",
                        "TTM",
                        "Tail",
                        "Пауза",
                        "TTD Pause",
                        "Discovery backlog (дни)",
                        "Готова к разработке (дни)",
                        "Возвраты с Testing",
                        "Возвраты с Внешний тест",
                        "Всего возвратов",
                        "Квартал",
                    ]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                    writer.writeheader()
                    writer.writerows(task_details)

                logger.info(f"Task details CSV generated: {filepath}")
                logger.info(f"Total tasks processed: {len(task_details)}")
                return filepath
            else:
                logger.info("No task details to write to CSV.")
                return ""
        except Exception as e:
            logger.error(f"Error generating task details CSV: {e}", exc_info=True)
            return ""

    def _calculate_ttd_pause(self, task: TaskData) -> int:
        """
        Calculate TTD pause time (pause time up to 'Готова к разработке' status).

        Args:
            task: Task data

        Returns:
            Number of days spent in pause status up to ready for development
        """
        try:
            history = self.data_service.get_task_history(task.id)
            if not history:
                return 0

            # Find 'Готова к разработке' status
            ready_entry = None
            for entry in sorted(history, key=lambda x: x.start_date):
                if entry.status == "Готова к разработке":
                    ready_entry = entry
                    break

            if not ready_entry:
                return 0

            # Calculate pause time up to ready status
            return self.metrics_service.calculate_pause_time_up_to_date(
                history, ready_entry.start_date
            )

        except Exception as e:
            logger.warning(f"Failed to calculate TTD pause for task {task.key}: {e}")
            return 0

    def print_summary(self, report_type: ReportType = ReportType.BOTH) -> None:
        """
        Print summary of the report to console.

        Args:
            report_type: Type of report to print
        """
        if not self.report:
            print("No report data available. Run generate_report_data() first.")
            return

        renderer = ConsoleRenderer(self.report)
        renderer.render(report_type=report_type)


def main():
    """Main function for command line execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Time To Delivery and Time To Market report"
    )
    parser.add_argument(
        "--group-by",
        choices=["author", "team"],
        default="author",
        help="Group by author or team (default: author)",
    )
    parser.add_argument(
        "--report-type",
        choices=["ttd", "ttm", "both"],
        default="both",
        help="Report type: ttd (Time To Delivery), ttm (Time To Market), or both (default: both)",
    )
    parser.add_argument("--csv", help="CSV output file path")
    parser.add_argument("--table", help="Table output file path")
    parser.add_argument("--task-details", help="Task details CSV output file path")
    parser.add_argument(
        "--csv-format",
        choices=["wide", "long"],
        default="wide",
        help="CSV format: wide (quarters as columns, default) or long (quarters as rows)",
    )
    parser.add_argument(
        "--config-dir",
        default="data/config",
        help="Configuration directory path (default: data/config)",
    )

    args = parser.parse_args()

    try:
        # Convert string arguments to enums
        group_by = GroupBy.AUTHOR if args.group_by == "author" else GroupBy.TEAM
        report_type = ReportType(args.report_type)

        with GenerateTimeToMarketReportCommand(
            group_by=group_by, config_dir=args.config_dir
        ) as cmd:
            # Generate report data
            cmd.generate_report_data()

            # Generate separate TTD and TTM files
            ttd_csv_file = ""
            ttd_table_file = ""
            ttm_csv_file = ""
            ttm_table_file = ""
            task_details_file = ""

            if report_type == ReportType.BOTH:
                # Generate TTD files
                ttd_csv_file = cmd.generate_csv(None, ReportType.TTD, args.csv_format)
                ttd_table_file = cmd.generate_table(None, ReportType.TTD)

                # Generate TTM files
                ttm_csv_file = cmd.generate_csv(None, ReportType.TTM, args.csv_format)
                ttm_table_file = cmd.generate_table(None, ReportType.TTM)
            else:
                # Generate single report type files
                if report_type == ReportType.TTD:
                    ttd_csv_file = cmd.generate_csv(
                        args.csv, ReportType.TTD, args.csv_format
                    )
                    ttd_table_file = cmd.generate_table(args.table, ReportType.TTD)
                elif report_type == ReportType.TTM:
                    ttm_csv_file = cmd.generate_csv(
                        args.csv, ReportType.TTM, args.csv_format
                    )
                    ttm_table_file = cmd.generate_table(args.table, ReportType.TTM)

            # Generate task details CSV (always generate, use provided path or default)
            task_details_file = cmd.generate_task_details_csv(args.task_details)

            # Print summary
            cmd.print_summary(report_type)

            print(f"\nReport generated successfully!")

            # Print generated files
            if ttd_csv_file:
                print(f"TTD CSV file: {ttd_csv_file}")
            if ttd_table_file:
                print(f"TTD Table file: {ttd_table_file}")
            if ttm_csv_file:
                print(f"TTM CSV file: {ttm_csv_file}")
            if ttm_table_file:
                print(f"TTM Table file: {ttm_table_file}")
            if task_details_file:
                print(f"Task details CSV file: {task_details_file}")

    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
