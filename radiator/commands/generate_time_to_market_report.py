"""Command for generating Time To Delivery and Time To Market report for CPO tasks by authors/teams over defined periods."""

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import csv
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.core.database import SessionLocal
from radiator.core.config import settings
from radiator.core.logging import logger
from radiator.crud.tracker import tracker_task, tracker_task_history
from radiator.models.tracker import TrackerTask, TrackerTaskHistory


class GenerateTimeToMarketReportCommand:
    """Command for generating Time To Delivery and Time To Market report for CPO tasks by authors or teams over defined periods."""
    
    def __init__(self, group_by: str = "author"):
        """
        Initialize command with grouping preference.
        
        Args:
            group_by: Grouping field - "author" or "team"
        """
        if group_by not in ["author", "team"]:
            raise ValueError("group_by must be 'author' or 'team'")
        
        self.group_by = group_by
        self.db = SessionLocal()
        self.report_data: Dict[str, Dict[str, Any]] = {}
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()
    
    def _load_quarters(self) -> List[Dict[str, Any]]:
        """
        Load quarters/periods from file.
        
        Returns:
            List of dictionaries with quarter information
        """
        try:
            quarters_file = Path("data/config/quarters.txt")
            if not quarters_file.exists():
                logger.warning(f"Quarters file not found: {quarters_file}")
                return []
            
            quarters = []
            with open(quarters_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and ';' in line:
                        try:
                            name, start_str, end_str = line.split(';', 2)
                            start_date = datetime.strptime(start_str.strip(), '%Y-%m-%d')
                            end_date = datetime.strptime(end_str.strip(), '%Y-%m-%d')
                            
                            quarters.append({
                                'name': name.strip(),
                                'start_date': start_date,
                                'end_date': end_date
                            })
                        except ValueError as e:
                            logger.warning(f"Failed to parse quarter line '{line}': {e}")
                            continue
            
            logger.info(f"Loaded {len(quarters)} quarters")
            return quarters
            
        except Exception as e:
            logger.error(f"Failed to load quarters: {e}")
            return []
    
    def _load_status_mapping(self) -> Dict[str, str]:
        """
        Load status to block mapping from file.
        
        Returns:
            Dictionary mapping status names to block names (discovery/delivery/done)
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
    
    def _get_target_statuses(self, status_mapping: Dict[str, str]) -> Dict[str, List[str]]:
        """
        Extract target statuses for each metric.
        
        Args:
            status_mapping: Status to block mapping
            
        Returns:
            Dictionary with discovery and done status lists
        """
        discovery_statuses = [status for status, block in status_mapping.items() if block == 'discovery']
        done_statuses = [status for status, block in status_mapping.items() if block == 'done']
        
        return {
            'discovery': discovery_statuses,
            'done': done_statuses
        }
    
    def _calculate_time_to_delivery(self, task_created_at: datetime, history_data: List[Dict[str, Any]], target_statuses: List[str]) -> Optional[int]:
        """
        Calculate Time To Delivery (days from creation to first discovery status).
        
        Args:
            task_created_at: Task creation date (not used, we use history data)
            history_data: List of status history entries
            target_statuses: List of discovery status names
            
        Returns:
            Number of days or None if not found
        """
        try:
            if not history_data:
                return None
            
            # Find the earliest date in history (actual task creation)
            earliest_date = min(entry['start_date'] for entry in history_data)
            
            for entry in history_data:
                if entry['status'] in target_statuses:
                    # Calculate days between earliest date and first discovery status
                    days = (entry['start_date'] - earliest_date).days
                    return max(0, days)  # Ensure non-negative
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to calculate Time To Delivery: {e}")
            return None
    
    def _calculate_time_to_market(self, task_created_at: datetime, history_data: List[Dict[str, Any]], target_statuses: List[str]) -> Optional[int]:
        """
        Calculate Time To Market (days from creation to first done status).
        
        Args:
            task_created_at: Task creation date (not used, we use history data)
            history_data: List of status history entries
            target_statuses: List of done status names
            
        Returns:
            Number of days or None if not found
        """
        try:
            if not history_data:
                return None
            
            # Find the earliest date in history (actual task creation)
            earliest_date = min(entry['start_date'] for entry in history_data)
            
            for entry in history_data:
                if entry['status'] in target_statuses:
                    # Calculate days between earliest date and first done status
                    days = (entry['start_date'] - earliest_date).days
                    return max(0, days)  # Ensure non-negative
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to calculate Time To Market: {e}")
            return None
    
    def _calculate_statistics(self, times: List[int]) -> Dict[str, Optional[float]]:
        """
        Calculate mean and 85th percentile for a list of times.
        
        Args:
            times: List of time values in days
            
        Returns:
            Dictionary with mean and p85 values
        """
        if not times:
            return {'mean': None, 'p85': None}
        
        try:
            mean = np.mean(times)
            p85 = np.percentile(times, 85)
            
            return {
                'mean': float(mean),
                'p85': float(p85)
            }
            
        except Exception as e:
            logger.warning(f"Failed to calculate statistics: {e}")
            return {'mean': None, 'p85': None}
    
    def _get_tasks_for_period(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Get CPO tasks that reached target statuses within the specified period.
        
        Args:
            start_date: Period start date
            end_date: Period end date
            
        Returns:
            List of task dictionaries
        """
        try:
            if self.group_by == "author":
                group_field = TrackerTask.author
                filter_condition = TrackerTask.author.isnot(None)
            else:  # team
                group_field = TrackerTask.team
                filter_condition = TrackerTask.team.isnot(None)
            
            # Load status mapping to get target statuses
            status_mapping = self._load_status_mapping()
            target_statuses = self._get_target_statuses(status_mapping)
            
            discovery_statuses = target_statuses['discovery']
            done_statuses = target_statuses['done']
            all_target_statuses = discovery_statuses + done_statuses
            
            if not all_target_statuses:
                logger.warning("No target statuses found")
                return []
            
            # Get tasks that have target status transitions in the period using JOIN
            tasks_query = self.db.query(
                TrackerTask.id,
                TrackerTask.key,
                group_field,
                TrackerTask.created_at
            ).join(
                TrackerTaskHistory, TrackerTask.id == TrackerTaskHistory.task_id
            ).filter(
                filter_condition,
                TrackerTask.key.like('CPO-%'),
                TrackerTaskHistory.status.in_(all_target_statuses),
                TrackerTaskHistory.start_date >= start_date,
                TrackerTaskHistory.start_date <= end_date
            ).distinct()
            
            tasks = tasks_query.all()
            logger.info(f"Found {len(tasks)} CPO tasks with target transitions in period {start_date.date()} - {end_date.date()}")
            
            result = []
            for task_id, key, group_value, created_at in tasks:
                if group_value:  # Double check group value is not None
                    try:
                        # Handle potential encoding issues
                        if isinstance(group_value, bytes):
                            group_value = group_value.decode('utf-8', errors='replace')
                        elif isinstance(group_value, str):
                            # Ensure it's valid UTF-8
                            group_value.encode('utf-8').decode('utf-8')
                        
                        result.append({
                            'id': task_id,
                            'key': key,
                            'group_value': group_value,
                            'author': group_value if self.group_by == "author" else None,
                            'team': group_value if self.group_by == "team" else None,
                            'created_at': created_at
                        })
                        
                    except (UnicodeDecodeError, UnicodeEncodeError) as e:
                        logger.warning(f"Skipping task with encoding issue: {e}, task_id: {task_id}")
                        continue
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get tasks for period: {e}")
            return []
    
    
    def _get_task_history(self, task_id: int) -> List[Dict[str, Any]]:
        """
        Get status history for a specific task.
        
        Args:
            task_id: Task ID
            
        Returns:
            List of status history entries
        """
        try:
            history_query = self.db.query(
                TrackerTaskHistory.status,
                TrackerTaskHistory.status_display,
                TrackerTaskHistory.start_date,
                TrackerTaskHistory.end_date
            ).filter(
                TrackerTaskHistory.task_id == task_id
            ).order_by(
                TrackerTaskHistory.start_date
            )
            
            history = history_query.all()
            
            result = []
            for status, status_display, start_date, end_date in history:
                result.append({
                    'status': status,
                    'status_display': status_display,
                    'start_date': start_date,
                    'end_date': end_date
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get task history for task_id {task_id}: {e}")
            return []
    
    def generate_report_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Generate report data for all quarters.
        
        Returns:
            Dictionary with report data organized by quarter and group
        """
        try:
            # Load configuration
            quarters = self._load_quarters()
            status_mapping = self._load_status_mapping()
            target_statuses = self._get_target_statuses(status_mapping)
            
            if not quarters:
                logger.warning("No quarters found, returning empty report")
                return {}
            
            if not target_statuses['discovery'] or not target_statuses['done']:
                logger.warning("No target statuses found, returning empty report")
                return {}
            
            report_data = {}
            
            for quarter in quarters:
                quarter_name = quarter['name']
                start_date = quarter['start_date']
                end_date = quarter['end_date']
                
                logger.info(f"Processing quarter: {quarter_name}")
                
                # Get tasks for this quarter
                tasks = self._get_tasks_for_period(start_date, end_date)
                
                # Group tasks by author/team
                group_data = defaultdict(lambda: {
                    'ttd_times': [],
                    'ttm_times': []
                })
                
                for task in tasks:
                    group_value = task['group_value']
                    task_id = task['id']
                    created_at = task['created_at']
                    
                    # Get task history
                    history = self._get_task_history(task_id)
                    
                    if not history:
                        logger.debug(f"No history found for task {task['key']}")
                        continue
                    
                    # Calculate Time To Delivery
                    ttd = self._calculate_time_to_delivery(created_at, history, target_statuses['discovery'])
                    if ttd is not None:
                        group_data[group_value]['ttd_times'].append(ttd)
                    
                    # Calculate Time To Market
                    ttm = self._calculate_time_to_market(created_at, history, target_statuses['done'])
                    if ttm is not None:
                        group_data[group_value]['ttm_times'].append(ttm)
                
                # Calculate statistics for each group
                quarter_data = {}
                for group_value, data in group_data.items():
                    if data['ttd_times'] or data['ttm_times']:
                        ttd_stats = self._calculate_statistics(data['ttd_times'])
                        ttm_stats = self._calculate_statistics(data['ttm_times'])
                        
                        quarter_data[group_value] = {
                            'tasks_count': len(data['ttd_times']) + len(data['ttm_times']),
                            'ttd_times': data['ttd_times'],
                            'ttm_times': data['ttm_times'],
                            'ttd_mean': ttd_stats['mean'],
                            'ttd_p85': ttd_stats['p85'],
                            'ttm_mean': ttm_stats['mean'],
                            'ttm_p85': ttm_stats['p85']
                        }
                
                if quarter_data:
                    report_data[quarter_name] = quarter_data
            
            self.report_data = report_data
            logger.info(f"Generated report data for {len(report_data)} quarters")
            return report_data
            
        except Exception as e:
            logger.error(f"Failed to generate report data: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def generate_csv(self, filepath: str = None, report_type: str = "both") -> str:
        """
        Generate CSV report for TTD, TTM, or both.
        
        Args:
            filepath: Output file path (optional)
            report_type: "ttd", "ttm", or "both"
            
        Returns:
            Path to generated CSV file
        """
        try:
            if not self.report_data:
                logger.warning("No report data available. Run generate_report_data() first.")
                return ""
            
            if not filepath:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if report_type == "ttd":
                    filepath = f"reports/time_to_delivery_report_{timestamp}.csv"
                elif report_type == "ttm":
                    filepath = f"reports/time_to_market_report_{timestamp}.csv"
                else:
                    filepath = f"reports/time_to_market_report_{timestamp}.csv"
            
            # Ensure reports directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            # Collect all unique groups across all quarters
            all_groups = set()
            for quarter_data in self.report_data.values():
                all_groups.update(quarter_data.keys())
            all_groups = sorted(all_groups)
            
            quarters = sorted(self.report_data.keys())
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                # Create dynamic fieldnames based on quarters and report type
                fieldnames = ['group_name']
                for quarter in quarters:
                    if report_type in ["ttd", "both"]:
                        fieldnames.extend([
                            f'{quarter}_ttd_mean',
                            f'{quarter}_ttd_p85', 
                            f'{quarter}_ttd_tasks'
                        ])
                    if report_type in ["ttm", "both"]:
                        fieldnames.extend([
                            f'{quarter}_ttm_mean',
                            f'{quarter}_ttm_p85',
                            f'{quarter}_ttm_tasks'
                        ])
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for group_name in all_groups:
                    row = {'group_name': group_name}
                    
                    for quarter in quarters:
                        quarter_data = self.report_data.get(quarter, {})
                        data = quarter_data.get(group_name, {})
                        
                        if data:
                            if report_type in ["ttd", "both"]:
                                row.update({
                                    f'{quarter}_ttd_mean': data.get('ttd_mean'),
                                    f'{quarter}_ttd_p85': data.get('ttd_p85'),
                                    f'{quarter}_ttd_tasks': data.get('tasks_count')
                                })
                            if report_type in ["ttm", "both"]:
                                row.update({
                                    f'{quarter}_ttm_mean': data.get('ttm_mean'),
                                    f'{quarter}_ttm_p85': data.get('ttm_p85'),
                                    f'{quarter}_ttm_tasks': data.get('tasks_count')
                                })
                        else:
                            if report_type in ["ttd", "both"]:
                                row.update({
                                    f'{quarter}_ttd_mean': '',
                                    f'{quarter}_ttd_p85': '',
                                    f'{quarter}_ttd_tasks': ''
                                })
                            if report_type in ["ttm", "both"]:
                                row.update({
                                    f'{quarter}_ttm_mean': '',
                                    f'{quarter}_ttm_p85': '',
                                    f'{quarter}_ttm_tasks': ''
                                })
                    
                    writer.writerow(row)
            
            logger.info(f"CSV report saved to: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate CSV: {e}")
            raise
    
    def generate_table(self, filepath: str = None, report_type: str = "both") -> str:
        """
        Generate visual table report for TTD, TTM, or both.
        
        Args:
            filepath: Output file path (optional)
            report_type: "ttd", "ttm", or "both"
            
        Returns:
            Path to generated table file
        """
        try:
            if not self.report_data:
                logger.warning("No report data available. Run generate_report_data() first.")
                return ""
            
            if not filepath:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if report_type == "ttd":
                    filepath = f"reports/time_to_delivery_table_{timestamp}.png"
                elif report_type == "ttm":
                    filepath = f"reports/time_to_market_table_{timestamp}.png"
                else:
                    filepath = f"reports/time_to_market_table_{timestamp}.png"
            
            # Ensure reports directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            # Collect all unique groups across all quarters
            all_groups = set()
            for quarter_data in self.report_data.values():
                all_groups.update(quarter_data.keys())
            all_groups = sorted(all_groups)
            
            quarters = sorted(self.report_data.keys())
            
            # Data will be prepared separately for each section
            
            if not all_groups:
                logger.warning("No data to display in table")
                return ""
            
            # Create table - optimized for smaller file size
            fig_width = max(12, len(quarters) * 1.8 + 2)
            # Limit height for very large datasets to prevent extremely tall images
            max_height = 20
            fig_height = min(max_height, max(6, len(all_groups) * 0.15 + 2))
            
            # Adjust height based on report type
            if report_type == "both":
                fig_height = min(max_height, max(8, len(all_groups) * 0.2 + 4))
            
            fig = plt.figure(figsize=(fig_width, fig_height))
            
            # Determine which sections to show
            show_ttd = report_type in ["ttd", "both"]
            show_ttm = report_type in ["ttm", "both"]
            
            # TTD section
            if show_ttd:
                if report_type == "both":
                    ax1 = fig.add_axes([0.05, 0.55, 0.9, 0.4])
                else:
                    ax1 = fig.add_axes([0.05, 0.1, 0.9, 0.8])
                ax1.axis('off')
            
            # Create TTD table if needed
            if show_ttd:
                # Prepare data with proper structure
                ttd_table_data = []
                for group in all_groups:
                    row = [group]
                    for quarter in quarters:
                        quarter_data = self.report_data.get(quarter, {})
                        data = quarter_data.get(group, {})
                        if data:
                            ttd_avg = data.get('ttd_mean', 0) or 0
                            ttd_p85 = data.get('ttd_p85', 0) or 0
                            tasks = data.get('tasks_count', 0)
                            row.extend([f"{ttd_avg:.1f}", f"{ttd_p85:.1f}", str(tasks)])
                        else:
                            row.extend(["", "", ""])
                    ttd_table_data.append(row)
                
                # Create two-level headers - combine periods and metrics
                ttd_headers = ['Group']
                for quarter in quarters:
                    ttd_headers.extend([f'{quarter}\nAvg', f'{quarter}\n85%', f'{quarter}\nTasks'])
                
                # Create table
                ttd_table = ax1.table(cellText=ttd_table_data,
                                     colLabels=ttd_headers,
                                     cellLoc='center',
                                     loc='center',
                                     colWidths=[0.15] + [0.28/len(quarters)] * (len(quarters) * 3))
                
                # Style TTD table - optimized for smaller file size and large datasets
                ttd_table.auto_set_font_size(False)
                # Use smaller font for large datasets
                font_size = 5 if len(all_groups) > 30 else 6
                ttd_table.set_fontsize(font_size)
                # Reduce scaling for large datasets
                scale_y = 0.8 if len(all_groups) > 30 else 1.2
                ttd_table.scale(1.0, scale_y)
                
                # Style TTD header row
                for i in range(len(ttd_headers)):
                    ttd_table[(0, i)].set_facecolor('#4CAF50')
                    ttd_table[(0, i)].set_text_props(weight='bold', color='white')
                
                # Style TTD data rows
                for i in range(1, len(ttd_table_data) + 1):
                    for j in range(len(ttd_headers)):
                        cell = ttd_table[(i, j)]
                        if i % 2 == 0:
                            cell.set_facecolor('#F5F5F5')
                        else:
                            cell.set_facecolor('#FFFFFF')
                        
                        if j == 0:  # Group column
                            cell.set_text_props(ha='left', va='center')
                        else:  # Data columns
                            cell.set_text_props(ha='center', va='center')
                
                ax1.set_title('Time To Delivery (days)', fontsize=12, fontweight='bold', pad=10)
            
            # TTM section
            if show_ttm:
                if report_type == "both":
                    ax2 = fig.add_axes([0.05, 0.05, 0.9, 0.4])
                else:
                    ax2 = fig.add_axes([0.05, 0.1, 0.9, 0.8])
                ax2.axis('off')
                
                # Prepare data with proper structure
                ttm_table_data = []
                for group in all_groups:
                    row = [group]
                    for quarter in quarters:
                        quarter_data = self.report_data.get(quarter, {})
                        data = quarter_data.get(group, {})
                        if data:
                            ttm_avg = data.get('ttm_mean', 0) or 0
                            ttm_p85 = data.get('ttm_p85', 0) or 0
                            tasks = data.get('tasks_count', 0)
                            row.extend([f"{ttm_avg:.1f}", f"{ttm_p85:.1f}", str(tasks)])
                        else:
                            row.extend(["", "", ""])
                    ttm_table_data.append(row)
                
                # Create two-level headers - combine periods and metrics
                ttm_headers = ['Group']
                for quarter in quarters:
                    ttm_headers.extend([f'{quarter}\nAvg', f'{quarter}\n85%', f'{quarter}\nTasks'])
                
                # Create table
                ttm_table = ax2.table(cellText=ttm_table_data,
                                     colLabels=ttm_headers,
                                     cellLoc='center',
                                     loc='center',
                                     colWidths=[0.15] + [0.28/len(quarters)] * (len(quarters) * 3))
                
                # Style TTM table - optimized for smaller file size and large datasets
                ttm_table.auto_set_font_size(False)
                # Use smaller font for large datasets
                font_size = 5 if len(all_groups) > 30 else 6
                ttm_table.set_fontsize(font_size)
                # Reduce scaling for large datasets
                scale_y = 0.8 if len(all_groups) > 30 else 1.2
                ttm_table.scale(1.0, scale_y)
                
                # Style TTM header row
                for i in range(len(ttm_headers)):
                    ttm_table[(0, i)].set_facecolor('#2196F3')
                    ttm_table[(0, i)].set_text_props(weight='bold', color='white')
                
                # Style TTM data rows
                for i in range(1, len(ttm_table_data) + 1):
                    for j in range(len(ttm_headers)):
                        cell = ttm_table[(i, j)]
                        if i % 2 == 0:
                            cell.set_facecolor('#F5F5F5')
                        else:
                            cell.set_facecolor('#FFFFFF')
                        
                        if j == 0:  # Group column
                            cell.set_text_props(ha='left', va='center')
                        else:  # Data columns
                            cell.set_text_props(ha='center', va='center')
                
                ax2.set_title('Time To Market (days)', fontsize=12, fontweight='bold', pad=10)
            
            # Main title - smaller font for optimization
            if report_type == "ttd":
                title = f'Time To Delivery Report - {self.group_by.title()} Grouping'
            elif report_type == "ttm":
                title = f'Time To Market Report - {self.group_by.title()} Grouping'
            else:
                title = f'Time To Delivery & Time To Market Report - {self.group_by.title()} Grouping'
            
            fig.suptitle(title, fontsize=12, fontweight='bold', y=0.95)
            
            # Save with optimized settings for smaller file size
            plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white', 
                       pad_inches=0.1, edgecolor='none', transparent=False)
            plt.close()
            
            logger.info(f"Table saved to: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate table: {e}")
            raise
    
    def print_summary(self, report_type: str = "both"):
        """Print summary of the report to console."""
        if not self.report_data:
            print("No report data available. Run generate_report_data() first.")
            return
        
        print("\n" + "="*120)
        group_name = "AUTHORS" if self.group_by == "author" else "TEAMS"
        
        if report_type == "ttd":
            title = f"TIME TO DELIVERY REPORT BY {group_name}"
        elif report_type == "ttm":
            title = f"TIME TO MARKET REPORT BY {group_name}"
        else:
            title = f"TIME TO DELIVERY & TIME TO MARKET REPORT BY {group_name}"
        
        print(title)
        print("="*120)
        
        # Collect all unique groups across all quarters
        all_groups = set()
        for quarter_data in self.report_data.values():
            all_groups.update(quarter_data.keys())
        all_groups = sorted(all_groups)
        
        # Print header
        quarters = sorted(self.report_data.keys())
        header = f"{'Group':<25}"
        for quarter in quarters:
            header += f"{quarter:>20}"
        print(header)
        print("-" * 120)
        
        # Print TTD section if needed
        if report_type in ["ttd", "both"]:
            print("Time To Delivery (days):")
            print(f"{'':<25}", end="")
            for quarter in quarters:
                print(f"{'Avg':>8} {'85%':>8} {'Tasks':>4}", end="")
            print()
            
            for group in all_groups:
                line = f"{group:<25}"
                for quarter in quarters:
                    quarter_data = self.report_data.get(quarter, {})
                    data = quarter_data.get(group, {})
                    if data:
                        ttd_avg = data.get('ttd_mean', 0) or 0
                        ttd_p85 = data.get('ttd_p85', 0) or 0
                        tasks = data.get('tasks_count', 0)
                        line += f"{ttd_avg:>8.1f}{ttd_p85:>8.1f}{tasks:>4}"
                    else:
                        line += f"{'':>8}{'':>8}{'':>4}"
                print(line)
            
            print()
        
        # Print TTM section if needed
        if report_type in ["ttm", "both"]:
            print("Time To Market (days):")
            print(f"{'':<25}", end="")
            for quarter in quarters:
                print(f"{'Avg':>8} {'85%':>8} {'Tasks':>4}", end="")
            print()
            
            for group in all_groups:
                line = f"{group:<25}"
                for quarter in quarters:
                    quarter_data = self.report_data.get(quarter, {})
                    data = quarter_data.get(group, {})
                    if data:
                        ttm_avg = data.get('ttm_mean', 0) or 0
                        ttm_p85 = data.get('ttm_p85', 0) or 0
                        tasks = data.get('tasks_count', 0)
                        line += f"{ttm_avg:>8.1f}{ttm_p85:>8.1f}{tasks:>4}"
                    else:
                        line += f"{'':>8}{'':>8}{'':>4}"
                print(line)
        
        # Print totals
        print("-" * 120)
        total_tasks = 0
        for quarter_data in self.report_data.values():
            quarter_tasks = sum(data['tasks_count'] for data in quarter_data.values())
            total_tasks += quarter_tasks
        
        print(f"Total tasks analyzed: {total_tasks}")
        print("="*120)


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
    
    args = parser.parse_args()
    
    try:
        with GenerateTimeToMarketReportCommand(group_by=args.group_by) as cmd:
            # Generate report data
            cmd.generate_report_data()
            
            # Generate outputs
            csv_file = cmd.generate_csv(args.csv, args.report_type)
            table_file = cmd.generate_table(args.table, args.report_type)
            
            # Print summary
            cmd.print_summary(args.report_type)
            
            print(f"\nReport generated successfully!")
            if csv_file:
                print(f"CSV file: {csv_file}")
            if table_file:
                print(f"Table file: {table_file}")
                
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
