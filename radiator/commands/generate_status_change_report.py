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
    """Command for generating status change report for tasks by authors over last 2 weeks."""
    
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
    
    def get_status_changes_by_author(self, start_date: datetime, end_date: datetime) -> Dict[str, int]:
        """
        Get count of status changes by author within date range.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Dictionary mapping author to count of status changes
        """
        try:
            # Query status changes within date range
            # We need to join tracker_tasks with tracker_task_history to get author information
            query = self.db.query(
                TrackerTask.author,
                TrackerTaskHistory.id
            ).join(
                TrackerTaskHistory,
                TrackerTask.id == TrackerTaskHistory.task_id
            ).filter(
                TrackerTaskHistory.start_date >= start_date,
                TrackerTaskHistory.start_date < end_date,
                TrackerTask.author.isnot(None)  # Exclude tasks without author
            )
            
            logger.info(f"Executing query for date range: {start_date.date()} to {end_date.date()}")
            
            # Execute query and count by author
            results = query.all()
            logger.info(f"Query returned {len(results)} results")
            
            author_counts = defaultdict(int)
            
            for i, (author, _) in enumerate(results):
                if author:  # Double check author is not None
                    try:
                        # Handle potential encoding issues
                        if isinstance(author, bytes):
                            author = author.decode('utf-8', errors='replace')
                        elif isinstance(author, str):
                            # Ensure it's valid UTF-8
                            author.encode('utf-8').decode('utf-8')
                        
                        author_counts[author] += 1
                    except (UnicodeDecodeError, UnicodeEncodeError) as e:
                        logger.warning(f"Skipping author with encoding issue at position {i}: {e}, author value: {repr(author)}")
                        continue
            
            logger.info(f"Found {sum(author_counts.values())} status changes for {len(author_counts)} authors from {start_date.date()} to {end_date.date()}")
            return dict(author_counts)
            
        except Exception as e:
            logger.error(f"Failed to get status changes by author: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def generate_report_data(self) -> Dict[str, Dict[str, int]]:
        """
        Generate report data for last 2 weeks.
        
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
        
        logger.info(f"Generating report for:")
        logger.info(f"  Week 1: {week1_start.date()} to {week1_end.date()}")
        logger.info(f"  Week 2: {week2_start.date()} to {week2_end.date()}")
        
        # Get data for each week
        self.week1_data = self.get_status_changes_by_author(week1_start, week1_end)
        self.week2_data = self.get_status_changes_by_author(week2_start, week2_end)
        
        # Combine all unique authors
        all_authors = set(self.week1_data.keys()) | set(self.week2_data.keys())
        
        # Build report data (without total)
        self.report_data = {}
        for author in sorted(all_authors):
            self.report_data[author] = {
                'week1': self.week1_data.get(author, 0),
                'week2': self.week2_data.get(author, 0)
            }
        
        logger.info(f"Generated report for {len(self.report_data)} authors")
        return self.report_data
    
    def save_csv_report(self, filename: str = None) -> str:
        """
        Save report data to CSV file.
        
        Args:
            filename: Optional filename, will generate default if not provided
            
        Returns:
            Path to saved CSV file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"status_change_report_{timestamp}.csv"
        
        filepath = Path(filename)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Author', 'Last Week', 'Week Before Last']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for author, data in self.report_data.items():
                    writer.writerow({
                        'Author': author,
                        'Last Week': data['week1'],
                        'Week Before Last': data['week2']
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
        
        filepath = Path(filename)
        
        try:
            # Prepare data for table
            authors = list(self.report_data.keys())
            week1_values = [self.report_data[author]['week1'] for author in authors]
            week2_values = [self.report_data[author]['week2'] for author in authors]
            
            # Create figure and axis
            fig, ax = plt.subplots(figsize=(10, max(6, len(authors) * 0.4 + 2)))
            
            # Hide axes
            ax.axis('tight')
            ax.axis('off')
            
            # Create table data
            table_data = []
            for author, week1, week2 in zip(authors, week1_values, week2_values):
                table_data.append([author, week1, week2])
            
            # Create table
            table = ax.table(cellText=table_data,
                           colLabels=['Author', 'Last Week', 'Week Before Last'],
                           cellLoc='center',
                           loc='center',
                           colWidths=[0.5, 0.25, 0.25])
            
            # Style the table
            table.auto_set_font_size(False)
            table.set_fontsize(12)
            table.scale(1.2, 1.5)
            
            # Style header row
            for i in range(3):
                table[(0, i)].set_facecolor('#4CAF50')
                table[(0, i)].set_text_props(weight='bold', color='white')
            
            # Style data rows
            for i in range(1, len(table_data) + 1):
                for j in range(3):
                    cell = table[(i, j)]
                    if i % 2 == 0:  # Alternate row colors
                        cell.set_facecolor('#F5F5F5')
                    else:
                        cell.set_facecolor('#FFFFFF')
                    
                    # Center align text
                    cell.set_text_props(ha='center', va='center')
            
            # Add title
            plt.title('Status Changes by Author (Last 2 Weeks)', fontsize=16, fontweight='bold', pad=20)
            
            # Adjust layout and save
            plt.tight_layout()
            plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
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
        print("STATUS CHANGE REPORT - LAST 2 WEEKS")
        print("="*80)
        
        # Calculate totals
        total_week1 = sum(data['week1'] for data in self.report_data.values())
        total_week2 = sum(data['week2'] for data in self.report_data.values())
        
        print(f"Total Status Changes - Last Week: {total_week1}")
        print(f"Total Status Changes - Week Before Last: {total_week2}")
        print(f"Number of Authors: {len(self.report_data)}")
        print("-"*80)
        
        # Print by author
        print(f"{'Author':<30} {'Last Week':<12} {'Prev Week':<12}")
        print("-"*80)
        
        for author, data in sorted(self.report_data.items(), key=lambda x: x[1]['week1'] + x[1]['week2'], reverse=True):
            print(f"{author:<30} {data['week1']:<12} {data['week2']:<12}")
        
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
            logger.info("Starting status change report generation...")
            
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
    
    parser = argparse.ArgumentParser(description='Generate status change report for last 2 weeks')
    parser.add_argument('--csv', help='CSV output filename')
    parser.add_argument('--table', help='Table image output filename')
    
    args = parser.parse_args()
    
    with GenerateStatusChangeReportCommand() as cmd:
        success = cmd.run(args.csv, args.table)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
