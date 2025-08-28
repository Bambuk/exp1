"""Command for generating status change report for tasks by authors over last 2 weeks."""

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import csv
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.core.database import SessionLocal
from radiator.core.config import settings
from radiator.core.logging import logger
from radiator.crud.tracker import tracker_task, tracker_task_history
from radiator.models.tracker import TrackerTask, TrackerTaskHistory


class GenerateStatusChangeReportCommand:
    """Command for generating status change report for CPO tasks by authors over last 2 weeks."""
    
    def __init__(self):
        self.db = SessionLocal()
        self.report_data: Dict[str, Dict[str, int]] = {}
        self.week1_data: Dict[str, int] = {}
        self.week2_data: Dict[str, int] = {}
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()
    
    def get_status_changes_by_author(self, start_date: datetime, end_date: datetime) -> Dict[str, Dict[str, int]]:
        """
        Get count of status changes and unique tasks by author within date range for CPO tasks only.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Dictionary mapping author to dict with 'changes', 'tasks', and 'open_tasks' counts
        """
        try:
            # Query status changes within date range
            # We need to join tracker_tasks with tracker_task_history to get author information
            query = self.db.query(
                TrackerTask.author,
                TrackerTaskHistory.id,
                TrackerTaskHistory.task_id
            ).join(
                TrackerTaskHistory,
                TrackerTask.id == TrackerTaskHistory.task_id
            ).filter(
                TrackerTaskHistory.start_date >= start_date,
                TrackerTaskHistory.start_date < end_date,
                TrackerTask.author.isnot(None),  # Exclude tasks without author
                TrackerTask.key.like('CPO-%')  # Only CPO tasks
            )
            
            logger.info(f"Executing query for CPO tasks in date range: {start_date.date()} to {end_date.date()}")
            
            # Execute query and count by author
            results = query.all()
            logger.info(f"Query returned {len(results)} results")
            
            author_data = defaultdict(lambda: {'changes': 0, 'tasks': set()})
            
            for i, (author, _, task_id) in enumerate(results):
                if author:  # Double check author is not None
                    try:
                        # Handle potential encoding issues
                        if isinstance(author, bytes):
                            author = author.decode('utf-8', errors='replace')
                        elif isinstance(author, str):
                            # Ensure it's valid UTF-8
                            author.encode('utf-8').decode('utf-8')
                        
                        author_data[author]['changes'] += 1
                        author_data[author]['tasks'].add(task_id)
                    except (UnicodeDecodeError, UnicodeEncodeError) as e:
                        logger.warning(f"Skipping author with encoding issue at position {i}: {e}, author value: {repr(author)}")
                        continue
            
            # Convert sets to counts and return
            result = {}
            for author, data in author_data.items():
                result[author] = {
                    'changes': data['changes'],
                    'tasks': len(data['tasks'])
                }
            
            total_changes = sum(data['changes'] for data in result.values())
            total_tasks = sum(data['tasks'] for data in result.values())
            logger.info(f"Found {total_changes} status changes across {total_tasks} unique tasks for {len(result)} authors from {start_date.date()} to {end_date.date()}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get status changes by author: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def get_open_tasks_by_author(self) -> Dict[str, Dict[str, int]]:
        """
        Get count of open tasks by author grouped by discovery/delivery blocks for CPO tasks only.
        
        Returns:
            Dictionary mapping author to dict with 'discovery' and 'delivery' counts
        """
        try:
            # Load status mapping from file
            status_mapping = self._load_status_mapping()
            
            # Query open tasks (not in closed statuses)
            closed_statuses = ['closed', 'done', 'resolved', 'cancelled', 'rejected']
            
            query = self.db.query(
                TrackerTask.author,
                TrackerTask.id,
                TrackerTask.status
            ).filter(
                TrackerTask.author.isnot(None),  # Exclude tasks without author
                TrackerTask.key.like('CPO-%'),  # Only CPO tasks
                ~TrackerTask.status.in_(closed_statuses)  # Not in closed statuses
            )
            
            logger.info("Executing query for open CPO tasks with status mapping")
            
            # Execute query and count by author and block
            results = query.all()
            logger.info(f"Query returned {len(results)} open tasks")
            
            author_blocks = defaultdict(lambda: {'discovery': 0, 'delivery': 0})
            
            for author, _, status in results:
                if author:  # Double check author is not None
                    try:
                        # Handle potential encoding issues
                        if isinstance(author, bytes):
                            author = author.decode('utf-8', errors='replace')
                        elif isinstance(author, str):
                            # Ensure it's valid UTF-8
                            author.encode('utf-8').decode('utf-8')
                        
                        # Map status to block
                        block = status_mapping.get(status, 'discovery')  # Default to discovery if status not found
                        if block in ['discovery', 'delivery']:
                            author_blocks[author][block] += 1
                        
                    except (UnicodeDecodeError, UnicodeEncodeError) as e:
                        logger.warning(f"Skipping author with encoding issue: {e}, author value: {repr(author)}")
                        continue
            
            # Convert to final format
            result = {}
            for author, blocks in author_blocks.items():
                result[author] = {
                    'discovery': blocks['discovery'],
                    'delivery': blocks['delivery']
                }
            
            total_discovery = sum(data['discovery'] for data in result.values())
            total_delivery = sum(data['delivery'] for data in result.values())
            logger.info(f"Found {total_discovery} discovery tasks and {total_delivery} delivery tasks for {len(result)} authors")
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
            with open(mapping_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and ';' in line:
                        status, block = line.split(';', 1)
                        status_mapping[status.strip()] = block.strip()
            
            logger.info(f"Loaded {len(status_mapping)} status mappings")
            return status_mapping
            
        except Exception as e:
            logger.error(f"Failed to load status mapping: {e}")
            return {}
    
    def generate_report_data(self) -> Dict[str, Dict[str, int]]:
        """
        Generate report data for CPO tasks over last 2 weeks.
        
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
        
        # Store date ranges for display
        self.week1_start = week1_start
        self.week1_end = week1_end
        self.week2_start = week2_start
        self.week2_end = week2_end
        
        logger.info(f"Generating CPO tasks report for:")
        logger.info(f"  Week 1: {week1_start.date()} to {week1_end.date()}")
        logger.info(f"  Week 2: {week2_start.date()} to {week2_end.date()}")
        
        # Get data for each week
        self.week1_data = self.get_status_changes_by_author(week1_start, week1_end)
        self.week2_data = self.get_status_changes_by_author(week2_start, week2_end)
        
        # Get current open tasks data
        self.open_tasks_data = self.get_open_tasks_by_author()
        
        # Combine all unique authors
        all_authors = set(self.week1_data.keys()) | set(self.week2_data.keys()) | set(self.open_tasks_data.keys())
        
        # Build report data with changes, tasks counts, and open tasks by blocks
        # Note: week2 is earlier (left), week1 is later (right)
        self.report_data = {}
        for author in sorted(all_authors):
            week2_data = self.week2_data.get(author, {'changes': 0, 'tasks': 0})
            week1_data = self.week1_data.get(author, {'changes': 0, 'tasks': 0})
            open_tasks_data = self.open_tasks_data.get(author, {'discovery': 0, 'delivery': 0})
            
            self.report_data[author] = {
                'week2_changes': week2_data['changes'],
                'week2_tasks': week2_data['tasks'],
                'week1_changes': week1_data['changes'],
                'week1_tasks': week1_data['tasks'],
                'discovery_tasks': open_tasks_data['discovery'],
                'delivery_tasks': open_tasks_data['delivery']
            }
        
        logger.info(f"Generated report for {len(self.report_data)} authors")
        return self.report_data
    
    def _get_dynamics_arrow(self, current: int, previous: int) -> str:
        """
        Get dynamics arrow based on comparison of current vs previous values.
        
        Args:
            current: Current week value
            previous: Previous week value
            
        Returns:
            Arrow emoji with color indication
        """
        if current > previous:
            return "🟢↗️"  # Green up arrow for improvement
        elif current < previous:
            return "🔴↘️"  # Red down arrow for decline
        else:
            return "⚪➡️"  # White right arrow for no change
    
    def save_csv_report(self, filename: str = None) -> str:
        """
        Save report data to CSV file with dynamics indicators.
        
        Args:
            filename: Optional filename, will generate default if not provided
            
        Returns:
            Path to saved CSV file
        """
        if not filename:
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
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Автор', f'{week2_header}_изменения', f'{week2_header}_задачи', f'{week1_header}_изменения', f'{week1_header}_задачи', 'Discovery', 'Delivery']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for author, data in self.report_data.items():
                    # Get dynamics arrows
                    changes_arrow = self._get_dynamics_arrow(data['week1_changes'], data['week2_changes'])
                    tasks_arrow = self._get_dynamics_arrow(data['week1_tasks'], data['week2_tasks'])
                    
                    writer.writerow({
                        'Автор': author,
                        f'{week2_header}_изменения': data['week2_changes'],  # Earlier week changes
                        f'{week2_header}_задачи': data['week2_tasks'],       # Earlier week tasks
                        f'{week1_header}_изменения': f"{data['week1_changes']} {changes_arrow}",  # Later week changes with arrow
                        f'{week1_header}_задачи': f"{data['week1_tasks']} {tasks_arrow}",         # Later week tasks with arrow
                        'Discovery': data['discovery_tasks'],                 # Discovery tasks
                        'Delivery': data['delivery_tasks']                    # Delivery tasks
                    })
            
            logger.info(f"CSV report saved to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to save CSV report: {e}")
            raise
    
    def generate_table(self, filename: str = None) -> str:
        """
        Generate table visualization of the report data.
        
        Args:
            filename: Optional filename, will generate default if not provided
            
        Returns:
            Path to saved table image
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"status_change_table_{timestamp}.png"
        
        # Ensure reports directory exists
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        filepath = reports_dir / filename
        
        try:
            # Prepare data for table
            authors = list(self.report_data.keys())
            week2_changes = [self.report_data[author]['week2_changes'] for author in authors]  # Earlier week changes
            week2_tasks = [self.report_data[author]['week2_tasks'] for author in authors]      # Earlier week tasks
            week1_changes = [self.report_data[author]['week1_changes'] for author in authors]  # Later week changes
            week1_tasks = [self.report_data[author]['week1_tasks'] for author in authors]      # Later week tasks
            discovery_tasks = [self.report_data[author]['discovery_tasks'] for author in authors]  # Discovery tasks
            delivery_tasks = [self.report_data[author]['delivery_tasks'] for author in authors]    # Delivery tasks
            
            # Format dates for column headers
            week2_header = f"{self.week2_start.strftime('%d.%m')}-{self.week2_end.strftime('%d.%m')}"
            week1_header = f"{self.week1_start.strftime('%d.%m')}-{self.week1_end.strftime('%d.%m')}"
            
            # Calculate dimensions with proper padding for table (6 columns: Author, Week2, Week1_changes, Week1_tasks, Discovery, Delivery)
            cell_height = 0.08  # Height per row
            header_height = 0.1  # Header row height (standard height for single line)
            table_height = len(authors) * cell_height + header_height
            
            # Add minimal padding around table (top, bottom, left, right)
            padding = 0.05
            total_height = table_height + 2 * padding
            
            # Create figure with proper size including padding
            fig_width = 18  # Increased width for 6 columns
            fig_height = total_height
            fig = plt.figure(figsize=(fig_width, fig_height))
            
            # Create axis with padding around table
            ax = fig.add_axes([padding, padding, 1 - 2*padding, 1 - 2*padding])
            ax.axis('off')
            
            # Create table data with changes, tasks, and tasks by blocks
            table_data = []
            for author, w2_ch, w2_t, w1_ch, w1_t, disc, deliv in zip(authors, week2_changes, week2_tasks, week1_changes, week1_tasks, discovery_tasks, delivery_tasks):
                # Add dynamics arrows to current week data
                changes_arrow = self._get_dynamics_arrow(w1_ch, w2_ch)
                tasks_arrow = self._get_dynamics_arrow(w1_t, w2_t)
                table_data.append([author, f"{w2_ch} ({w2_t})", f"{w1_ch} ({w1_t}) {changes_arrow}", f"{w1_t} {tasks_arrow}", disc, deliv])
            
            # Create table positioned in the center of the axis
            table = ax.table(cellText=table_data,
                           colLabels=['Автор', f'{week2_header} | изменения (задачи)', f'{week1_header} | изменения', f'{week1_header} | задачи', 'Discovery', 'Delivery'],
                           cellLoc='center',
                           loc='center',
                           colWidths=[0.25, 0.20, 0.20, 0.20, 0.08, 0.08])  # Adjusted widths for 6 columns
            
            # Style the table
            table.auto_set_font_size(False)
            table.set_fontsize(11)
            
            # Minimal scaling to fit properly
            table.scale(1.0, 1.0)
            
            # Style header row
            for i in range(6):
                table[(0, i)].set_facecolor('#4CAF50')
                table[(0, i)].set_text_props(weight='bold', color='white')
            
            # Style data rows
            for i in range(1, len(table_data) + 1):
                for j in range(6):
                    cell = table[(i, j)]
                    if i % 2 == 0:  # Alternate row colors
                        cell.set_facecolor('#F5F5F5')
                    else:
                        cell.set_facecolor('#FFFFFF')
                    
                    # Left align text for Author column, center for data columns
                    if j == 0:  # Author column
                        cell.set_text_props(ha='left', va='center')
                    else:  # Data columns
                        cell.set_text_props(ha='center', va='center')
            
            # No title - clean table only
            
            # Save with minimal margins - use tight layout to avoid cropping
            plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white', 
                       pad_inches=0.1, edgecolor='none', transparent=False)
            plt.close()
            
            logger.info(f"Table saved to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to generate table: {e}")
            raise
    
    def print_summary(self):
        """Print summary of the report to console."""
        if not self.report_data:
            logger.warning("No report data available. Run generate_report_data() first.")
            return
        
        print("\n" + "="*80)
        print("CPO TASKS STATUS CHANGE REPORT - LAST 2 WEEKS")
        print("="*80)
        
        # Calculate totals
        total_week1_changes = sum(data['week1_changes'] for data in self.report_data.values())
        total_week1_tasks = sum(data['week1_tasks'] for data in self.report_data.values())
        total_week2_changes = sum(data['week2_changes'] for data in self.report_data.values())
        total_week2_tasks = sum(data['week2_tasks'] for data in self.report_data.values())
        total_discovery_tasks = sum(data['discovery_tasks'] for data in self.report_data.values())
        total_delivery_tasks = sum(data['delivery_tasks'] for data in self.report_data.values())
        
        # Format dates for display
        week2_header = f"{self.week2_start.strftime('%d.%m')}-{self.week2_end.strftime('%d.%m')}"
        week1_header = f"{self.week1_start.strftime('%d.%m')}-{self.week1_end.strftime('%d.%m')}"
        
        print(f"Total Status Changes - {week1_header}: {total_week1_changes} across {total_week1_tasks} tasks")
        print(f"Total Status Changes - {week2_header}: {total_week2_changes} across {total_week2_tasks} tasks")
        print(f"Total Discovery Tasks: {total_discovery_tasks}")
        print(f"Total Delivery Tasks: {total_delivery_tasks}")
        print(f"Number of Authors: {len(self.report_data)}")
        print("-"*80)
        
        # Print by author with changes, tasks, and tasks by blocks
        print(f"{'Author':<25} {week2_header:<20} {week1_header:<20} {'Discovery':<10} {'Delivery':<10}")
        print("-"*80)
        
        for author, data in sorted(self.report_data.items(), key=lambda x: x[1]['week1_changes'] + x[1]['week2_changes'], reverse=True):
            week2_str = f"{data['week2_changes']} ({data['week2_tasks']})"
            
            # Add dynamics arrows to current week
            changes_arrow = self._get_dynamics_arrow(data['week1_changes'], data['week2_changes'])
            tasks_arrow = self._get_dynamics_arrow(data['week1_tasks'], data['week2_tasks'])
            week1_str = f"{data['week1_changes']} ({data['week1_tasks']}) {changes_arrow}{tasks_arrow}"
            
            discovery_str = str(data['discovery_tasks'])
            delivery_str = str(data['delivery_tasks'])
            print(f"{author:<25} {week2_str:<20} {week1_str:<20} {discovery_str:<10} {delivery_str:<10}")
        
        print("="*80)
    
    def run(self, csv_filename: str = None, table_filename: str = None) -> bool:
        """
        Run the complete report generation process.
        
        Args:
            csv_filename: Optional CSV filename
            table_filename: Optional table image filename
            
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
            csv_path = self.save_csv_report(csv_filename)
            logger.info(f"CSV report saved: {csv_path}")
            
            # Generate table
            table_path = self.generate_table(table_filename)
            logger.info(f"Table saved: {table_path}")
            
            logger.info("Status change report generation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate status change report: {e}")
            return False


def main():
    """Main entry point for command line execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate CPO tasks status change report for last 2 weeks')
    parser.add_argument('--csv', help='CSV output filename')
    parser.add_argument('--table', help='Table image output filename')
    
    args = parser.parse_args()
    
    with GenerateStatusChangeReportCommand() as cmd:
        success = cmd.run(args.csv, args.table)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
