"""Command line tool for searching tasks in Yandex Tracker."""

import argparse
import sys
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from radiator.core.config import settings, log_limit_info
from radiator.core.logging import logger
from radiator.services.tracker_service import tracker_service


class TaskSearchCommand:
    """Command line tool for searching tasks."""
    
    def __init__(self):
        self.tracker_service = tracker_service
    
    def search_tasks(self, query: str, limit: int = None, output_format: str = "table") -> List[Dict[str, Any]]:
        """
        Search tasks using custom query.
        
        Args:
            query: Yandex Tracker search query
            limit: Maximum number of tasks to return (uses default from config if None)
            output_format: Output format (table, json, csv)
            
        Returns:
            List of task data dictionaries
        """
        try:
            log_limit_info(f"Searching tasks with query: {query}", limit)
            
            # Get task IDs from search
            task_ids = self.tracker_service.search_tasks(query=query, limit=limit)
            
            if not task_ids:
                logger.info("No tasks found matching the query")
                return []
            
            logger.info(f"Found {len(task_ids)} tasks, fetching details...")
            
            # Get full task data
            tasks_data = self.tracker_service.get_tasks_batch(task_ids)
            tasks = []
            
            for task_id, task_data in tasks_data:
                if task_data:
                    task_info = self.tracker_service.extract_task_data(task_data)
                    # Add original ID for reference
                    task_info["id"] = task_id
                    tasks.append(task_info)
                else:
                    logger.warning(f"Failed to get data for task {task_id}")
            
            logger.info(f"Successfully retrieved {len(tasks)} task details")
            return tasks
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def format_output(self, tasks: List[Dict[str, Any]], output_format: str = "table") -> str:
        """Format tasks output in specified format."""
        if not tasks:
            return "No tasks found."
        
        if output_format == "json":
            import json
            return json.dumps(tasks, indent=2, ensure_ascii=False, default=str)
        
        elif output_format == "csv":
            import csv
            from io import StringIO
            
            if not tasks:
                return ""
            
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=tasks[0].keys())
            writer.writeheader()
            writer.writerows(tasks)
            return output.getvalue()
        
        else:  # table format
            return self._format_table(tasks)
    
    def _format_table(self, tasks: List[Dict[str, Any]]) -> str:
        """Format tasks as a table."""
        if not tasks:
            return "No tasks found."
        
        # Define columns to display
        columns = ["id", "key", "summary", "status", "assignee", "author"]
        
        # Calculate column widths
        widths = {}
        for col in columns:
            max_width = len(col)
            for task in tasks:
                value = str(task.get(col, ""))[:50]  # Truncate long values
                max_width = max(max_width, len(value))
            widths[col] = max_width
        
        # Build table header
        header = " | ".join(f"{col:<{widths[col]}}" for col in columns)
        separator = "-" * len(header)
        
        # Build table rows
        rows = []
        for task in tasks:
            row = " | ".join(
                f"{str(task.get(col, ''))[:widths[col]]:<{widths[col]}}" 
                for col in columns
            )
            rows.append(row)
        
        return f"{header}\n{separator}\n" + "\n".join(rows)
    
    def run(self, query: str, limit: int = None, output_format: str = "table") -> bool:
        """Run the search command."""
        try:
            # Search for tasks
            tasks = self.search_tasks(query=query, limit=limit, output_format=output_format)
            
            if not tasks:
                print("No tasks found matching the query.")
                return True
            
            # Format and display output
            output = self.format_output(tasks, output_format)
            print(output)
            
            # Summary
            print(f"\nFound {len(tasks)} tasks")
            return True
            
        except Exception as e:
            logger.error(f"Search command failed: {e}")
            print(f"Error: {e}")
            return False


def main():
    """Main entry point for the search command."""
    parser = argparse.ArgumentParser(
        description="Search tasks in Yandex Tracker using custom queries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search by queue and status
  python -m radiator.commands.search_tasks 'Queue: CPO Status: "Арх. ревью"'
  
  # Search with date range
  python -m radiator.commands.search_tasks 'Queue: CPO Status: changed( to: "Арх. ревью" date: 2025-07-10 .. 2025-08-17)'
  
  # Search active tasks
  python -m radiator.commands.search_tasks 'Status: "In Progress"'
  
  # Search by assignee
  python -m radiator.commands.search_tasks 'Assignee: "Иван Иванов"'
  
  # Search with limit
  python -m radiator.commands.search_tasks 'Queue: CPO' --limit 50
  
  # Output in JSON format
  python -m radiator.commands.search_tasks 'Queue: CPO' --format json
        """
    )
    
    parser.add_argument(
        "query",
        help="Yandex Tracker search query (e.g., 'Queue: CPO Status: Open')"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=f"Maximum number of tasks to return (default: {settings.DEFAULT_SEARCH_LIMIT})"
    )
    
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format (default: table)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel("DEBUG")
    
    # Check required environment variables
    if not settings.TRACKER_API_TOKEN:
        logger.error("TRACKER_API_TOKEN environment variable is required")
        sys.exit(1)
    
    if not settings.TRACKER_ORG_ID:
        logger.error("TRACKER_ORG_ID environment variable is required")
        sys.exit(1)
    
    # Run search
    search_cmd = TaskSearchCommand()
    success = search_cmd.run(
        query=args.query,
        limit=args.limit,
        output_format=args.format
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
