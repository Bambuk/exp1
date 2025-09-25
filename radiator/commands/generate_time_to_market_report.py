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
                    try:
                        tail = self.metrics_service.calculate_tail_metric(
                            history, status_mapping.done_statuses
                        )
                        if tail is not None:
                            group_data[group_value]['tail_times'].append(tail)
                            group_data[group_value]['tail_pause_times'].append(0)  # No pause time for tail
                    except Exception as e:
                        logger.warning(f"Error calculating tail metric for task {task.key}: {e}")
                        # Continue without tail metric
                
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
    
    def generate_task_details_csv(self, filepath: Optional[str] = None) -> str:
        """
        Generate detailed CSV with individual task metrics.
        
        Args:
            filepath: Output file path (optional)
            
        Returns:
            Path to generated CSV file
        """
        if not self.report:
            logger.warning("No report data available. Run generate_report_data() first.")
            return ""
        
        task_details = []
        
        try:
            from datetime import datetime
            import csv
            
            # Generate filename if not provided
            if not filepath:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = f"reports/task_details_{timestamp}.csv"
            
            # Ensure reports directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            # Process each quarter
            for quarter in self.report.quarters:
                logger.info(f"Processing task details for quarter: {quarter.name}")
                
                # Get tasks for TTD and TTM
                ttd_tasks = self.data_service.get_tasks_for_period(
                    quarter.start_date, 
                    quarter.end_date, 
                    self.group_by, 
                    self.report.status_mapping,
                    metric_type="ttd"
                )
                
                ttm_tasks = self.data_service.get_tasks_for_period(
                    quarter.start_date, 
                    quarter.end_date, 
                    self.group_by, 
                    self.report.status_mapping,
                    metric_type="ttm"
                )
                
                # Combine tasks for processing
                all_tasks_in_quarter = {task.key: task for task in ttd_tasks + ttm_tasks}
                
                for task_key, task in all_tasks_in_quarter.items():
                    history = self.data_service.get_task_history(task.id)
                    if not history:
                        logger.debug(f"No history found for task {task.key}")
                        continue
                    
                    ttd = self.metrics_service.calculate_time_to_delivery(history, self.report.status_mapping.discovery_statuses)
                    ttm = self.metrics_service.calculate_time_to_market(history, self.report.status_mapping.done_statuses)
                    tail = self.metrics_service.calculate_tail_metric(history, self.report.status_mapping.done_statuses)
                    pause_time = self.metrics_service.calculate_pause_time(history)
                    
                    task_details.append({
                        "Автор": task.author,
                        "Ключ задачи": task.key,
                        "Название": task.summary,
                        "TTD": ttd if ttd is not None else '',
                        "TTM": ttm if ttm is not None else '',
                        "Tail": tail if tail is not None else '',
                        "Пауза": pause_time if pause_time is not None else '',
                        "Квартал": quarter.name
                    })
            
            # Write to CSV
            if task_details:
                with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ["Автор", "Ключ задачи", "Название", "TTD", "TTM", "Tail", "Пауза", "Квартал"]
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
    parser.add_argument('--task-details', help='Task details CSV output file path')
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
            task_details_file = ""
            
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
