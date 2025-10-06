"""Table renderer for Time To Market report."""

from datetime import datetime
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt

from radiator.commands.models.time_to_market_models import (
    ReportType,
    TimeToMarketReport,
)
from radiator.commands.renderers.base_renderer import BaseRenderer
from radiator.core.logging import logger


class TableRenderer(BaseRenderer):
    """Table renderer for Time To Market report."""

    def render(
        self, filepath: Optional[str] = None, report_type: ReportType = ReportType.BOTH
    ) -> str:
        """
        Render report to table image file.

        Args:
            filepath: Output file path (optional)
            report_type: Type of report to render

        Returns:
            Path to generated table file
        """
        try:
            if not filepath:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if report_type == ReportType.TTD:
                    filepath = f"{self.output_dir}/TTD_table_{timestamp}.png"
                elif report_type == ReportType.TTM:
                    filepath = f"{self.output_dir}/TTM_table_{timestamp}.png"
                else:
                    filepath = f"{self.output_dir}/TTM_table_{timestamp}.png"

            # Ensure reports directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            quarters = self._get_quarters()
            all_groups = self._get_all_groups()

            if not all_groups:
                logger.warning("No data to display in table")
                return ""

            # Create table - optimized for smaller file size
            fig_width = max(8, len(quarters) * 0.9 + 2)
            # Limit height for very large datasets to prevent extremely tall images
            max_height = 20
            fig_height = min(max_height, max(6, len(all_groups) * 0.15 + 2))

            # Adjust height based on report type
            if report_type == ReportType.BOTH:
                fig_height = min(max_height, max(8, len(all_groups) * 0.2 + 4))

            fig = plt.figure(figsize=(fig_width, fig_height))

            # Determine which sections to show
            show_ttd = report_type in [ReportType.TTD, ReportType.BOTH]
            show_ttm = report_type in [ReportType.TTM, ReportType.BOTH]

            # Calculate layout based on what we're showing
            if report_type == ReportType.BOTH:
                # Show TTD, TTM+Tail in two sections
                ax1 = fig.add_axes([0.05, 0.55, 0.9, 0.35])  # TTD
                ax2 = fig.add_axes([0.05, 0.1, 0.9, 0.35])  # TTM+Tail
                ax3 = None
            elif report_type == ReportType.TTD:
                ax1 = fig.add_axes([0.05, 0.1, 0.9, 0.8])
                ax2 = None
                ax3 = None
            elif report_type == ReportType.TTM:
                ax1 = None
                ax2 = fig.add_axes([0.05, 0.1, 0.9, 0.8])  # TTM+Tail
                ax3 = None

            # TTD section
            if show_ttd and ax1:
                ax1.axis("off")
                self._render_ttd_table(ax1, quarters, all_groups)

            # TTM section (now includes Tail columns)
            if show_ttm and ax2:
                ax2.axis("off")
                self._render_ttm_with_tail_table(ax2, quarters, all_groups)

            # Main title
            title = self._get_title(report_type)
            fig.suptitle(title, fontsize=12, fontweight="bold", y=0.95)

            # Save with optimized settings for smaller file size
            plt.savefig(
                filepath,
                dpi=150,
                bbox_inches="tight",
                facecolor="white",
                pad_inches=0.1,
                edgecolor="none",
                transparent=False,
            )
            plt.close()

            logger.info(f"Table saved to: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to generate table: {e}")
            raise

    def _render_ttd_table(self, ax, quarters: list, all_groups: list):
        """Render TTD table section."""
        # Prepare data with proper structure
        ttd_table_data = []
        for group in all_groups:
            row = [group]
            for quarter in quarters:
                quarter_report = self.report.quarter_reports.get(quarter)
                group_metrics = (
                    quarter_report.groups.get(group) if quarter_report else None
                )
                if group_metrics:
                    ttd_avg = group_metrics.ttd_metrics.mean or 0
                    ttd_p85 = group_metrics.ttd_metrics.p85 or 0
                    tasks = group_metrics.ttd_metrics.count
                    pause_avg = group_metrics.ttd_metrics.pause_mean or 0
                    pause_p85 = group_metrics.ttd_metrics.pause_p85 or 0
                    row.extend(
                        [
                            f"{ttd_avg:.1f}",
                            f"{ttd_p85:.1f}",
                            str(tasks),
                            f"{pause_avg:.1f}",
                            f"{pause_p85:.1f}",
                        ]
                    )
                else:
                    row.extend(["", "", "", "", ""])
            ttd_table_data.append(row)

        # Create headers
        ttd_headers = ["Group"]
        for quarter in quarters:
            ttd_headers.extend(
                [
                    f"{quarter}\nAvg",
                    f"{quarter}\n85%",
                    f"{quarter}\nTasks",
                    f"{quarter}\nPause Avg",
                    f"{quarter}\nPause 85%",
                ]
            )

        # Create table
        ttd_table = ax.table(
            cellText=ttd_table_data,
            colLabels=ttd_headers,
            cellLoc="center",
            loc="center",
            colWidths=[0.15] + [0.14 / len(quarters)] * (len(quarters) * 5),
        )

        # Style TTD table
        self._style_table(
            ttd_table, len(ttd_headers), len(ttd_table_data), all_groups, "#4CAF50"
        )
        ax.set_title(
            "Time To Delivery (days) - Excluding Pause Time",
            fontsize=12,
            fontweight="bold",
            pad=10,
        )

    def _render_ttm_table(self, ax, quarters: list, all_groups: list):
        """Render TTM table section."""
        # Prepare data with proper structure
        ttm_table_data = []
        for group in all_groups:
            row = [group]
            for quarter in quarters:
                quarter_report = self.report.quarter_reports.get(quarter)
                group_metrics = (
                    quarter_report.groups.get(group) if quarter_report else None
                )
                if group_metrics:
                    ttm_avg = group_metrics.ttm_metrics.mean or 0
                    ttm_p85 = group_metrics.ttm_metrics.p85 or 0
                    tasks = group_metrics.ttm_metrics.count
                    pause_avg = group_metrics.ttm_metrics.pause_mean or 0
                    pause_p85 = group_metrics.ttm_metrics.pause_p85 or 0
                    row.extend(
                        [
                            f"{ttm_avg:.1f}",
                            f"{ttm_p85:.1f}",
                            str(tasks),
                            f"{pause_avg:.1f}",
                            f"{pause_p85:.1f}",
                        ]
                    )
                else:
                    row.extend(["", "", "", "", ""])
            ttm_table_data.append(row)

        # Create headers
        ttm_headers = ["Group"]
        for quarter in quarters:
            ttm_headers.extend(
                [
                    f"{quarter}\nAvg",
                    f"{quarter}\n85%",
                    f"{quarter}\nTasks",
                    f"{quarter}\nPause Avg",
                    f"{quarter}\nPause 85%",
                ]
            )

        # Create table
        ttm_table = ax.table(
            cellText=ttm_table_data,
            colLabels=ttm_headers,
            cellLoc="center",
            loc="center",
            colWidths=[0.15] + [0.14 / len(quarters)] * (len(quarters) * 5),
        )

        # Style TTM table
        self._style_table(
            ttm_table, len(ttm_headers), len(ttm_table_data), all_groups, "#2196F3"
        )
        ax.set_title(
            "Time To Market (days) - Excluding Pause Time",
            fontsize=12,
            fontweight="bold",
            pad=10,
        )

    def _render_ttm_with_tail_table(self, ax, quarters: list, all_groups: list):
        """Render TTM table section with Tail columns."""
        # Prepare data with proper structure
        ttm_tail_table_data = []
        for group in all_groups:
            row = [group]
            for quarter in quarters:
                quarter_report = self.report.quarter_reports.get(quarter)
                group_metrics = (
                    quarter_report.groups.get(group) if quarter_report else None
                )
                if group_metrics:
                    # TTM columns
                    if group_metrics.ttm_metrics.count > 0:
                        ttm_avg = group_metrics.ttm_metrics.mean or 0
                        ttm_p85 = group_metrics.ttm_metrics.p85 or 0
                        ttm_tasks = group_metrics.ttm_metrics.count
                        ttm_pause_avg = group_metrics.ttm_metrics.pause_mean or 0
                        ttm_pause_p85 = group_metrics.ttm_metrics.pause_p85 or 0
                        ttm_values = [
                            f"{ttm_avg:.1f}",
                            f"{ttm_p85:.1f}",
                            str(ttm_tasks),
                            f"{ttm_pause_avg:.1f}",
                            f"{ttm_pause_p85:.1f}",
                        ]
                    else:
                        ttm_values = ["", "", "", "", ""]

                    # Tail columns
                    if group_metrics.tail_metrics.count > 0:
                        tail_avg = group_metrics.tail_metrics.mean or 0
                        tail_p85 = group_metrics.tail_metrics.p85 or 0
                        tail_tasks = group_metrics.tail_metrics.count
                        tail_values = [
                            f"{tail_avg:.1f}",
                            f"{tail_p85:.1f}",
                            str(tail_tasks),
                        ]
                    else:
                        tail_values = ["", "", ""]

                    row.extend(ttm_values + tail_values)
                else:
                    row.extend(["", "", "", "", "", "", "", ""])
            ttm_tail_table_data.append(row)

        # Create headers
        ttm_tail_headers = ["Group"]
        for quarter in quarters:
            ttm_tail_headers.extend(
                [
                    f"{quarter}\nTTM Avg",
                    f"{quarter}\nTTM 85%",
                    f"{quarter}\nTTM Tasks",
                    f"{quarter}\nTTM Pause Avg",
                    f"{quarter}\nTTM Pause 85%",
                    f"{quarter}\nTail Avg",
                    f"{quarter}\nTail 85%",
                    f"{quarter}\nTail Tasks",
                ]
            )

        # Create table
        ttm_tail_table = ax.table(
            cellText=ttm_tail_table_data,
            colLabels=ttm_tail_headers,
            cellLoc="center",
            loc="center",
            colWidths=[0.15] + [0.14 / len(quarters)] * (len(quarters) * 8),
        )

        # Style TTM+Tail table
        self._style_table(
            ttm_tail_table,
            len(ttm_tail_headers),
            len(ttm_tail_table_data),
            all_groups,
            "#4CAF50",
        )
        ax.set_title(
            "Time To Market & Tail (TTM: Discovery to Done, Tail: MP/External Test to Done) - Excluding Pause Time",
            fontsize=12,
            fontweight="bold",
            pad=10,
        )

    def _render_tail_table(self, ax, quarters: list, all_groups: list):
        """Render Tail table section."""
        # Prepare data with proper structure
        tail_table_data = []
        for group in all_groups:
            row = [group]
            for quarter in quarters:
                quarter_report = self.report.quarter_reports.get(quarter)
                group_metrics = (
                    quarter_report.groups.get(group) if quarter_report else None
                )
                if group_metrics and group_metrics.tail_metrics.count > 0:
                    tail_avg = group_metrics.tail_metrics.mean or 0
                    tail_p85 = group_metrics.tail_metrics.p85 or 0
                    tasks = group_metrics.tail_metrics.count
                    row.extend(
                        [
                            f"{tail_avg:.1f}",
                            f"{tail_p85:.1f}",
                            str(tasks),
                        ]
                    )
                else:
                    row.extend(["N/A", "N/A", "0"])
            tail_table_data.append(row)

        # Create headers
        tail_headers = ["Group"]
        for quarter in quarters:
            tail_headers.extend(
                [
                    f"{quarter}\nAvg",
                    f"{quarter}\n85%",
                    f"{quarter}\nTasks",
                ]
            )

        # Create table
        tail_table = ax.table(
            cellText=tail_table_data,
            colLabels=tail_headers,
            cellLoc="center",
            loc="center",
            colWidths=[0.15] + [0.14 / len(quarters)] * (len(quarters) * 3),
        )

        # Style Tail table
        self._style_table(
            tail_table, len(tail_headers), len(tail_table_data), all_groups, "#FF9800"
        )
        ax.set_title(
            "Tail (days from MP/External Test to Done) - Excluding Pause Time",
            fontsize=12,
            fontweight="bold",
            pad=10,
        )

    def _style_table(
        self,
        table,
        num_headers: int,
        num_rows: int,
        all_groups: list,
        header_color: str,
    ):
        """Style table with colors and formatting."""
        table.auto_set_font_size(False)
        # Use smaller font for large datasets
        font_size = 5 if len(all_groups) > 30 else 6
        table.set_fontsize(font_size)
        # Reduce scaling for large datasets
        scale_y = 0.8 if len(all_groups) > 30 else 1.2
        table.scale(1.0, scale_y)

        # Define column group colors (subtle background highlighting)
        column_colors = {
            "group": "#F8F9FA",  # Very light gray for group column
            "avg": "#F0F8FF",  # Very light blue for average columns
            "p85": "#F0FFF0",  # Very light green for 85th percentile columns
            "tasks": "#FFF8F0",  # Very light orange for task count columns
            "pause_avg": "#FFF0F8",  # Very light pink for pause average columns
            "pause_p85": "#F8F0FF",  # Very light purple for pause 85th percentile columns
        }

        # Style header row
        for i in range(num_headers):
            table[(0, i)].set_facecolor(header_color)
            table[(0, i)].set_text_props(weight="bold", color="white")

        # Style data rows with column-based highlighting
        for i in range(1, num_rows + 1):
            for j in range(num_headers):
                cell = table[(i, j)]

                # Determine column type based on position
                if j == 0:  # Group column
                    base_color = column_colors["group"]
                    cell.set_text_props(ha="left", va="center")
                else:
                    # Calculate column group based on position (assuming 5 columns per quarter: avg, p85, tasks, pause_avg, pause_p85)
                    col_in_quarter = (j - 1) % 5
                    if col_in_quarter == 0:  # Average column
                        base_color = column_colors["avg"]
                    elif col_in_quarter == 1:  # 85th percentile column
                        base_color = column_colors["p85"]
                    elif col_in_quarter == 2:  # Tasks column
                        base_color = column_colors["tasks"]
                    elif col_in_quarter == 3:  # Pause average column
                        base_color = column_colors["pause_avg"]
                    elif col_in_quarter == 4:  # Pause 85th percentile column
                        base_color = column_colors["pause_p85"]
                    else:
                        base_color = "#FFFFFF"

                    cell.set_text_props(ha="center", va="center")

                # Apply alternating row highlighting on top of column colors
                if i % 2 == 0:
                    # Darken the base color slightly for even rows
                    cell.set_facecolor(self._darken_color(base_color, 0.05))
                else:
                    cell.set_facecolor(base_color)

    def _darken_color(self, hex_color: str, factor: float) -> str:
        """Darken a hex color by a factor (0-1)."""
        # Remove # if present
        hex_color = hex_color.lstrip("#")

        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # Darken by factor
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))

        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"

    def _get_title(self, report_type: ReportType) -> str:
        """Get title for the report."""
        group_name = self.report.group_by.value.title()

        if report_type == ReportType.TTD:
            return f"Time To Delivery Report - {group_name} Grouping"
        elif report_type == ReportType.TTM:
            return f"Time To Market & Tail Report - {group_name} Grouping"
        else:
            return f"Time To Delivery, Time To Market & Tail Report - {group_name} Grouping"
