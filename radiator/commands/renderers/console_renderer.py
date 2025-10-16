"""Console renderer for Time To Market report."""

from typing import Optional

from radiator.commands.models.time_to_market_models import (
    ReportType,
    TimeToMarketReport,
)
from radiator.commands.renderers.base_renderer import BaseRenderer


class ConsoleRenderer(BaseRenderer):
    """Console renderer for Time To Market report."""

    def render(
        self, filepath: Optional[str] = None, report_type: ReportType = ReportType.BOTH
    ) -> str:
        """
        Render report to console.

        Args:
            filepath: Not used for console output
            report_type: Type of report to render

        Returns:
            Empty string (console output)
        """
        if not self.report.quarter_reports:
            print("No report data available.")
            return ""

        print("\n" + "=" * 120)
        group_name = "AUTHORS" if self.report.group_by.value == "author" else "TEAMS"

        if report_type == ReportType.TTD:
            title = f"TIME TO DELIVERY REPORT BY {group_name}"
        elif report_type == ReportType.TTM:
            title = f"TIME TO MARKET & TAIL REPORT BY {group_name}"
        else:
            title = f"TIME TO DELIVERY, TIME TO MARKET & TAIL REPORT BY {group_name}"

        print(title)
        print("=" * 120)

        quarters = self._get_quarters()
        all_groups = self._get_all_groups()

        # Print header
        header = f"{'Group':<25}"
        for quarter in quarters:
            header += f"{quarter:>20}"
        print(header)
        print("-" * 120)

        # Print TTD section if needed
        if report_type in [ReportType.TTD, ReportType.BOTH]:
            print("Time To Delivery (days) - Excluding Pause Time:")
            print(f"{'':<25}", end="")
            for quarter in quarters:
                print(
                    f"{'Avg':>8} {'85%':>8} {'Tasks':>4} {'Pause Avg':>10} {'Pause 85%':>10}",
                    end="",
                )
            print()

            for group in all_groups:
                line = f"{group:<25}"
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
                        line += f"{ttd_avg:>8.1f}{ttd_p85:>8.1f}{tasks:>4}{pause_avg:>10.1f}{pause_p85:>10.1f}"
                    else:
                        line += f"{'':>8}{'':>8}{'':>4}{'':>10}{'':>10}"
                print(line)

            print()

        # Print TTM section if needed
        if report_type in [ReportType.TTM, ReportType.BOTH]:
            print("Time To Market (days) - Excluding Pause Time:")
            print(f"{'':<25}", end="")
            for quarter in quarters:
                print(
                    f"{'Avg':>8} {'85%':>8} {'Tasks':>4} {'Pause Avg':>10} {'Pause 85%':>10} {'Testing 85%':>12} {'External 85%':>12}",
                    end="",
                )
            print()

            for group in all_groups:
                line = f"{group:<25}"
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
                        testing_returns_p85 = (
                            group_metrics.ttm_metrics.testing_returns_p85 or 0
                        )
                        external_returns_p85 = (
                            group_metrics.ttm_metrics.external_test_returns_p85 or 0
                        )
                        line += f"{ttm_avg:>8.1f}{ttm_p85:>8.1f}{tasks:>4}{pause_avg:>10.1f}{pause_p85:>10.1f}{testing_returns_p85:>12.1f}{external_returns_p85:>12.1f}"
                    else:
                        line += f"{'':>8}{'':>8}{'':>4}{'':>10}{'':>10}{'':>12}{'':>12}"
                print(line)

            print()

        # Print Tail section if needed (only for TTM and BOTH)
        if report_type in [ReportType.TTM, ReportType.BOTH]:
            print("Tail (days from MP/External Test to Done) - Excluding Pause Time:")
            print(f"{'':<25}", end="")
            for quarter in quarters:
                print(f"{'Avg':>8} {'85%':>8} {'Tasks':>4}", end="")
            print()

            for group in all_groups:
                line = f"{group:<25}"
                for quarter in quarters:
                    quarter_report = self.report.quarter_reports.get(quarter)
                    group_metrics = (
                        quarter_report.groups.get(group) if quarter_report else None
                    )
                    if group_metrics:
                        tail_avg = group_metrics.tail_metrics.mean or 0
                        tail_p85 = group_metrics.tail_metrics.p85 or 0
                        tasks = group_metrics.tail_metrics.count
                        line += f"{tail_avg:>8.1f}{tail_p85:>8.1f}{tasks:>4}"
                    else:
                        line += f"{'':>8}{'':>8}{'':>4}"
                print(line)

        # Print totals
        print("-" * 120)
        print("=" * 120)

        return ""
