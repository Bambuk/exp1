"""Command for generating status change report for tasks by authors over last 2 weeks."""

import csv
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from sqlalchemy.orm import Session

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.commands.services.author_team_mapping_service import (
    AuthorTeamMappingService,
)
from radiator.core.config import settings
from radiator.core.database import SessionLocal
from radiator.core.logging import logger

# CRUD operations removed - using direct SQLAlchemy queries
from radiator.models.tracker import TrackerTask, TrackerTaskHistory


class GenerateStatusChangeReportCommand:
    """Command for generating status change report for CPO tasks by authors or teams over last 2 weeks."""

    def __init__(
        self,
        group_by: str = "author",
        config_dir: str = "data/config",
        db: Session = None,
    ):
        """
        Initialize command with grouping preference.

        Args:
            group_by: Grouping field - "author" or "team"
            config_dir: Configuration directory path
            db: Database session (optional, creates new if not provided)
        """
        if group_by not in ["author", "team"]:
            raise ValueError("group_by must be 'author' or 'team'")

        self.group_by = group_by
        self.config_dir = config_dir
        self.db = db if db is not None else SessionLocal()
        self.report_data: Dict[str, Dict[str, int]] = {}
        self.week1_data: Dict[str, int] = {}
        self.week2_data: Dict[str, int] = {}

        # Initialize AuthorTeamMappingService for team grouping
        if group_by == "team":
            self.author_team_mapping_service = AuthorTeamMappingService(
                f"{config_dir}/cpo_authors.txt"
            )
        else:
            self.author_team_mapping_service = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()

    def get_status_changes_by_group(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Dict[str, int]]:
        """
        Get count of status changes and unique tasks by author or team within date range for CPO tasks only.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dictionary mapping author/team to dict with 'changes', 'tasks', and 'open_tasks' counts
        """
        try:
            # Query status changes within date range
            # We need to join tracker_tasks with tracker_task_history to get author/team information
            if self.group_by == "author":
                group_field = TrackerTask.author
                filter_condition = TrackerTask.author.isnot(None)
            else:  # team - use author field and map to team via AuthorTeamMappingService
                if not self.author_team_mapping_service:
                    logger.error(
                        "AuthorTeamMappingService is required for team grouping"
                    )
                    return {}
                group_field = TrackerTask.author
                filter_condition = TrackerTask.author.isnot(None)

            query = (
                self.db.query(
                    group_field, TrackerTaskHistory.id, TrackerTaskHistory.task_id
                )
                .join(TrackerTaskHistory, TrackerTask.id == TrackerTaskHistory.task_id)
                .filter(
                    TrackerTaskHistory.start_date >= start_date,
                    TrackerTaskHistory.start_date < end_date,
                    filter_condition,  # Exclude tasks without author/team
                    TrackerTask.key.like("CPO-%"),  # Only CPO tasks
                )
            )

            logger.info(
                f"Executing query for CPO tasks grouped by {self.group_by} in date range: {start_date.date()} to {end_date.date()}"
            )

            # Execute query and count by author/team
            results = query.all()
            logger.info(f"Query returned {len(results)} results")

            group_data = defaultdict(lambda: {"changes": 0, "tasks": set()})

            for i, (group_value, _, task_id) in enumerate(results):
                if group_value:  # Double check group value is not None
                    try:
                        # Handle potential encoding issues
                        if isinstance(group_value, bytes):
                            group_value = group_value.decode("utf-8", errors="replace")
                        elif isinstance(group_value, str):
                            # Ensure it's valid UTF-8
                            group_value.encode("utf-8").decode("utf-8")

                        # Determine final group value based on grouping type
                        if self.group_by == "author":
                            final_group_value = group_value
                        else:  # team
                            # Map author to team using AuthorTeamMappingService
                            final_group_value = (
                                self.author_team_mapping_service.get_team_by_author(
                                    group_value
                                )
                            )
                            logger.debug(
                                f"Mapped author '{group_value}' to team '{final_group_value}'"
                            )

                        group_data[final_group_value]["changes"] += 1
                        group_data[final_group_value]["tasks"].add(task_id)
                    except (UnicodeDecodeError, UnicodeEncodeError) as e:
                        logger.warning(
                            f"Skipping {self.group_by} with encoding issue at position {i}: {e}, value: {repr(group_value)}"
                        )
                        continue

            # Convert sets to counts and return
            result = {}
            for group_value, data in group_data.items():
                result[group_value] = {
                    "changes": data["changes"],
                    "tasks": len(data["tasks"]),
                }

            total_changes = sum(data["changes"] for data in result.values())
            total_tasks = sum(data["tasks"] for data in result.values())
            group_name = "authors" if self.group_by == "author" else "teams"
            logger.info(
                f"Found {total_changes} status changes across {total_tasks} unique tasks for {len(result)} {group_name} from {start_date.date()} to {end_date.date()}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get status changes by author: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}

    def get_open_tasks_by_group(self) -> Dict[str, Dict[str, Any]]:
        """
        Get count of open tasks and last update dates by author or team grouped by discovery/delivery blocks for CPO tasks only.
        Closed tasks (with 'done' block) are automatically excluded by the status mapping logic.

        Returns:
            Dictionary mapping author/team to dict with 'discovery', 'delivery' counts and last update dates
        """
        try:
            # Load status mapping from file
            status_mapping = self._load_status_mapping()

            # Get open tasks with their IDs, status, and last update date
            if self.group_by == "author":
                group_field = TrackerTask.author
                filter_condition = TrackerTask.author.isnot(None)
            else:  # team - use author field and map to team via AuthorTeamMappingService
                if not self.author_team_mapping_service:
                    logger.error(
                        "AuthorTeamMappingService is required for team grouping"
                    )
                    return {}
                group_field = TrackerTask.author
                filter_condition = TrackerTask.author.isnot(None)

            open_tasks_query = self.db.query(
                group_field,
                TrackerTask.id,
                TrackerTask.status,
                TrackerTask.task_updated_at,
            ).filter(
                filter_condition,  # Exclude tasks without author/team
                TrackerTask.key.like("CPO-%"),  # Only CPO tasks
            )

            open_tasks = open_tasks_query.all()
            logger.info(f"Query returned {len(open_tasks)} open tasks")

            author_blocks = defaultdict(
                lambda: {
                    "discovery": {"count": 0, "last_change": None},
                    "delivery": {"count": 0, "last_change": None},
                }
            )

            for group_value, task_id, status, task_updated_at in open_tasks:
                if group_value:  # Double check group value is not None
                    try:
                        # Handle potential encoding issues
                        if isinstance(group_value, bytes):
                            group_value = group_value.decode("utf-8", errors="replace")
                        elif isinstance(group_value, str):
                            # Ensure it's valid UTF-8
                            group_value.encode("utf-8").decode("utf-8")

                        # Determine final group value based on grouping type
                        if self.group_by == "author":
                            final_group_value = group_value
                        else:  # team
                            # Map author to team using AuthorTeamMappingService
                            final_group_value = (
                                self.author_team_mapping_service.get_team_by_author(
                                    group_value
                                )
                            )

                        # Map status to block
                        block = status_mapping.get(
                            status, "discovery"
                        )  # Default to discovery if status not found
                        # Only count tasks that are not in done status
                        if block in ["discovery", "delivery"] and block != "done":
                            author_blocks[final_group_value][block]["count"] += 1

                            # Update last update date if this task has a more recent update
                            if task_updated_at:
                                current_last = author_blocks[final_group_value][block][
                                    "last_change"
                                ]
                                if (
                                    current_last is None
                                    or task_updated_at > current_last
                                ):
                                    author_blocks[final_group_value][block][
                                        "last_change"
                                    ] = task_updated_at

                    except (UnicodeDecodeError, UnicodeEncodeError) as e:
                        logger.warning(
                            f"Skipping {self.group_by} with encoding issue: {e}, value: {repr(group_value)}"
                        )
                        continue

            # Convert to final format
            result = {}
            for author, blocks in author_blocks.items():
                result[author] = {
                    "discovery": blocks["discovery"]["count"],
                    "delivery": blocks["delivery"]["count"],
                    "discovery_last_change": blocks["discovery"]["last_change"],
                    "delivery_last_change": blocks["delivery"]["last_change"],
                }

            total_discovery = sum(data["discovery"] for data in result.values())
            total_delivery = sum(data["delivery"] for data in result.values())
            logger.info(
                f"Found {total_discovery} discovery tasks and {total_delivery} delivery tasks for {len(result)} authors"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get open tasks by author: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}

    def _load_status_mapping(self) -> Dict[str, str]:
        """
        Load status to block mapping from file.

        Returns:
            Dictionary mapping status names to block names (discovery/delivery)
        """
        try:
            mapping_file = Path("data/config/status_order.txt")
            if not mapping_file.exists():
                logger.warning(f"Status mapping file not found: {mapping_file}")
                return {}

            status_mapping = {}
            with open(mapping_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and ";" in line:
                        status, block = line.split(";", 1)
                        status_mapping[status.strip()] = block.strip()

            logger.info(f"Loaded {len(status_mapping)} status mappings")
            return status_mapping

        except Exception as e:
            logger.error(f"Failed to load status mapping: {e}")
            return {}

    def generate_report_data(self) -> Dict[str, Dict[str, int]]:
        """
        Generate report data for CPO tasks over last 2 weeks with hidden week 3 for dynamics.

        Returns:
            Dictionary with week data
        """
        now = datetime.now(timezone.utc)

        # Calculate week boundaries
        # Week 1: Last week (7 days ago to today)
        week1_end = now
        week1_start = week1_end - timedelta(days=7)

        # Week 2: Week before last (14 days ago to 7 days ago)
        week2_end = week1_start
        week2_start = week2_end - timedelta(days=7)

        # Week 3: Hidden week for dynamics (21 days ago to 14 days ago)
        week3_end = week2_start
        week3_start = week3_end - timedelta(days=7)

        # Store date ranges for display (only weeks 1 and 2)
        self.week1_start = week1_start
        self.week1_end = week1_end
        self.week2_start = week2_start
        self.week2_end = week2_end

        logger.info(f"Generating CPO tasks report for:")
        logger.info(f"  Week 1: {week1_start.date()} to {week1_end.date()}")
        logger.info(f"  Week 2: {week2_start.date()} to {week2_end.date()}")
        logger.info(f"  Week 3 (hidden): {week3_start.date()} to {week3_end.date()}")

        # Get data for each week
        self.week1_data = self.get_status_changes_by_group(week1_start, week1_end)
        self.week2_data = self.get_status_changes_by_group(week2_start, week2_end)
        self.week3_data = self.get_status_changes_by_group(
            week3_start, week3_end
        )  # Hidden week for dynamics

        # Get current open tasks data
        self.open_tasks_data = self.get_open_tasks_by_group()

        # Combine all unique authors/teams
        if self.group_by == "author":
            # For author grouping, combine all authors
            all_groups = (
                set(self.week1_data.keys())
                | set(self.week2_data.keys())
                | set(self.week3_data.keys())
                | set(self.open_tasks_data.keys())
            )
        else:  # team
            # For team grouping, only show teams (not individual authors)
            # Get all teams from the mapping service
            if self.author_team_mapping_service:
                all_teams = set(self.author_team_mapping_service.get_all_teams())
                # Filter to only include teams that have data
                all_groups = set()
                for team in all_teams:
                    if (
                        team in self.week1_data
                        or team in self.week2_data
                        or team in self.week3_data
                        or team in self.open_tasks_data
                    ):
                        all_groups.add(team)
            else:
                all_groups = set()

        # Build report data with changes, tasks counts, and open tasks by blocks
        # Note: week2 is earlier (left), week1 is later (right)
        # Week 3 is hidden but used for dynamics arrows
        self.report_data = {}
        for group_value in sorted(all_groups):
            week3_data = self.week3_data.get(
                group_value, {"changes": 0, "tasks": 0}
            )  # Hidden week
            week2_data = self.week2_data.get(group_value, {"changes": 0, "tasks": 0})
            week1_data = self.week1_data.get(group_value, {"changes": 0, "tasks": 0})
            open_tasks_data = self.open_tasks_data.get(
                group_value, {"discovery": 0, "delivery": 0}
            )

            # Check if all counts are zero - if so, skip this group
            total_changes = (
                week3_data["changes"] + week2_data["changes"] + week1_data["changes"]
            )
            total_tasks = (
                week3_data["tasks"] + week2_data["tasks"] + week1_data["tasks"]
            )
            total_open_tasks = (
                open_tasks_data["discovery"] + open_tasks_data["delivery"]
            )

            if total_changes == 0 and total_tasks == 0 and total_open_tasks == 0:
                continue  # Skip groups with all zero counts

            self.report_data[group_value] = {
                "week3_changes": week3_data["changes"],  # Hidden week for dynamics
                "week3_tasks": week3_data["tasks"],  # Hidden week for dynamics
                "week2_changes": week2_data["changes"],
                "week2_tasks": week2_data["tasks"],
                "week1_changes": week1_data["changes"],
                "week1_tasks": week1_data["tasks"],
                "discovery_tasks": open_tasks_data["discovery"],
                "delivery_tasks": open_tasks_data["delivery"],
                "discovery_last_change": open_tasks_data.get("discovery_last_change"),
                "delivery_last_change": open_tasks_data.get("delivery_last_change"),
            }

        group_name = "authors" if self.group_by == "author" else "teams"
        logger.info(f"Generated report for {len(self.report_data)} {group_name}")
        return self.report_data

    def save_csv_report(self) -> str:
        """
        Save report data to CSV file with dynamics indicators.

        Returns:
            Path to saved CSV file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"status_change_report_{timestamp}.csv"

        # Ensure reports directory exists
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        filepath = reports_dir / filename

        try:
            # Format dates for column headers
            week2_header = f"{self.week2_start.strftime('%d.%m')}-{self.week2_end.strftime('%d.%m')}"
            week1_header = f"{self.week1_start.strftime('%d.%m')}-{self.week1_end.strftime('%d.%m')}"

            # Determine column header based on grouping
            group_header = "Автор" if self.group_by == "author" else "Команда"

            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = [
                    group_header,
                    f"{week2_header}_активность",
                    f"{week1_header}_активность",
                    "Discovery",
                    "Delivery",
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for group_value, data in self.report_data.items():
                    writer.writerow(
                        {
                            group_header: group_value,
                            f"{week2_header}_активность": f"{data['week2_changes']} изменений ({data['week2_tasks']} задач)",
                            f"{week1_header}_активность": f"{data['week1_changes']} изменений ({data['week1_tasks']} задач)",
                            "Discovery": f"{data['discovery_tasks']}",
                            "Delivery": f"{data['delivery_tasks']}",
                        }
                    )

            logger.info(f"CSV report saved to: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to save CSV report: {e}")
            raise

    def generate_table(self) -> str:
        """
        Generate table visualization of the report data.

        Returns:
            Path to saved table image
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"status_change_table_{timestamp}.png"

        # Ensure reports directory exists
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        filepath = reports_dir / filename

        try:
            # Prepare data for table
            groups = list(self.report_data.keys())
            week3_changes = [
                self.report_data[group]["week3_changes"] for group in groups
            ]  # Hidden week changes
            week3_tasks = [
                self.report_data[group]["week3_tasks"] for group in groups
            ]  # Hidden week tasks
            week2_changes = [
                self.report_data[group]["week2_changes"] for group in groups
            ]  # Earlier week changes
            week2_tasks = [
                self.report_data[group]["week2_tasks"] for group in groups
            ]  # Earlier week tasks
            week1_changes = [
                self.report_data[group]["week1_changes"] for group in groups
            ]  # Later week changes
            week1_tasks = [
                self.report_data[group]["week1_tasks"] for group in groups
            ]  # Later week tasks
            discovery_tasks = [
                self.report_data[group]["discovery_tasks"] for group in groups
            ]  # Discovery tasks
            delivery_tasks = [
                self.report_data[group]["delivery_tasks"] for group in groups
            ]  # Delivery tasks

            # Format dates for column headers
            week2_header = f"{self.week2_start.strftime('%d.%m')}-{self.week2_end.strftime('%d.%m')}"
            week1_header = f"{self.week1_start.strftime('%d.%m')}-{self.week1_end.strftime('%d.%m')}"

            # Use adaptive sizing based on content (inspired by TTM approach)
            # Calculate base dimensions
            num_rows = len(groups) + 1  # +1 for header
            num_cols = 5

            # Set adaptive figure size with protection against extreme sizes
            fig_width = max(8, num_cols * 0.9 + 2)  # Adaptive width based on columns
            max_height = 20  # Protection against extremely tall images

            if self.group_by == "team":
                # For teams: larger cells, more readable
                fig_height = min(max_height, max(4, num_rows * 0.12 + 1))
            else:
                # For authors: compact cells, fit more data
                fig_height = min(max_height, max(6, num_rows * 0.04 + 1))

            fig = plt.figure(figsize=(fig_width, fig_height))

            # Create axis with padding around table
            padding = 0.05  # 5% padding around table
            ax = fig.add_axes([padding, padding, 1 - 2 * padding, 1 - 2 * padding])
            ax.axis("off")

            # Create table data with changes, tasks, and tasks by blocks
            table_data = []
            for i, (
                group_value,
                w3_ch,
                w3_t,
                w2_ch,
                w2_t,
                w1_ch,
                w1_t,
                disc,
                deliv,
            ) in enumerate(
                zip(
                    groups,
                    week3_changes,
                    week3_tasks,
                    week2_changes,
                    week2_tasks,
                    week1_changes,
                    week1_tasks,
                    discovery_tasks,
                    delivery_tasks,
                )
            ):
                table_data.append(
                    [
                        group_value,
                        f"{w2_ch} изменений ({w2_t} задач)",
                        f"{w1_ch} изменений ({w1_t} задач)",
                        f"{disc}",
                        f"{deliv}",
                    ]
                )

            # Create table positioned in the center of the axis
            group_header = "Автор" if self.group_by == "author" else "Команда"
            table = ax.table(
                cellText=table_data,
                colLabels=[
                    group_header,
                    f"{week2_header} | активность",
                    f"{week1_header} | активность",
                    "Discovery",
                    "Delivery",
                ],
                cellLoc="center",
                loc="center",
                colWidths=[0.25, 0.21, 0.21, 0.08, 0.08],
            )  # Adjusted widths for 5 columns (activity columns reduced by 30%)

            # Style the table with adaptive settings (inspired by TTM approach)
            table.auto_set_font_size(False)

            # Adaptive font size and scaling based on data size
            font_size = 5 if len(groups) > 30 else (8 if self.group_by == "team" else 6)
            table.set_fontsize(font_size)

            # Adaptive scaling for large datasets
            scale_y = (
                0.8 if len(groups) > 30 else (1.2 if self.group_by == "team" else 1.0)
            )
            table.scale(1.0, scale_y)

            # Set cell dimensions adaptively
            cell_height = 0.05 if self.group_by == "team" else 0.03
            cell_padding = 0.05 if self.group_by == "team" else 0.03

            for i in range(len(table_data) + 1):
                for j in range(5):
                    cell = table[(i, j)]
                    cell.set_height(cell_height)
                    cell.PAD = cell_padding

            # Style header row
            for i in range(5):
                table[(0, i)].set_facecolor("#4CAF50")
                table[(0, i)].set_text_props(weight="bold", color="white")

            # Style data rows
            for i in range(1, len(table_data) + 1):
                for j in range(5):
                    cell = table[(i, j)]
                    if i % 2 == 0:  # Alternate row colors
                        cell.set_facecolor("#F5F5F5")
                    else:
                        cell.set_facecolor("#FFFFFF")

                    # Left align text for Author column, center for data columns
                    if j == 0:  # Author column
                        cell.set_text_props(ha="left", va="center")
                    else:  # Data columns
                        cell.set_text_props(ha="center", va="center")

            # No title - clean table only

            # Save with minimal margins - use tight layout to avoid cropping
            plt.savefig(
                filepath,
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
                pad_inches=0.1,
                edgecolor="none",
                transparent=False,
            )
            plt.close()

            logger.info(f"Table saved to: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to generate table: {e}")
            raise

    def print_summary(self):
        """Print summary of the report to console."""
        if not self.report_data:
            logger.warning(
                "No report data available. Run generate_report_data() first."
            )
            return

        print("\n" + "=" * 80)
        group_name = "AUTHORS" if self.group_by == "author" else "TEAMS"
        print(f"CPO TASKS STATUS CHANGE REPORT BY {group_name} - LAST 2 WEEKS")
        print("=" * 80)

        # Calculate totals
        total_week1_changes = sum(
            data["week1_changes"] for data in self.report_data.values()
        )
        total_week1_tasks = sum(
            data["week1_tasks"] for data in self.report_data.values()
        )
        total_week2_changes = sum(
            data["week2_changes"] for data in self.report_data.values()
        )
        total_week2_tasks = sum(
            data["week2_tasks"] for data in self.report_data.values()
        )
        total_discovery_tasks = sum(
            data["discovery_tasks"] for data in self.report_data.values()
        )
        total_delivery_tasks = sum(
            data["delivery_tasks"] for data in self.report_data.values()
        )

        # Format dates for display
        week2_header = (
            f"{self.week2_start.strftime('%d.%m')}-{self.week2_end.strftime('%d.%m')}"
        )
        week1_header = (
            f"{self.week1_start.strftime('%d.%m')}-{self.week1_end.strftime('%d.%m')}"
        )

        print(
            f"Total Status Changes - {week1_header}: {total_week1_changes} across {total_week1_tasks} tasks"
        )
        print(
            f"Total Status Changes - {week2_header}: {total_week2_changes} across {total_week2_tasks} tasks"
        )
        print(f"Total Discovery Tasks: {total_discovery_tasks}")
        print(f"Total Delivery Tasks: {total_delivery_tasks}")
        group_name = "Authors" if self.group_by == "author" else "Teams"
        print(f"Number of {group_name}: {len(self.report_data)}")
        print("-" * 80)

        # Print by author/team with combined activity data
        group_header = "Author" if self.group_by == "author" else "Team"
        print(
            f"{group_header:<25} {week2_header:<35} {week1_header:<35} {'Discovery':<15} {'Delivery':<15}"
        )
        print("-" * 110)

        for group_value, data in sorted(self.report_data.items(), key=lambda x: x[0]):
            week2_str = (
                f"{data['week2_changes']} изменений ({data['week2_tasks']} задач)"
            )
            week1_str = (
                f"{data['week1_changes']} изменений ({data['week1_tasks']} задач)"
            )

            discovery_str = f"{data['discovery_tasks']}"
            delivery_str = f"{data['delivery_tasks']}"
            print(
                f"{group_value:<25} {week2_str:<35} {week1_str:<35} {discovery_str:<15} {delivery_str:<15}"
            )

        print("=" * 80)

    def run(self) -> bool:
        """
        Run the complete report generation process.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Starting CPO tasks status change report generation...")

            # Generate report data
            self.generate_report_data()

            if not self.report_data:
                logger.warning("No data found for the specified time period")
                return False

            # Print summary to console
            self.print_summary()

            # Save CSV report
            csv_path = self.save_csv_report()
            logger.info(f"CSV report saved: {csv_path}")

            # Generate table
            table_path = self.generate_table()
            logger.info(f"Table saved: {table_path}")

            logger.info("Status change report generation completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to generate status change report: {e}")
            return False


def main():
    """Main entry point for command line execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate CPO tasks status change report for last 2 weeks"
    )
    parser.add_argument(
        "--group-by",
        choices=["author", "team"],
        default="author",
        help="Group by author or team (default: author)",
    )
    parser.add_argument(
        "--config-dir",
        default="data/config",
        help="Configuration directory path (default: data/config)",
    )

    args = parser.parse_args()

    with GenerateStatusChangeReportCommand(
        group_by=args.group_by, config_dir=args.config_dir
    ) as cmd:
        success = cmd.run()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
