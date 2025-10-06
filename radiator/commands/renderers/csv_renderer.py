"""CSV renderer for Time To Market report."""

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from radiator.commands.models.time_to_market_models import (
    ReportType,
    TimeToMarketReport,
)
from radiator.commands.renderers.base_renderer import BaseRenderer
from radiator.core.logging import logger


class CSVRenderer(BaseRenderer):
    """CSV renderer for Time To Market report."""

    def render(
        self, filepath: Optional[str] = None, report_type: ReportType = ReportType.BOTH
    ) -> str:
        """
        Render report to CSV file.

        Args:
            filepath: Output file path (optional)
            report_type: Type of report to render

        Returns:
            Path to generated CSV file
        """
        try:
            if not filepath:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if report_type == ReportType.TTD:
                    filepath = (
                        f"{self.output_dir}/time_to_delivery_report_{timestamp}.csv"
                    )
                elif report_type == ReportType.TTM:
                    filepath = (
                        f"{self.output_dir}/time_to_market_report_{timestamp}.csv"
                    )
                else:
                    filepath = (
                        f"{self.output_dir}/time_to_market_report_{timestamp}.csv"
                    )

            # Ensure reports directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            quarters = self._get_quarters()
            all_groups = self._get_all_groups()

            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                # Create dynamic fieldnames based on quarters and report type
                fieldnames = ["group_name"]
                for quarter in quarters:
                    if report_type in [ReportType.TTD, ReportType.BOTH]:
                        fieldnames.extend(
                            [
                                f"{quarter}_ttd_mean",
                                f"{quarter}_ttd_p85",
                                f"{quarter}_ttd_tasks",
                                f"{quarter}_ttd_pause_mean",
                                f"{quarter}_ttd_pause_p85",
                            ]
                        )
                    if report_type in [ReportType.TTM, ReportType.BOTH]:
                        fieldnames.extend(
                            [
                                f"{quarter}_ttm_mean",
                                f"{quarter}_ttm_p85",
                                f"{quarter}_ttm_tasks",
                                f"{quarter}_ttm_pause_mean",
                                f"{quarter}_ttm_pause_p85",
                                f"{quarter}_tail_mean",
                                f"{quarter}_tail_p85",
                                f"{quarter}_tail_tasks",
                            ]
                        )

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for group_name in all_groups:
                    row = {"group_name": group_name}

                    for quarter in quarters:
                        quarter_report = self.report.quarter_reports.get(quarter)
                        group_metrics = (
                            quarter_report.groups.get(group_name)
                            if quarter_report
                            else None
                        )

                        if group_metrics:
                            if report_type in [ReportType.TTD, ReportType.BOTH]:
                                row.update(
                                    {
                                        f"{quarter}_ttd_mean": group_metrics.ttd_metrics.mean,
                                        f"{quarter}_ttd_p85": group_metrics.ttd_metrics.p85,
                                        f"{quarter}_ttd_tasks": group_metrics.ttd_metrics.count,
                                        f"{quarter}_ttd_pause_mean": group_metrics.ttd_metrics.pause_mean,
                                        f"{quarter}_ttd_pause_p85": group_metrics.ttd_metrics.pause_p85,
                                    }
                                )
                            if report_type in [ReportType.TTM, ReportType.BOTH]:
                                row.update(
                                    {
                                        f"{quarter}_ttm_mean": group_metrics.ttm_metrics.mean,
                                        f"{quarter}_ttm_p85": group_metrics.ttm_metrics.p85,
                                        f"{quarter}_ttm_tasks": group_metrics.ttm_metrics.count,
                                        f"{quarter}_ttm_pause_mean": group_metrics.ttm_metrics.pause_mean,
                                        f"{quarter}_ttm_pause_p85": group_metrics.ttm_metrics.pause_p85,
                                        f"{quarter}_tail_mean": group_metrics.tail_metrics.mean,
                                        f"{quarter}_tail_p85": group_metrics.tail_metrics.p85,
                                        f"{quarter}_tail_tasks": group_metrics.tail_metrics.count,
                                    }
                                )
                        else:
                            if report_type in [ReportType.TTD, ReportType.BOTH]:
                                row.update(
                                    {
                                        f"{quarter}_ttd_mean": "",
                                        f"{quarter}_ttd_p85": "",
                                        f"{quarter}_ttd_tasks": "",
                                        f"{quarter}_ttd_pause_mean": "",
                                        f"{quarter}_ttd_pause_p85": "",
                                    }
                                )
                            if report_type in [ReportType.TTM, ReportType.BOTH]:
                                row.update(
                                    {
                                        f"{quarter}_ttm_mean": "",
                                        f"{quarter}_ttm_p85": "",
                                        f"{quarter}_ttm_tasks": "",
                                        f"{quarter}_ttm_pause_mean": "",
                                        f"{quarter}_ttm_pause_p85": "",
                                        f"{quarter}_tail_mean": "",
                                        f"{quarter}_tail_p85": "",
                                        f"{quarter}_tail_tasks": "",
                                    }
                                )

                    writer.writerow(row)

            logger.info(f"CSV report saved to: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to generate CSV: {e}")
            raise
