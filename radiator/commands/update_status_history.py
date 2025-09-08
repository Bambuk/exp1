"""Command for updating status history for specific tasks."""

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.core.database import SessionLocal
from radiator.core.config import settings, with_default_limit
from radiator.core.logging import logger
from radiator.crud.tracker import tracker_task, tracker_task_history, tracker_sync_log
from radiator.services.tracker_service import tracker_service
from radiator.models.tracker import TrackerSyncLog
from radiator.models.tracker import TrackerTask


class UpdateStatusHistoryCommand:
    """Command for updating status history for specific tasks."""
    
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
            sync_started_at=datetime.now(timezone.utc),
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
    
    def get_tasks_with_recent_status_changes(self, queue: str = "CPO", days: int = 14) -> List[str]:
        """
        Get tasks that changed status in recent days from specific queue.
        
        Args:
            queue: Queue name to filter tasks
            days: Number of days to look back for status changes
            
        Returns:
            List of task IDs
        """
        try:
            # Build query for recent status changes in specific queue
            query = f'Queue: {queue} "Last status change": today()-{days}d..today() "Sort by": Updated DESC'
            logger.info(f"Searching for tasks with query: {query}")
            
            task_ids = tracker_service.search_tasks(query=query, limit=1000)
            logger.info(f"Found {len(task_ids)} tasks with recent status changes in queue {queue}")
            
            return task_ids
            
        except Exception as e:
            logger.error(f"Failed to get tasks with recent status changes: {e}")
            return []
    
    def update_status_history_for_tasks(self, task_ids: List[str], auto_sync_missing: bool = False) -> Dict[str, int]:
        """
        Update status history for specific tasks.
        
        Args:
            task_ids: List of task IDs to update history for
            auto_sync_missing: If True, automatically sync missing tasks before updating history
            
        Returns:
            Dictionary with counts of created and updated history entries
        """
        logger.info(f"Starting status history update for {len(task_ids)} tasks")
        
        total_created = 0
        total_updated = 0
        missing_tasks = []
        
        # First pass: identify missing tasks
        for task_id in task_ids:
            db_task = tracker_task.get_by_tracker_id(self.db, task_id)
            if not db_task:
                missing_tasks.append(task_id)
        
        # Auto-sync missing tasks if requested
        if missing_tasks and auto_sync_missing:
            logger.info(f"Found {len(missing_tasks)} missing tasks, attempting to sync them first...")
            try:
                self._sync_missing_tasks(missing_tasks)
                logger.info(f"Successfully synced {len(missing_tasks)} missing tasks")
            except Exception as e:
                logger.error(f"Failed to sync missing tasks: {e}")
                logger.warning("Continuing with existing tasks only")
        
        # Second pass: process all tasks (including newly synced ones)
        for task_id in task_ids:
            try:
                # Get task from database
                db_task = tracker_task.get_by_tracker_id(self.db, task_id)
                if not db_task:
                    logger.warning(f"Task {task_id} not found in database, skipping history update")
                    continue
                
                # Get changelog for this task
                changelog = tracker_service.get_task_changelog(task_id)
                if not changelog:
                    logger.debug(f"No changelog found for task {task_id}")
                    continue
                
                # Extract status history
                status_history = tracker_service.extract_status_history(changelog)
                if not status_history:
                    logger.debug(f"No status changes found for task {task_id}")
                    continue
                
                # Delete existing history for this task
                deleted_count = tracker_task_history.delete_by_task_id(self.db, db_task.id)
                logger.debug(f"Deleted {deleted_count} existing history entries for task {task_id}")
                
                # Prepare new history data
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
                
                # Save new history
                if history_data:
                    created_count = tracker_task_history.bulk_create(self.db, history_data)
                    total_created += created_count
                    logger.debug(f"Created {created_count} new history entries for task {task_id}")
                
                # Update task's last_sync_at timestamp
                db_task.last_sync_at = datetime.now(timezone.utc)
                self.db.commit()
                
            except Exception as e:
                logger.error(f"Failed to update status history for task {task_id}: {e}")
                continue
        
        logger.info(f"Status history update completed: {total_created} entries created")
        return {"created": total_created, "updated": total_updated}
    
    def _sync_missing_tasks(self, task_ids: List[str]) -> None:
        """
        Sync missing tasks from Yandex Tracker.
        
        Args:
            task_ids: List of task IDs to sync
        """
        logger.info(f"Syncing {len(task_ids)} missing tasks...")
        
        # Get tasks data in batch
        tasks_data = tracker_service.get_tasks_batch(task_ids)
        
        for task_id, task_data in tasks_data:
            if not task_data:
                logger.warning(f"Failed to get data for task {task_id}")
                continue
            
            try:
                # Extract task data
                task_info = tracker_service.extract_task_data(task_data)
                
                # Create new task in database
                new_task = TrackerTask(**task_info)
                self.db.add(new_task)
                self.db.commit()
                self.db.refresh(new_task)
                
                logger.debug(f"Successfully synced task {task_id}")
                
            except Exception as e:
                logger.error(f"Failed to sync task {task_id}: {e}")
                continue
        
        self.db.commit()
        logger.info(f"Task sync completed")
    
    def run(self, queue: str = "CPO", days: int = 14, limit: int = None, auto_sync_missing: bool = False) -> bool:
        """
        Run the status history update command.
        
        Args:
            queue: Queue name to filter tasks (default: CPO)
            days: Number of days to look back for status changes (default: 14)
            limit: Maximum number of tasks to process (uses default from config if None)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use default limit from config if not provided
            if limit is None:
                limit = settings.DEFAULT_LARGE_LIMIT
            
            # Create sync log
            self.sync_log = self.create_sync_log()
            logger.info(f"Started status history update: {self.sync_log.id}")
            logger.info(f"Queue: {queue}, Days: {days}, Limit: {limit}, Auto-sync: {auto_sync_missing}")
            
            # Get tasks with recent status changes
            task_ids = self.get_tasks_with_recent_status_changes(queue, days)
            if not task_ids:
                self.update_sync_log(
                    status="completed",
                    sync_completed_at=datetime.now(timezone.utc),
                    tasks_processed=0
                )
                logger.info("No tasks found for status history update")
                return True
            
            # Apply limit if specified
            if limit and len(task_ids) > limit:
                task_ids = task_ids[:limit]
                logger.info(f"Limited to {limit} tasks")
            
            self.update_sync_log(tasks_processed=len(task_ids))
            
            # Update status history
            history_result = self.update_status_history_for_tasks(task_ids, auto_sync_missing)
            
            # Mark sync as completed
            self.update_sync_log(
                status="completed",
                sync_completed_at=datetime.now(timezone.utc),
                tasks_created=history_result["created"],
                tasks_updated=history_result["updated"]
            )
            
            logger.info(f"Status history update completed successfully: {history_result['created']} entries created")
            return True
            
        except Exception as e:
            logger.error(f"Status history update failed: {e}")
            if self.sync_log:
                self.update_sync_log(
                    status="failed",
                    sync_completed_at=datetime.now(timezone.utc),
                    error_details=str(e)
                )
            return False


def main():
    """Main entry point for the status history update command."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Update status history for tasks with recent status changes")
    parser.add_argument(
        "--queue",
        default="CPO",
        help="Queue name to filter tasks (default: CPO)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Number of days to look back for status changes (default: 14)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=f"Maximum number of tasks to process (default: {settings.DEFAULT_LARGE_LIMIT})"
    )
    parser.add_argument(
        "--auto-sync",
        action="store_true",
        help="Automatically sync missing tasks before updating history"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel("DEBUG")
    
    with UpdateStatusHistoryCommand() as cmd:
        success = cmd.run(
            queue=args.queue,
            days=args.days,
            limit=args.limit,
            auto_sync_missing=args.auto_sync
        )
        
        if success:
            logger.info("Status history update completed successfully")
            sys.exit(0)
        else:
            logger.error("Status history update failed")
            sys.exit(1)


if __name__ == "__main__":
    main()
