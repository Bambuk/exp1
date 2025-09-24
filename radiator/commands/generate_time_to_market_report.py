"""Refactored command for generating Time To Delivery and Time To Market report for CPO tasks by authors/teams over defined periods."""

import sys
from pathlib import Path
from typing import Optional
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.core.database import SessionLocal
from radiator.core.logging import logger
from radiator.commands.models.time_to_market_models import (
    TimeToMarketReport, QuarterReport, GroupMetrics, GroupBy, ReportType
)
from radiator.commands.services.config_service import ConfigService
from radiator.commands.services.data_service import DataService
from radiator.commands.services.metrics_service import MetricsService
from radiator.commands.renderers.csv_renderer import CSVRenderer
from radiator.commands.renderers.table_renderer import TableRenderer
from radiator.commands.renderers.console_renderer import ConsoleRenderer


class GenerateTimeToMarketReportCommand:
    """Refactored command for generating Time To Delivery and Time To Market report."""
    
    def __init__(self, group_by: GroupBy = GroupBy.AUTHOR, config_dir: str = "data/config"):
        """
        Initialize command with grouping preference.
        
        Args:
            group_by: Grouping type - AUTHOR or TEAM
            config_dir: Configuration directory path
        """
        self.group_by = group_by
        self.config_dir = config_dir
        self.db = SessionLocal()
        
        # Initialize services
        self.config_service = ConfigService(config_dir)
        self.data_service = DataService(self.db)
        self.metrics_service = MetricsService()
        
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
                    quarter_reports={}
                )
            
            if not status_mapping.discovery_statuses or not status_mapping.done_statuses:
                logger.warning("No target statuses found, returning empty report")
                return TimeToMarketReport(
                    quarters=quarters,
                    status_mapping=status_mapping,
                    group_by=self.group_by,
                    quarter_reports={}
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
                    metric_type="ttd"
                )
                
                # Get tasks for TTM (only done status transitions)
                ttm_tasks = self.data_service.get_tasks_for_period(
                    quarter.start_date, 
                    quarter.end_date, 
                    self.group_by, 
                    status_mapping,
                    metric_type="ttm"
                )
                
                # Group tasks by author/team
                group_data = defaultdict(lambda: {
                    'ttd_times': [],
                    'ttd_pause_times': [],
                    'ttm_times': [],
                    'ttm_pause_times': [],
                    'tail_times': [],
                    'tail_pause_times': []
                })
                
                # Process TTD tasks
                for task in ttd_tasks:
                    group_value = task.group_value
                    task_id = task.id
                    
                    # Get task history
                    history = self.data_service.get_task_history(task_id)
                    
                    if not history:
                        logger.debug(f"No history found for task {task.key}")
                        continue
                    
                    # Calculate pause time for this task
                    pause_time = self.metrics_service.calculate_pause_time(history)
                    
                    # Calculate Time To Delivery (only for TTD tasks)
                    ttd = self.metrics_service.calculate_time_to_delivery(
                        history, status_mapping.discovery_statuses
                    )
                    if ttd is not None:
                        group_data[group_value]['ttd_times'].append(ttd)
                        group_data[group_value]['ttd_pause_times'].append(pause_time)
                
                # Process TTM tasks
                for task in ttm_tasks:
                    group_value = task.group_value
                    task_id = task.id
                    
                    # Get task history
                    history = self.data_service.get_task_history(task_id)
                    
                    if not history:
                        logger.debug(f"No history found for task {task.key}")
                        continue
                    
                    # Calculate pause time for this task
                    pause_time = self.metrics_service.calculate_pause_time(history)
                    
                    # Calculate Time To Market (only for TTM tasks)
                    ttm = self.metrics_service.calculate_time_to_market(
                        history, status_mapping.done_statuses
                    )
                    if ttm is not None:
                        group_data[group_value]['ttm_times'].append(ttm)
                        group_data[group_value]['ttm_pause_times'].append(pause_time)
                    
                    # Calculate Tail metric (only for TTM tasks)
                    tail = self.metrics_service.calculate_tail_metric(
                        history, status_mapping.done_statuses
                    )
                    if tail is not None:
                        # Calculate pause time specifically for Tail metric period
                        # Find the last MP/External Test entry
                        sorted_history = sorted(history, key=lambda x: x.start_date)
                        last_mp_entry = None
                        for entry in sorted_history:
                            if entry.status == 'МП / Внешний тест':
                                last_mp_entry = entry
                        
                        # Find the done entry after MP/External Test
                        done_entry = None
                        for entry in sorted_history:
                            if (entry.start_date > last_mp_entry.start_date and 
                                entry.status in status_mapping.done_statuses):
                                done_entry = entry
                                break
                        
                        # Calculate pause time between MP/External Test and done status
                        tail_pause_time = 0
                        if last_mp_entry and done_entry:
                            tail_pause_time = self.metrics_service.calculate_pause_time_between_dates(
                                history, last_mp_entry.start_date, done_entry.start_date
                            )
                        
                        group_data[group_value]['tail_times'].append(tail)
                        group_data[group_value]['tail_pause_times'].append(tail_pause_time)
                
                # Calculate metrics for each group
                groups = {}
                for group_value, data in group_data.items():
                    if data['ttd_times'] or data['ttm_times'] or data['tail_times']:
                        groups[group_value] = self.metrics_service.calculate_enhanced_group_metrics(
                            group_value, 
                            data['ttd_times'], 
                            data['ttd_pause_times'],
                            data['ttm_times'], 
                            data['ttm_pause_times'],
                            data['tail_times'],
                            data['tail_pause_times']
                        )
                
                if groups:
                    quarter_reports[quarter.name] = QuarterReport(
                        quarter=quarter,
                        groups=groups
                    )
            
            self.report = TimeToMarketReport(
                quarters=quarters,
                status_mapping=status_mapping,
                group_by=self.group_by,
                quarter_reports=quarter_reports
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
                quarter_reports={}
            )
    
    def generate_csv(self, filepath: Optional[str] = None, report_type: ReportType = ReportType.BOTH) -> str:
        """
        Generate CSV report.
        
        Args:
            filepath: Output file path (optional)
            report_type: Type of report to generate
            
        Returns:
            Path to generated CSV file
        """
        if not self.report:
            logger.warning("No report data available. Run generate_report_data() first.")
            return ""
        
        renderer = CSVRenderer(self.report)
        return renderer.render(filepath, report_type)
    
    def generate_table(self, filepath: Optional[str] = None, report_type: ReportType = ReportType.BOTH) -> str:
        """
        Generate table report.
        
        Args:
            filepath: Output file path (optional)
            report_type: Type of report to generate
            
        Returns:
            Path to generated table file
        """
        if not self.report:
            logger.warning("No report data available. Run generate_report_data() first.")
            return ""
        
        renderer = TableRenderer(self.report)
        return renderer.render(filepath, report_type)
    
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
    
    parser = argparse.ArgumentParser(description='Generate Time To Delivery and Time To Market report')
    parser.add_argument('--group-by', choices=['author', 'team'], default='author',
                       help='Group by author or team (default: author)')
    parser.add_argument('--report-type', choices=['ttd', 'ttm', 'both'], default='both',
                       help='Report type: ttd (Time To Delivery), ttm (Time To Market), or both (default: both)')
    parser.add_argument('--csv', help='CSV output file path')
    parser.add_argument('--table', help='Table output file path')
    parser.add_argument('--config-dir', default='data/config',
                       help='Configuration directory path (default: data/config)')
    
    args = parser.parse_args()
    
    try:
        # Convert string arguments to enums
        group_by = GroupBy.AUTHOR if args.group_by == 'author' else GroupBy.TEAM
        report_type = ReportType(args.report_type)
        
        with GenerateTimeToMarketReportCommand(group_by=group_by, config_dir=args.config_dir) as cmd:
            # Generate report data
            cmd.generate_report_data()
            
            # Generate separate TTD and TTM files
            ttd_csv_file = ""
            ttd_table_file = ""
            ttm_csv_file = ""
            ttm_table_file = ""
            
            if report_type == ReportType.BOTH:
                # Generate TTD files
                ttd_csv_file = cmd.generate_csv(None, ReportType.TTD)
                ttd_table_file = cmd.generate_table(None, ReportType.TTD)
                
                # Generate TTM files
                ttm_csv_file = cmd.generate_csv(None, ReportType.TTM)
                ttm_table_file = cmd.generate_table(None, ReportType.TTM)
            else:
                # Generate single report type files
                if report_type == ReportType.TTD:
                    ttd_csv_file = cmd.generate_csv(args.csv, ReportType.TTD)
                    ttd_table_file = cmd.generate_table(args.table, ReportType.TTD)
                elif report_type == ReportType.TTM:
                    ttm_csv_file = cmd.generate_csv(args.csv, ReportType.TTM)
                    ttm_table_file = cmd.generate_table(args.table, ReportType.TTM)
            
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
                
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
