"""Command for syncing data from Yandex Tracker."""

import os
import sys
import logging.config

# Disable SQLAlchemy logging BEFORE any imports
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": True,   # ключ: гасим уже созданные логгеры
    "handlers": {
        "null": {"class": "logging.NullHandler"}
    },
    "loggers": {
        "sqlalchemy":         {"handlers": ["null"], "level": "CRITICAL", "propagate": False},
        "sqlalchemy.engine":  {"handlers": ["null"], "level": "CRITICAL", "propagate": False},
        "sqlalchemy.pool":    {"handlers": ["null"], "level": "CRITICAL", "propagate": False},
    },
    "root": {"handlers": ["null"], "level": "WARNING"},
})

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
from tqdm import tqdm

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.core.database import SessionLocal
from radiator.core.config import settings
from radiator.core.logging import logger
from radiator.crud.tracker import tracker_task, tracker_task_history, tracker_sync_log
from radiator.services.tracker_service import tracker_service
from radiator.models.tracker import TrackerSyncLog
import logging


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
    
    def get_last_sync_time(self) -> datetime:
        """Get timestamp of last successful sync."""
        last_sync = tracker_sync_log.get_last_successful_sync(self.db)
        if last_sync:
            return last_sync.sync_completed_at
        else:
            # Default to 30 days ago if no previous sync
            return datetime.now(timezone.utc) - timedelta(days=30)
    
    def get_tasks_to_sync(self, filters: Dict[str, Any] = None, limit: int = 100) -> List[str]:
        """
        Get list of tasks to sync using filters.
        
        Args:
            filters: Custom filters for getting tasks
            limit: Maximum number of tasks to sync
            
        Returns:
            List of task IDs to sync
        """
        try:
            logger.info(f"Getting tasks using filters: {filters}")
            task_ids = tracker_service.get_tasks_by_filter(filters, limit=limit)
            
            logger.info(f"Found {len(task_ids)} tasks to sync")
            return task_ids
            
        except Exception as e:
            logger.error(f"Failed to get tasks to sync: {e}")
            return []
    
    def sync_tasks(self, task_ids: List[str]) -> Dict[str, int]:
        """Sync tasks data from tracker."""
        logger.info(f"Starting sync for {len(task_ids)} tasks")
        
        # Get tasks data with progress bar
        logger.info("📥 Получаем данные задач из Tracker...")
        tasks_data = tracker_service.get_tasks_batch(task_ids)
        valid_tasks = []
        
        # Process tasks with progress bar
        with tqdm(total=len(task_ids), desc="🔄 Обработка задач", unit="задача") as pbar:
            for i, (task_id, task_data) in enumerate(tasks_data, 1):
                if task_data:
                    task_info = tracker_service.extract_task_data(task_data)
                    valid_tasks.append(task_info)
                    pbar.set_postfix({"task": task_id[:8] + "..."})
                else:
                    logger.warning(f"Failed to get data for task {task_id} ({i}/{len(task_ids)})")
                pbar.update(1)
        
        if not valid_tasks:
            logger.warning("No valid tasks data received")
            return {"created": 0, "updated": 0}
        
        # Save tasks to database
        logger.info(f"💾 Сохраняем {len(valid_tasks)} задач в базу данных...")
        result = tracker_task.bulk_create_or_update(self.db, valid_tasks)
        logger.info(f"✅ Задачи синхронизированы: {result}")
        
        return result
    
    def sync_task_history(self, task_ids: List[str]) -> int:
        """Sync task history data."""
        logger.info(f"📚 Начинаем синхронизацию истории для {len(task_ids)} задач")
        
        # Get changelogs
        logger.info("📥 Получаем данные истории из Tracker...")
        changelogs_data = tracker_service.get_changelogs_batch(task_ids)
        total_history_entries = 0
        
        # Process history with progress bar
        with tqdm(total=len(task_ids), desc="🔄 Обработка истории", unit="задача") as pbar:
            for i, (task_id, changelog) in enumerate(changelogs_data, 1):
                if not changelog:
                    logger.debug(f"No changelog data for task {task_id} ({i}/{len(task_ids)})")
                    pbar.update(1)
                    continue
                
                # Get task from database
                db_task = tracker_task.get_by_tracker_id(self.db, task_id)
                if not db_task:
                    logger.warning(f"Task {task_id} not found in database, skipping history ({i}/{len(task_ids)})")
                    pbar.update(1)
                    continue
                
                # Extract status history
                status_history = tracker_service.extract_status_history(changelog)
                if not status_history:
                    logger.debug(f"No status history found for task {task_id} ({i}/{len(task_ids)})")
                    pbar.update(1)
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
                    pbar.set_postfix({"entries": created_count, "task": task_id[:8] + "..."})
                    logger.debug(f"Created {created_count} history entries for task {task_id} ({i}/{len(task_ids)})")
                
                pbar.update(1)
        
        logger.info(f"✅ История синхронизирована: {total_history_entries} записей создано для {len(task_ids)} задач")
        return total_history_entries
    
    def run(self, filters: Dict[str, Any] = None, limit: int = 100, force_full_sync: bool = False, skip_history: bool = False):
        """Run the sync command."""
        try:
            # Create sync log
            self.sync_log = self.create_sync_log()
            logger.info(f"Started sync operation: {self.sync_log.id}")
            logger.info("Sync mode: filters and limit")
            if skip_history:
                logger.info("History sync disabled")
            
            # Get tasks to sync
            logger.info(f"🚀 Начинаем синхронизацию...")
            logger.info(f"   📋 Фильтр: {filters}")
            logger.info(f"   🎯 Лимит: {limit} задач")
            
            task_ids = self.get_tasks_to_sync(filters, limit)
            if not task_ids:
                logger.error(f"❌ Не найдено задач для синхронизации")
                self.update_sync_log(
                    status="failed",
                    sync_completed_at=datetime.utcnow(),
                    error_details="No tasks found to sync"
                )
                return False
            
            logger.info(f"✅ Найдено {len(task_ids)} задач для синхронизации")
            
            self.update_sync_log(tasks_processed=len(task_ids))
            
            # Determine sync scope
            if force_full_sync:
                last_sync_time = datetime.utcnow() - timedelta(days=365)  # Very old date
                logger.info("🔄 Принудительная полная синхронизация включена")
            else:
                last_sync_time = self.get_last_sync_time()
                logger.info(f"⏰ Время последней синхронизации: {last_sync_time}")
            
            # Sync tasks
            logger.info("🔄 Начинаем синхронизацию задач...")
            tasks_result = self.sync_tasks(task_ids)
            self.update_sync_log(
                tasks_created=tasks_result["created"],
                tasks_updated=tasks_result["updated"]
            )
            
            # Sync history (if not skipped)
            history_entries = 0
            if skip_history:
                logger.info("⏭️ Пропускаем синхронизацию истории по запросу")
            else:
                history_entries = self.sync_task_history(task_ids)
            
            # Mark sync as completed
            self.update_sync_log(
                status="completed",
                sync_completed_at=datetime.now(timezone.utc)
            )
            
            logger.info(f"🎉 Синхронизация завершена успешно!")
            logger.info(f"   📝 Создано: {tasks_result['created']} задач")
            logger.info(f"   🔄 Обновлено: {tasks_result['updated']} задач")
            logger.info(f"   📚 Записей истории: {history_entries}")
            return True
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            if self.sync_log:
                self.update_sync_log(
                    status="failed",
                    sync_completed_at=datetime.now(timezone.utc),
                    error_details=str(e)
                )
            return False


def main():
    """Main entry point for the sync command."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sync data from Yandex Tracker with pagination support",
        epilog="""
Note: Yandex Tracker API returns maximum 50 records per page. 
The command automatically handles pagination to retrieve the requested number of tasks.
        """
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10000,
        help="Maximum number of tasks to sync (default: 10000, use 0 for unlimited)"
    )
    parser.add_argument(
        "--filter",
        type=str,
        help="Filter string for task selection (passed directly to tracker)"
    )

    parser.add_argument(
        "--force-full-sync",
        action="store_true",
        help="Force full sync ignoring last sync time"
    )
    parser.add_argument(
        "--skip-history",
        action="store_true",
        help="Skip syncing task history (faster sync for testing)"
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
    if args.filter:
        # Pass the filter string directly as a query
        filters["query"] = args.filter
    
    # Run sync
    with TrackerSyncCommand() as sync_cmd:
        success = sync_cmd.run(
            filters=filters,
            limit=args.limit,
            force_full_sync=args.force_full_sync,
            skip_history=args.skip_history
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
