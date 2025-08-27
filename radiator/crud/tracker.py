"""CRUD operations for tracker models."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from radiator.models.tracker import TrackerTask, TrackerTaskHistory, TrackerSyncLog
from radiator.crud.base import CRUDBase


class CRUDTrackerTask(CRUDBase[TrackerTask, TrackerTask, TrackerTask]):
    """CRUD operations for TrackerTask model."""
    
    def get_by_tracker_id(self, db: Session, tracker_id: str) -> Optional[TrackerTask]:
        """Get task by tracker ID."""
        return db.query(TrackerTask).filter(TrackerTask.tracker_id == tracker_id).first()
    
    def get_tasks_modified_since(self, db: Session, since: datetime) -> List[TrackerTask]:
        """Get tasks modified since given datetime."""
        return db.query(TrackerTask).filter(
            TrackerTask.updated_at >= since
        ).all()
    
    def get_tasks_for_sync(self, db: Session, last_sync: datetime) -> List[TrackerTask]:
        """Get tasks that need to be synced."""
        return db.query(TrackerTask).filter(
            or_(
                TrackerTask.last_sync_at < last_sync,
                TrackerTask.last_sync_at.is_(None)
            )
        ).all()
    
    def bulk_create_or_update(self, db: Session, tasks_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Bulk create or update tasks."""
        created = 0
        updated = 0
        
        for task_data in tasks_data:
            tracker_id = task_data["tracker_id"]
            existing_task = self.get_by_tracker_id(db, tracker_id)
            
            if existing_task:
                # Update existing task - update ALL fields except tracker_id
                for key, value in task_data.items():
                    if key != "tracker_id" and hasattr(existing_task, key):
                        # Ensure we're setting the value even if it's None or empty string
                        setattr(existing_task, key, value)
                
                existing_task.updated_at = datetime.utcnow()
                existing_task.last_sync_at = datetime.utcnow()
                updated += 1
            else:
                # Create new task
                task_data["created_at"] = datetime.utcnow()
                task_data["updated_at"] = datetime.utcnow()
                task_data["last_sync_at"] = datetime.utcnow()
                new_task = TrackerTask(**task_data)
                db.add(new_task)
                created += 1
        
        db.commit()
        return {"created": created, "updated": updated}


class CRUDTrackerTaskHistory(CRUDBase[TrackerTaskHistory, TrackerTaskHistory, TrackerTaskHistory]):
    """CRUD operations for TrackerTaskHistory model."""
    
    def get_by_task_id(self, db: Session, task_id: int) -> List[TrackerTaskHistory]:
        """Get history by task ID."""
        return db.query(TrackerTaskHistory).filter(
            TrackerTaskHistory.task_id == task_id
        ).order_by(TrackerTaskHistory.start_date).all()
    
    def get_by_tracker_id(self, db: Session, tracker_id: str) -> List[TrackerTaskHistory]:
        """Get history by tracker ID."""
        return db.query(TrackerTaskHistory).filter(
            TrackerTaskHistory.tracker_id == tracker_id
        ).order_by(TrackerTaskHistory.start_date).all()
    
    def delete_by_task_id(self, db: Session, task_id: int) -> int:
        """Delete all history entries for a task."""
        result = db.query(TrackerTaskHistory).filter(
            TrackerTaskHistory.task_id == task_id
        ).delete()
        db.commit()
        return result
    
    def bulk_create(self, db: Session, history_data: List[Dict[str, Any]]) -> int:
        """Bulk create history entries."""
        history_entries = []
        for entry_data in history_data:
            entry_data["created_at"] = datetime.utcnow()
            history_entry = TrackerTaskHistory(**entry_data)
            history_entries.append(history_entry)
        
        db.add_all(history_entries)
        db.commit()
        return len(history_entries)


class CRUDTrackerSyncLog(CRUDBase[TrackerSyncLog, TrackerSyncLog, TrackerSyncLog]):
    """CRUD operations for TrackerSyncLog model."""
    
    def get_last_successful_sync(self, db: Session) -> Optional[TrackerSyncLog]:
        """Get last successful sync log."""
        return db.query(TrackerSyncLog).filter(
            TrackerSyncLog.status == "completed"
        ).order_by(TrackerSyncLog.sync_completed_at.desc()).first()
    
    def get_running_syncs(self, db: Session) -> List[TrackerSyncLog]:
        """Get all running sync operations."""
        return db.query(TrackerSyncLog).filter(
            TrackerSyncLog.status == "running"
        ).all()
    
    def mark_sync_failed(self, db: Session, sync_id: str, error_details: str) -> None:
        """Mark sync as failed."""
        sync_log = db.query(TrackerSyncLog).filter(
            TrackerSyncLog.id == sync_id
        ).first()
        if sync_log:
            sync_log.status = "failed"
            sync_log.error_details = error_details
            sync_log.sync_completed_at = datetime.utcnow()
            db.commit()


# Create instances
tracker_task = CRUDTrackerTask(TrackerTask)
tracker_task_history = CRUDTrackerTaskHistory(TrackerTaskHistory)
tracker_sync_log = CRUDTrackerSyncLog(TrackerSyncLog)
