"""Command for syncing data from Yandex Tracker."""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.core.database import SessionLocal
from radiator.core.config import settings
from radiator.core.logging import logger
from radiator.crud.tracker import tracker_task, tracker_task_history, tracker_sync_log
from radiator.services.tracker_service import tracker_service
from radiator.models.tracker import TrackerSyncLog


class TrackerSyncCommand:
    """Command for syncing tracker data."""
    
    def __init__(self):
        self.db = SessionLocal()
        self.sync_log: Optional[TrackerSyncLog] = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()
    
    def create_sync_log(self) -> TrackerSyncLog:
        """Create new sync log entry."""
        sync_log = TrackerSyncLog(
            sync_started_at=datetime.utcnow(),
            status="running"
        )
        self.db.add(sync_log)
        self.db.commit()
        self.db.refresh(sync_log)
        return sync_log
    
    def update_sync_log(self, **kwargs):
        """Update sync log with new data."""
        if self.sync_log:
            for key, value in kwargs.items():
                if hasattr(self.sync_log, key):
                    setattr(self.sync_log, key, value)
            self.db.commit()
    
    def get_last_sync_time(self) -> datetime:
        """Get timestamp of last successful sync."""
        last_sync = tracker_sync_log.get_last_successful_sync(self.db)
        if last_sync:
            return last_sync.sync_completed_at
        else:
            # Default to 30 days ago if no previous sync
            return datetime.utcnow() - timedelta(days=30)
    
    def get_tasks_to_sync(self, sync_mode: str = "recent", filters: Dict[str, Any] = None, 
                          days: int = 30, limit: int = 100) -> List[str]:
        """
        Get list of tasks to sync based on different strategies.
        
        Args:
            sync_mode: Strategy for getting tasks
                - "recent": Get recently updated tasks
                - "active": Get active (non-closed) tasks
                - "filter": Use custom filters
                - "file": Load from file (legacy mode)
            filters: Custom filters for "filter" mode
            days: Number of days to look back for "recent" mode
            limit: Maximum number of tasks to sync
            
        Returns:
            List of task IDs to sync
        """
        try:
            if sync_mode == "recent":
                logger.info(f"Getting recent tasks updated in last {days} days")
                task_ids = tracker_service.get_recent_tasks(days=days, limit=limit)
                
            elif sync_mode == "active":
                logger.info("Getting active tasks")
                task_ids = tracker_service.get_active_tasks(limit=limit)
                
            elif sync_mode == "filter":
                logger.info(f"Getting tasks using custom filters: {filters}")
                task_ids = tracker_service.get_tasks_by_filter(filters, limit=limit)
                
            elif sync_mode == "file":
                # Legacy mode - load from file
                file_path = filters.get("file_path", "tasks.txt") if filters else "tasks.txt"
                task_ids = self.load_task_list(file_path)
                
            else:
                logger.warning(f"Unknown sync mode: {sync_mode}, falling back to recent tasks")
                task_ids = tracker_service.get_recent_tasks(days=days, limit=limit)
            
            logger.info(f"Found {len(task_ids)} tasks to sync")
            return task_ids
            
        except Exception as e:
            logger.error(f"Failed to get tasks to sync: {e}")
            return []
    
    def load_task_list(self, file_path: str) -> List[str]:
        """Load list of task IDs from file (legacy method)."""
        if not os.path.exists(file_path):
            logger.error(f"Task list file not found: {file_path}")
            return []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                task_ids = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            logger.info(f"Loaded {len(task_ids)} task IDs from {file_path}")
            return task_ids
        except Exception as e:
            logger.error(f"Failed to load task list: {e}")
            return []
    
    def sync_tasks(self, task_ids: List[str]) -> Dict[str, int]:
        """Sync tasks data from tracker."""
        logger.info(f"Starting sync for {len(task_ids)} tasks")
        
        # Get tasks data
        tasks_data = tracker_service.get_tasks_batch(task_ids)
        valid_tasks = []
        
        for task_id, task_data in tasks_data:
            if task_data:
                task_info = tracker_service.extract_task_data(task_data)
                valid_tasks.append(task_info)
            else:
                logger.warning(f"Failed to get data for task {task_id}")
        
        if not valid_tasks:
            logger.warning("No valid tasks data received")
            return {"created": 0, "updated": 0}
        
        # Save tasks to database
        result = tracker_task.bulk_create_or_update(self.db, valid_tasks)
        logger.info(f"Tasks sync completed: {result}")
        
        return result
    
    def sync_task_history(self, task_ids: List[str]) -> int:
        """Sync task history data."""
        logger.info(f"Starting history sync for {len(task_ids)} tasks")
        
        # Get changelogs
        changelogs_data = tracker_service.get_changelogs_batch(task_ids)
        total_history_entries = 0
        
        for task_id, changelog in changelogs_data:
            if not changelog:
                continue
            
            # Get task from database
            db_task = tracker_task.get_by_tracker_id(self.db, task_id)
            if not db_task:
                logger.warning(f"Task {task_id} not found in database, skipping history")
                continue
            
            # Extract status history
            status_history = tracker_service.extract_status_history(changelog)
            if not status_history:
                continue
            
            # Delete existing history for this task
            tracker_task_history.delete_by_task_id(self.db, db_task.id)
            
            # Prepare history data
            history_data = []
            for entry in status_history:
                history_entry = {
                    "task_id": db_task.id,
                    "tracker_id": task_id,
                    "status": entry["status"],
                    "status_display": entry["status_display"],
                    "start_date": entry["start_date"],
                    "end_date": entry.get("end_date")
                }
                history_data.append(history_entry)
            
            # Save history
            if history_data:
                created_count = tracker_task_history.bulk_create(self.db, history_data)
                total_history_entries += created_count
                logger.debug(f"Created {created_count} history entries for task {task_id}")
        
        logger.info(f"History sync completed: {total_history_entries} entries created")
        return total_history_entries
    
    def run(self, sync_mode: str = "recent", filters: Dict[str, Any] = None, 
            days: int = 30, limit: int = 100, force_full_sync: bool = False):
        """Run the sync command."""
        try:
            # Create sync log
            self.sync_log = self.create_sync_log()
            logger.info(f"Started sync operation: {self.sync_log.id}")
            logger.info(f"Sync mode: {sync_mode}")
            
            # Get tasks to sync
            task_ids = self.get_tasks_to_sync(sync_mode, filters, days, limit)
            if not task_ids:
                self.update_sync_log(
                    status="failed",
                    sync_completed_at=datetime.utcnow(),
                    error_details="No tasks found to sync"
                )
                return False
            
            self.update_sync_log(tasks_processed=len(task_ids))
            
            # Determine sync scope
            if force_full_sync:
                last_sync_time = datetime.utcnow() - timedelta(days=365)  # Very old date
                logger.info("Force full sync enabled")
            else:
                last_sync_time = self.get_last_sync_time()
                logger.info(f"Last sync time: {last_sync_time}")
            
            # Sync tasks
            tasks_result = self.sync_tasks(task_ids)
            self.update_sync_log(
                tasks_created=tasks_result["created"],
                tasks_updated=tasks_result["updated"]
            )
            
            # Sync history
            history_entries = self.sync_task_history(task_ids)
            
            # Mark sync as completed
            self.update_sync_log(
                status="completed",
                sync_completed_at=datetime.utcnow()
            )
            
            logger.info(f"Sync completed successfully: {tasks_result['created']} created, {tasks_result['updated']} updated, {history_entries} history entries")
            return True
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            if self.sync_log:
                self.update_sync_log(
                    status="failed",
                    sync_completed_at=datetime.utcnow(),
                    error_details=str(e)
                )
            return False


def main():
    """Main entry point for the sync command."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync data from Yandex Tracker")
    parser.add_argument(
        "--sync-mode",
        choices=["recent", "active", "filter", "file"],
        default="recent",
        help="Strategy for getting tasks to sync (default: recent)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to look back for recent tasks (default: 30)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of tasks to sync (default: 100)"
    )
    parser.add_argument(
        "--status",
        help="Filter by status (e.g., 'Open', 'In Progress')"
    )
    parser.add_argument(
        "--assignee",
        help="Filter by assignee"
    )
    parser.add_argument(
        "--team",
        help="Filter by team"
    )
    parser.add_argument(
        "--file-path",
        help="Path to task list file (for file mode)"
    )
    parser.add_argument(
        "--force-full-sync",
        action="store_true",
        help="Force full sync ignoring last sync time"
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
    
    # Build filters
    filters = {}
    if args.status:
        filters["status"] = args.status
    if args.assignee:
        filters["assignee"] = args.assignee
    if args.team:
        filters["team"] = args.team
    if args.file_path:
        filters["file_path"] = args.file_path
    
    # Run sync
    with TrackerSyncCommand() as sync_cmd:
        success = sync_cmd.run(
            sync_mode=args.sync_mode,
            filters=filters,
            days=args.days,
            limit=args.limit,
            force_full_sync=args.force_full_sync
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
