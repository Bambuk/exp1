"""Demo command for generating status change report with test data."""

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

from radiator.core.logging import logger


class GenerateStatusChangeReportDemoCommand:
    """Demo command for generating status change report with test data."""
    
    def __init__(self):
        self.report_data: Dict[str, Dict[str, int]] = {}
        self.week1_data: Dict[str, int] = {}
        self.week2_data: Dict[str, int] = {}
    
    def generate_demo_data(self) -> Dict[str, Dict[str, int]]:
        """
        Generate demo report data for last 2 weeks.
        
        Returns:
            Dictionary with week data
        """
        # Generate realistic demo data
        demo_authors = [
            "Елена Кавкаева",
            "nra tech", 
            "Анастасия Милютина",
            "Феликс Пушкарский",
            "Ренат Минзакиевич Калимуллов",
            "Робот сервиса Tracker Робот",
            "Евгения Уколова",
            "Елизавета Купчинаус",
            "Екатерина Александровна Ионова",
            "Анатолий Георгиевич Антипов"
        ]
        
        # Generate random-like data for demo
        import random
        random.seed(42)  # For reproducible results
        
        self.week1_data = {}
        self.week2_data = {}
        
        for author in demo_authors:
            # Generate realistic numbers
            week1_count = random.randint(1, 15)
            week2_count = random.randint(0, 12)
            
            self.week1_data[author] = week1_count
            self.week2_data[author] = week2_count
        
        # Build report data (without total)
        # Note: week2 is earlier (left), week1 is later (right)
        self.report_data = {}
        for author in sorted(demo_authors):
            self.report_data[author] = {
                'week2': self.week2_data[author],  # Earlier week (left)
                'week1': self.week1_data[author]   # Later week (right)
            }
        
        logger.info(f"Generated demo report for {len(self.report_data)} authors")
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
            filename = f"demo_status_change_report_{timestamp}.csv"
        
        # Ensure reports directory exists
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        filepath = reports_dir / filename
        
        try:
            # Generate demo date ranges
            now = datetime.now()
            week1_end = now
            week1_start = week1_end - timedelta(days=7)
            week2_end = week1_start
            week2_start = week2_end - timedelta(days=7)
            
            # Format dates for column headers
            week2_header = f"{week2_start.strftime('%d.%m')}-{week2_end.strftime('%d.%m')}"
            week1_header = f"{week1_start.strftime('%d.%m')}-{week1_end.strftime('%d.%m')}"
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Author', week2_header, week1_header]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for author, data in self.report_data.items():
                    writer.writerow({
                        'Author': author,
                        week2_header: data['week2'],  # Earlier week (left)
                        week1_header: data['week1']   # Later week (right)
                    })
            
            logger.info(f"Demo CSV report saved to: {filepath}")
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
            filename = f"demo_status_change_table_{timestamp}.png"
        
        # Ensure reports directory exists
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        filepath = reports_dir / filename
        
        try:
            # Prepare data for table
            authors = list(self.report_data.keys())
            week2_values = [self.report_data[author]['week2'] for author in authors]  # Earlier week (left)
            week1_values = [self.report_data[author]['week1'] for author in authors]  # Later week (right)
            
            # Generate demo date ranges
            now = datetime.now()
            week1_end = now
            week1_start = week1_end - timedelta(days=7)
            week2_end = week1_start
            week2_start = week2_end - timedelta(days=7)
            
            # Format dates for column headers
            week2_header = f"{week2_start.strftime('%d.%m')}-{week2_end.strftime('%d.%m')}"
            week1_header = f"{week1_start.strftime('%d.%m')}-{week1_end.strftime('%d.%m')}"
            
            # Create figure and axis with optimized size
            fig, ax = plt.subplots(figsize=(10, max(6, len(authors) * 0.4 + 1)))
            
            # Hide axes
            ax.axis('tight')
            ax.axis('off')
            
            # Create table data
            table_data = []
            for author, week2, week1 in zip(authors, week2_values, week1_values):
                table_data.append([author, week2, week1])  # Earlier week first (left)
            
            # Create table
            table = ax.table(cellText=table_data,
                           colLabels=['Author', week2_header, week1_header],
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
            
            # Add title with reduced padding
            plt.title('Demo: Status Changes by Author (Last 2 Weeks)', fontsize=16, fontweight='bold', pad=10)
            
            # Adjust layout and save with optimized parameters
            plt.tight_layout(pad=0.5)
            plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white', pad_inches=0.1)
            plt.close()
            
            logger.info(f"Demo table saved to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to generate table: {e}")
            raise
    
    def print_summary(self):
        """Print summary of the report to console."""
        if not self.report_data:
            logger.warning("No report data available. Run generate_demo_data() first.")
            return
        
        print("\n" + "="*80)
        print("DEMO STATUS CHANGE REPORT - LAST 2 WEEKS")
        print("="*80)
        
        # Calculate totals
        total_week1 = sum(data['week1'] for data in self.report_data.values())
        total_week2 = sum(data['week2'] for data in self.report_data.values())
        
        # Generate demo date ranges
        now = datetime.now()
        week1_end = now
        week1_start = week1_end - timedelta(days=7)
        week2_end = week1_start
        week2_start = week2_end - timedelta(days=7)
        
        # Format dates for display
        week2_header = f"{week2_start.strftime('%d.%m')}-{week2_end.strftime('%d.%m')}"
        week1_header = f"{week1_start.strftime('%d.%m')}-{week1_end.strftime('%d.%m')}"
        
        print(f"Total Status Changes - {week1_header}: {total_week1}")
        print(f"Total Status Changes - {week2_header}: {total_week2}")
        print(f"Number of Authors: {len(self.report_data)}")
        print("-"*80)
        
        # Print by author
        print(f"{'Author':<35} {week2_header:<12} {week1_header:<12}")
        print("-"*80)
        
        for author, data in sorted(self.report_data.items(), key=lambda x: x[1]['week1'] + x[1]['week2'], reverse=True):
            print(f"{author:<35} {data['week2']:<12} {data['week1']:<12}")
        
        print("="*80)
        print("NOTE: This is a DEMO report with generated test data.")
        print("="*80)
    
    def run(self, csv_filename: str = None, table_filename: str = None) -> bool:
        """
        Run the complete demo report generation process.
        
        Args:
            csv_filename: Optional CSV filename
            table_filename: Optional table image filename
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Starting demo status change report generation...")
            
            # Generate demo report data
            self.generate_demo_data()
            
            if not self.report_data:
                logger.warning("No demo data generated")
                return False
            
            # Print summary to console
            self.print_summary()
            
            # Save CSV report
            csv_path = self.save_csv_report(csv_filename)
            logger.info(f"Demo CSV report saved: {csv_path}")
            
            # Generate table
            table_path = self.generate_table(table_filename)
            logger.info(f"Demo table saved: {table_path}")
            
            logger.info("Demo status change report generation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate demo status change report: {e}")
            return False


def main():
    """Main entry point for command line execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate demo status change report for last 2 weeks')
    parser.add_argument('--csv', help='CSV output filename')
    parser.add_argument('--table', help='Table image output filename')
    
    args = parser.parse_args()
    
    cmd = GenerateStatusChangeReportDemoCommand()
    success = cmd.run(args.csv, args.table)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
