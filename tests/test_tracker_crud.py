"""Tests for tracker CRUD operations."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from radiator.models.tracker import TrackerTask, TrackerTaskHistory, TrackerSyncLog
from radiator.crud.tracker import (
    CRUDTrackerTask,
    CRUDTrackerTaskHistory,
    CRUDTrackerSyncLog
)


class TestCRUDTrackerTask:
    """Test CRUD operations for TrackerTask."""

    @pytest.fixture
    def crud(self):
        """Create CRUD instance."""
        return CRUDTrackerTask(TrackerTask)

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for testing."""
        return {
            "tracker_id": "TEST-1",
            "key": "TEST-123",
            "summary": "Test Task",
            "description": "Test Description",
            "status": "open",
            "author": "user1",
            "assignee": "Test User",
            "business_client": "Test Client",
            "team": "frontend",
            "prodteam": "development",
            "profit_forecast": "high"
        }

    def test_create_task(self, crud, db_session, sample_task_data):
        """Test creating a single task."""
        # Create task in database
        task = TrackerTask(**sample_task_data)
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        
        # Verify task was created
        assert task.id is not None
        assert task.tracker_id == "TEST-1"
        assert task.key == "TEST-123"
        assert task.summary == "Test Task"
        assert task.status == "open"
        assert task.created_at is not None
        assert task.updated_at is not None
        
        # Cleanup
        db_session.delete(task)
        db_session.commit()

    def test_get_by_tracker_id(self, crud, db_session, sample_task_data):
        """Test getting task by tracker ID."""
        # Create task in database
        task = TrackerTask(**sample_task_data)
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        
        # Get task by tracker ID
        retrieved_task = crud.get_by_tracker_id(db_session, "TEST-1")
        
        # Verify task was retrieved
        assert retrieved_task is not None
        assert retrieved_task.tracker_id == "TEST-1"
        assert retrieved_task.key == "TEST-123"
        assert retrieved_task.summary == "Test Task"
        
        # Cleanup
        db_session.delete(task)
        db_session.commit()

    def test_get_by_tracker_id_not_found(self, crud, db_session):
        """Test getting task by tracker ID when not found."""
        # Try to get non-existent task
        retrieved_task = crud.get_by_tracker_id(db_session, "NONEXISTENT")
        
        # Verify task was not found
        assert retrieved_task is None

    def test_update_task(self, crud, db_session, sample_task_data):
        """Test updating a task."""
        # Create task in database
        task = TrackerTask(**sample_task_data)
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        
        # Update task
        task.status = "in_progress"
        task.summary = "Updated Task"
        db_session.commit()
        db_session.refresh(task)
        
        # Verify task was updated
        assert task.status == "in_progress"
        assert task.summary == "Updated Task"
        assert task.key == "TEST-123"
        assert task.updated_at > task.created_at
        
        # Cleanup
        db_session.delete(task)
        db_session.commit()

    def test_delete_task(self, crud, db_session, sample_task_data):
        """Test deleting a task."""
        # Create task in database
        task = TrackerTask(**sample_task_data)
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        
        task_id = task.id
        
        # Delete task
        db_session.delete(task)
        db_session.commit()
        
        # Verify task was deleted
        retrieved_task = crud.get_by_tracker_id(db_session, "TEST-1")
        assert retrieved_task is None

    def test_get_tasks_by_status(self, crud, db_session):
        """Test getting tasks by status."""
        # Create tasks with different statuses
        tasks_data = [
            {"tracker_id": "TEST-1", "key": "TEST-123", "status": "open"},
            {"tracker_id": "TEST-2", "key": "TEST-456", "status": "open"},
            {"tracker_id": "TEST-3", "key": "TEST-789", "status": "closed"}
        ]
        
        created_tasks = []
        for task_data in tasks_data:
            task = TrackerTask(**task_data)
            db_session.add(task)
            created_tasks.append(task)
        
        db_session.commit()
        
        # Get tasks by status
        open_tasks = db_session.query(TrackerTask).filter(TrackerTask.status == "open").all()
        closed_tasks = db_session.query(TrackerTask).filter(TrackerTask.status == "closed").all()
        
        # Verify results
        assert len(open_tasks) == 2
        assert len(closed_tasks) == 1
        assert open_tasks[0].status == "open"
        assert open_tasks[0].key == "TEST-123"
        assert closed_tasks[0].status == "closed"
        assert closed_tasks[0].key == "TEST-789"
        
        # Cleanup
        for task in created_tasks:
            db_session.delete(task)
        db_session.commit()

    def test_get_tasks_by_assignee(self, crud, db_session):
        """Test getting tasks by assignee."""
        # Create tasks with different assignees
        tasks_data = [
            {"tracker_id": "TEST-1", "key": "TEST-123", "assignee": "user1"},
            {"tracker_id": "TEST-2", "key": "TEST-456", "assignee": "user1"},
            {"tracker_id": "TEST-3", "key": "TEST-789", "assignee": "user2"}
        ]
        
        created_tasks = []
        for task_data in tasks_data:
            task = TrackerTask(**task_data)
            db_session.add(task)
            created_tasks.append(task)
        
        db_session.commit()
        
        # Get tasks by assignee
        user1_tasks = db_session.query(TrackerTask).filter(TrackerTask.assignee == "user1").all()
        user2_tasks = db_session.query(TrackerTask).filter(TrackerTask.assignee == "user2").all()
        
        # Verify results
        assert len(user1_tasks) == 2
        assert len(user2_tasks) == 1
        assert user1_tasks[0].assignee == "user1"
        assert user1_tasks[0].key == "TEST-123"
        assert user2_tasks[0].assignee == "user2"
        assert user2_tasks[0].key == "TEST-789"
        
        # Cleanup
        for task in created_tasks:
            db_session.delete(task)
        db_session.commit()

    def test_bulk_create_tasks(self, crud, db_session, sample_task_data):
        """Test bulk creation of tasks."""
        # Prepare bulk data
        tasks_data = [
            sample_task_data,
            {**sample_task_data, "tracker_id": "TEST-2", "key": "TEST-456"},
            {**sample_task_data, "tracker_id": "TEST-3", "key": "TEST-789"}
        ]
        
        # Create tasks using bulk create
        result = crud.bulk_create_or_update(db_session, tasks_data)
        
        # Verify results
        assert result["created"] == 3
        assert result["updated"] == 0
        
        # Verify tasks exist in database
        for task_data in tasks_data:
            retrieved_task = crud.get_by_tracker_id(db_session, task_data["tracker_id"])
            assert retrieved_task is not None
            assert retrieved_task.key == task_data["key"]
        
        # Cleanup
        for task_data in tasks_data:
            task = crud.get_by_tracker_id(db_session, task_data["tracker_id"])
            if task:
                db_session.delete(task)
        db_session.commit()

    def test_get_tasks_updated_since(self, crud, db_session):
        """Test getting tasks updated since a specific date."""
        # Create tasks with different update times
        from datetime import datetime, timedelta
        updated_since = datetime.now(timezone.utc) - timedelta(days=7)
        
        # Create old task
        old_task = TrackerTask(
            tracker_id="OLD-1", 
            key="OLD-123", 
            updated_at=datetime.now(timezone.utc) - timedelta(days=10)
        )
        db_session.add(old_task)
        
        # Create recent task
        recent_task = TrackerTask(
            tracker_id="RECENT-1", 
            key="RECENT-123", 
            updated_at=datetime.now(timezone.utc)
        )
        db_session.add(recent_task)
        
        db_session.commit()
        
        # Get tasks modified since
        recent_tasks = crud.get_tasks_modified_since(db_session, updated_since)
        
        # Verify results
        assert len(recent_tasks) == 1
        assert recent_tasks[0].tracker_id == "RECENT-1"
        assert recent_tasks[0].key == "RECENT-123"
        
        # Cleanup
        db_session.delete(old_task)
        db_session.delete(recent_task)
        db_session.commit()


class TestCRUDTrackerTaskHistory:
    """Test CRUD operations for TrackerTaskHistory."""

    @pytest.fixture
    def crud(self):
        """Create CRUD instance."""
        return CRUDTrackerTaskHistory(TrackerTaskHistory)

    @pytest.fixture
    def sample_history_data(self):
        """Sample history data for testing."""
        return {
            "task_id": 1,
            "tracker_id": "TEST-1",
            "status": "Open",
            "status_display": "Open",
            "start_date": datetime.now(timezone.utc)
        }

    def test_create_history_entry(self, crud, db_session, sample_history_data):
        """Test creating a history entry."""
        # Create history entry in database
        history = TrackerTaskHistory(**sample_history_data)
        db_session.add(history)
        db_session.commit()
        db_session.refresh(history)
        
        # Verify history was created
        assert history.id is not None
        assert history.tracker_id == "TEST-1"
        assert history.status == "Open"
        assert history.created_at is not None
        
        # Cleanup
        db_session.delete(history)
        db_session.commit()

    def test_get_history_for_task(self, crud, db_session):
        """Test getting history for a specific task."""
        # Create history entries
        history_data = [
            {"task_id": 1, "tracker_id": "TEST-1", "status": "Open", "status_display": "Open", "start_date": datetime.now(timezone.utc)},
            {"task_id": 1, "tracker_id": "TEST-1", "status": "In Progress", "status_display": "In Progress", "start_date": datetime.now(timezone.utc)}
        ]
        
        created_history = []
        for entry_data in history_data:
            history = TrackerTaskHistory(**entry_data)
            db_session.add(history)
            created_history.append(history)
        
        db_session.commit()
        
        # Get history by task ID
        task_history = crud.get_by_task_id(db_session, 1)
        
        # Verify results
        assert len(task_history) == 2
        assert all(entry.task_id == 1 for entry in task_history)
        assert task_history[0].status == "Open"
        assert task_history[1].status == "In Progress"
        
        # Cleanup
        for history in created_history:
            db_session.delete(history)
        db_session.commit()

    def test_get_status_changes(self, crud, db_session):
        """Test getting status changes for a task."""
        # Create history entries for status changes
        history_data = [
            {"task_id": 1, "tracker_id": "TEST-1", "status": "Open", "status_display": "Open", "start_date": datetime.now(timezone.utc)},
            {"task_id": 1, "tracker_id": "TEST-1", "status": "In Progress", "status_display": "In Progress", "start_date": datetime.now(timezone.utc)}
        ]
        
        created_history = []
        for entry_data in history_data:
            history = TrackerTaskHistory(**entry_data)
            db_session.add(history)
            created_history.append(history)
        
        db_session.commit()
        
        # Get history by tracker ID
        tracker_history = crud.get_by_tracker_id(db_session, "TEST-1")
        
        # Verify results
        assert len(tracker_history) == 2
        assert tracker_history[0].status == "Open"
        assert tracker_history[1].status == "In Progress"
        
        # Cleanup
        for history in created_history:
            db_session.delete(history)
        db_session.commit()

    def test_bulk_create_history(self, crud, db_session):
        """Test bulk creation of history entries."""
        # Prepare bulk data
        history_data = [
            {"task_id": 1, "tracker_id": "TEST-1", "status": "Open", "status_display": "Open", "start_date": datetime.now(timezone.utc)},
            {"task_id": 1, "tracker_id": "TEST-1", "status": "In Progress", "status_display": "In Progress", "start_date": datetime.now(timezone.utc)}
        ]
        
        # Create history entries using bulk create
        created_count = crud.bulk_create(db_session, history_data)
        
        # Verify results
        assert created_count == 2
        
        # Verify entries exist in database
        task_history = crud.get_by_task_id(db_session, 1)
        assert len(task_history) == 2
        
        # Cleanup
        for history in task_history:
            db_session.delete(history)
        db_session.commit()


class TestCRUDTrackerSyncLog:
    """Test CRUD operations for TrackerSyncLog."""

    @pytest.fixture
    def crud(self):
        """Create CRUD instance."""
        return CRUDTrackerSyncLog(TrackerSyncLog)

    @pytest.fixture
    def sample_sync_log_data(self):
        """Sample sync log data for testing."""
        return {
            "sync_started_at": datetime.now(timezone.utc),
            "status": "running",
            "tasks_processed": 0,
            "tasks_created": 0,
            "tasks_updated": 0
        }

    def test_create_sync_log(self, crud, db_session, sample_sync_log_data):
        """Test creating a sync log entry."""
        # Create sync log in database
        sync_log = TrackerSyncLog(**sample_sync_log_data)
        db_session.add(sync_log)
        db_session.commit()
        db_session.refresh(sync_log)
        
        # Verify sync log was created
        assert sync_log.id is not None
        assert sync_log.status == "running"
        assert sync_log.sync_started_at is not None
        
        # Cleanup
        db_session.delete(sync_log)
        db_session.commit()

    def test_get_latest_sync_log(self, crud, db_session):
        """Test getting the latest sync log."""
        # Create sync logs with different timestamps
        from datetime import datetime, timedelta
        
        old_log = TrackerSyncLog(
            sync_started_at=datetime.now(timezone.utc) - timedelta(hours=2),
            status="completed"
        )
        db_session.add(old_log)
        
        latest_log = TrackerSyncLog(
            sync_started_at=datetime.now(timezone.utc),
            status="running"
        )
        db_session.add(latest_log)
        
        db_session.commit()
        
        # Get latest sync log
        latest = db_session.query(TrackerSyncLog).order_by(TrackerSyncLog.sync_started_at.desc()).first()
        
        # Verify results
        assert latest is not None
        assert latest.status == "running"
        assert latest.sync_started_at > old_log.sync_started_at
        
        # Cleanup
        db_session.delete(old_log)
        db_session.delete(latest_log)
        db_session.commit()

    def test_get_sync_logs_by_status(self, crud, db_session):
        """Test getting sync logs by status."""
        # Create sync logs with different statuses
        sync_logs_data = [
            {"sync_started_at": datetime.now(timezone.utc), "status": "completed"},
            {"sync_started_at": datetime.now(timezone.utc), "status": "completed"},
            {"sync_started_at": datetime.now(timezone.utc), "status": "failed"}
        ]
        
        created_logs = []
        for log_data in sync_logs_data:
            sync_log = TrackerSyncLog(**log_data)
            db_session.add(sync_log)
            created_logs.append(sync_log)
        
        db_session.commit()
        
        # Get logs by status
        completed_logs = db_session.query(TrackerSyncLog).filter(TrackerSyncLog.status == "completed").all()
        failed_logs = db_session.query(TrackerSyncLog).filter(TrackerSyncLog.status == "failed").all()
        
        # Verify results
        assert len(completed_logs) == 2
        assert len(failed_logs) == 1
        assert completed_logs[0].status == "completed"
        assert failed_logs[0].status == "failed"
        
        # Cleanup
        for sync_log in created_logs:
            db_session.delete(sync_log)
        db_session.commit()

    def test_get_sync_statistics(self, crud, db_session):
        """Test getting sync statistics."""
        # Create sync logs with different statistics
        sync_logs_data = [
            {"sync_started_at": datetime.now(timezone.utc), "tasks_processed": 10, "tasks_created": 5, "tasks_updated": 3},
            {"sync_started_at": datetime.now(timezone.utc), "tasks_processed": 15, "tasks_created": 8, "tasks_updated": 4},
            {"sync_started_at": datetime.now(timezone.utc), "tasks_processed": 8, "tasks_created": 2, "tasks_updated": 1}
        ]
        
        created_logs = []
        for log_data in sync_logs_data:
            sync_log = TrackerSyncLog(**log_data)
            db_session.add(sync_log)
            created_logs.append(sync_log)
        
        db_session.commit()
        
        # Get all logs
        all_logs = db_session.query(TrackerSyncLog).all()
        
        # Verify results
        assert len(all_logs) == 3
        assert all_logs[0].tasks_processed == 10
        assert all_logs[1].tasks_created == 8
        assert all_logs[2].tasks_updated == 1
        
        # Cleanup
        for sync_log in created_logs:
            db_session.delete(sync_log)
        db_session.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
