"""Console renderer for Time To Market report."""

from typing import Optional
from radiator.commands.models.time_to_market_models import TimeToMarketReport, ReportType
from radiator.commands.renderers.base_renderer import BaseRenderer


class ConsoleRenderer(BaseRenderer):
    """Console renderer for Time To Market report."""
    
    def render(self, filepath: Optional[str] = None, report_type: ReportType = ReportType.BOTH) -> str:
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
        
        print("\n" + "="*120)
        group_name = "AUTHORS" if self.report.group_by.value == "author" else "TEAMS"
        
        if report_type == ReportType.TTD:
            title = f"TIME TO DELIVERY REPORT BY {group_name}"
        elif report_type == ReportType.TTM:
            title = f"TIME TO MARKET REPORT BY {group_name}"
        else:
            title = f"TIME TO DELIVERY & TIME TO MARKET REPORT BY {group_name}"
        
        print(title)
        print("="*120)
        
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
            print("Time To Delivery (days):")
            print(f"{'':<25}", end="")
            for quarter in quarters:
                print(f"{'Avg':>8} {'85%':>8} {'Tasks':>4}", end="")
            print()
            
            for group in all_groups:
                line = f"{group:<25}"
                for quarter in quarters:
                    quarter_report = self.report.quarter_reports.get(quarter)
                    group_metrics = quarter_report.groups.get(group) if quarter_report else None
                    if group_metrics:
                        ttd_avg = group_metrics.ttd_metrics.mean or 0
                        ttd_p85 = group_metrics.ttd_metrics.p85 or 0
                        tasks = group_metrics.ttd_metrics.count
                        line += f"{ttd_avg:>8.1f}{ttd_p85:>8.1f}{tasks:>4}"
                    else:
                        line += f"{'':>8}{'':>8}{'':>4}"
                print(line)
            
            print()
        
        # Print TTM section if needed
        if report_type in [ReportType.TTM, ReportType.BOTH]:
            print("Time To Market (days):")
            print(f"{'':<25}", end="")
            for quarter in quarters:
                print(f"{'Avg':>8} {'85%':>8} {'Tasks':>4}", end="")
            print()
            
            for group in all_groups:
                line = f"{group:<25}"
                for quarter in quarters:
                    quarter_report = self.report.quarter_reports.get(quarter)
                    group_metrics = quarter_report.groups.get(group) if quarter_report else None
                    if group_metrics:
                        ttm_avg = group_metrics.ttm_metrics.mean or 0
                        ttm_p85 = group_metrics.ttm_metrics.p85 or 0
                        tasks = group_metrics.ttm_metrics.count
                        line += f"{ttm_avg:>8.1f}{ttm_p85:>8.1f}{tasks:>4}"
                    else:
                        line += f"{'':>8}{'':>8}{'':>4}"
                print(line)
        
        # Print totals
        print("-" * 120)
        print(f"Total tasks analyzed: {self.report.total_tasks}")
        print("="*120)
        
        return ""
