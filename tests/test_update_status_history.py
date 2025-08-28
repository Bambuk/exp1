"""Tests for UpdateStatusHistoryCommand."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from radiator.commands.update_status_history import UpdateStatusHistoryCommand
from radiator.models.tracker import TrackerTask, TrackerTaskHistory, TrackerSyncLog


class TestUpdateStatusHistoryCommand:
    """Test cases for UpdateStatusHistoryCommand."""

    def test_init(self):
        """Test command initialization."""
        cmd = UpdateStatusHistoryCommand()
        assert cmd.db is not None
        assert cmd.sync_log is None

    def test_context_manager(self):
        """Test context manager functionality."""
        with UpdateStatusHistoryCommand() as cmd:
            assert cmd.db is not None
        # db should be closed after context exit

    def test_create_sync_log(self):
        """Test sync log creation."""
        cmd = UpdateStatusHistoryCommand()
        
        with patch.object(cmd.db, 'add') as mock_add, \
             patch.object(cmd.db, 'commit') as mock_commit, \
             patch.object(cmd.db, 'refresh') as mock_refresh:
            
            mock_log = Mock()
            mock_log.id = "sync-123"
            with patch('radiator.commands.update_status_history.TrackerSyncLog', return_value=mock_log):
                result = cmd.create_sync_log()
                
                assert result == mock_log
                mock_add.assert_called_once_with(mock_log)
                mock_commit.assert_called_once()
                mock_refresh.assert_called_once_with(mock_log)

    def test_update_sync_log(self):
        """Test sync log update."""
        cmd = UpdateStatusHistoryCommand()
        cmd.sync_log = Mock()
        
        with patch.object(cmd.db, 'commit') as mock_commit:
            cmd.update_sync_log(status="completed", tasks_processed=5)
            
            assert cmd.sync_log.status == "completed"
            assert cmd.sync_log.tasks_processed == 5
            mock_commit.assert_called_once()

    def test_get_tasks_with_recent_status_changes_success(self):
        """Test successful task retrieval."""
        cmd = UpdateStatusHistoryCommand()
        
        with patch('radiator.commands.update_status_history.tracker_service') as mock_service:
            mock_service.search_tasks.return_value = ["TEST-1", "TEST-2", "TEST-3"]
            
            result = cmd.get_tasks_with_recent_status_changes("CPO", 14)
            
            assert result == ["TEST-1", "TEST-2", "TEST-3"]
            mock_service.search_tasks.assert_called_once_with(
                query='Queue: CPO "Last status change": today()-14d..today() "Sort by": Updated DESC',
                limit=1000
            )

    def test_get_tasks_with_recent_status_changes_failure(self):
        """Test task retrieval failure."""
        cmd = UpdateStatusHistoryCommand()
        
        with patch('radiator.commands.update_status_history.tracker_service') as mock_service:
            mock_service.search_tasks.side_effect = Exception("API Error")
            
            result = cmd.get_tasks_with_recent_status_changes("CPO", 14)
            
            assert result == []

    def test_update_status_history_for_tasks_success(self):
        """Test successful status history update."""
        cmd = UpdateStatusHistoryCommand()
        
        # Mock task data
        mock_task = Mock()
        mock_task.id = 1
        
        # Mock changelog data
        mock_changelog = [
            {
                "updatedAt": "2024-01-15T10:30:00Z",
                "fields": [
                    {
                        "field": {"id": "status"},
                        "to": {"key": "open", "display": "Открыт"}
                    }
                ]
            }
        ]
        
        # Mock status history
        mock_status_history = [
            {
                "status": "open",
                "status_display": "Открыт",
                "start_date": datetime.now(timezone.utc),
                "end_date": None
            }
        ]
        
        with patch('radiator.commands.update_status_history.tracker_task') as mock_task_crud, \
             patch('radiator.commands.update_status_history.tracker_service') as mock_service, \
             patch('radiator.commands.update_status_history.tracker_task_history') as mock_history_crud:
            
            # Mock CRUD operations
            mock_task_crud.get_by_tracker_id.return_value = mock_task
            mock_service.get_task_changelog.return_value = mock_changelog
            mock_service.extract_status_history.return_value = mock_status_history
            mock_history_crud.delete_by_task_id.return_value = 2
            mock_history_crud.bulk_create.return_value = 1
            
            # Mock database operations
            with patch.object(cmd.db, 'commit') as mock_commit:
                result = cmd.update_status_history_for_tasks(["TEST-1"])
                
                assert result["created"] == 1
                assert result["updated"] == 0
                mock_commit.assert_called()

    def test_update_status_history_for_tasks_task_not_found(self):
        """Test status history update when task not found."""
        cmd = UpdateStatusHistoryCommand()
        
        with patch('radiator.commands.update_status_history.tracker_task') as mock_task_crud:
            mock_task_crud.get_by_tracker_id.return_value = None
            
            result = cmd.update_status_history_for_tasks(["TEST-1"])
            
            assert result["created"] == 0
            assert result["updated"] == 0

    def test_update_status_history_for_tasks_no_changelog(self):
        """Test status history update when no changelog exists."""
        cmd = UpdateStatusHistoryCommand()
        
        mock_task = Mock()
        mock_task.id = 1
        
        with patch('radiator.commands.update_status_history.tracker_task') as mock_task_crud, \
             patch('radiator.commands.update_status_history.tracker_service') as mock_service:
            
            mock_task_crud.get_by_tracker_id.return_value = mock_task
            mock_service.get_task_changelog.return_value = []
            
            result = cmd.update_status_history_for_tasks(["TEST-1"])
            
            assert result["created"] == 0
            assert result["updated"] == 0

    def test_update_status_history_for_tasks_no_status_changes(self):
        """Test status history update when no status changes exist."""
        cmd = UpdateStatusHistoryCommand()
        
        mock_task = Mock()
        mock_task.id = 1
        
        with patch('radiator.commands.update_status_history.tracker_task') as mock_task_crud, \
             patch('radiator.commands.update_status_history.tracker_service') as mock_service:
            
            mock_task_crud.get_by_tracker_id.return_value = mock_task
            mock_service.get_task_changelog.return_value = [{"updatedAt": "2024-01-15T10:30:00Z", "fields": []}]
            mock_service.extract_status_history.return_value = []
            
            result = cmd.update_status_history_for_tasks(["TEST-1"])
            
            assert result["created"] == 0
            assert result["updated"] == 0

    def test_run_success(self):
        """Test successful command execution."""
        cmd = UpdateStatusHistoryCommand()
        
        with patch.object(cmd, 'create_sync_log') as mock_create_log, \
             patch.object(cmd, 'get_tasks_with_recent_status_changes') as mock_get_tasks, \
             patch.object(cmd, 'update_status_history_for_tasks') as mock_update_history, \
             patch.object(cmd, 'update_sync_log') as mock_update_log:
            
            # Mock sync log
            mock_log = Mock()
            mock_log.id = "sync-123"
            mock_create_log.return_value = mock_log
            
            # Mock task retrieval
            mock_get_tasks.return_value = ["TEST-1", "TEST-2"]
            
            # Mock history update
            mock_update_history.return_value = {"created": 5, "updated": 0}
            
            result = cmd.run("CPO", 14, 100)
            
            assert result is True
            mock_create_log.assert_called_once()
            mock_get_tasks.assert_called_once_with("CPO", 14)
            mock_update_history.assert_called_once_with(["TEST-1", "TEST-2"])
            mock_update_log.assert_called()

    def test_run_no_tasks_found(self):
        """Test command execution when no tasks found."""
        cmd = UpdateStatusHistoryCommand()
        
        with patch.object(cmd, 'create_sync_log') as mock_create_log, \
             patch.object(cmd, 'get_tasks_with_recent_status_changes') as mock_get_tasks, \
             patch.object(cmd, 'update_sync_log') as mock_update_log:
            
            # Mock sync log
            mock_log = Mock()
            mock_log.id = "sync-123"
            mock_create_log.return_value = mock_log
            
            # Mock empty task list
            mock_get_tasks.return_value = []
            
            result = cmd.run("CPO", 14, 100)
            
            assert result is True
            mock_update_log.assert_called()

    def test_run_with_limit(self):
        """Test command execution with task limit."""
        cmd = UpdateStatusHistoryCommand()
        
        with patch.object(cmd, 'create_sync_log') as mock_create_log, \
             patch.object(cmd, 'get_tasks_with_recent_status_changes') as mock_get_tasks, \
             patch.object(cmd, 'update_status_history_for_tasks') as mock_update_history, \
             patch.object(cmd, 'update_sync_log') as mock_update_log:
            
            # Mock sync log
            mock_log = Mock()
            mock_log.id = "sync-123"
            mock_create_log.return_value = mock_log
            
            # Mock many tasks
            mock_get_tasks.return_value = [f"TEST-{i}" for i in range(100)]
            
            # Mock history update
            mock_update_history.return_value = {"created": 50, "updated": 0}
            
            result = cmd.run("CPO", 14, 50)  # Limit to 50 tasks
            
            assert result is True
            # Should call update_history with limited task list
            mock_update_history.assert_called_once_with([f"TEST-{i}" for i in range(50)])

    def test_run_failure(self):
        """Test command execution failure."""
        cmd = UpdateStatusHistoryCommand()
        
        with patch.object(cmd, 'create_sync_log') as mock_create_log, \
             patch.object(cmd, 'get_tasks_with_recent_status_changes') as mock_get_tasks, \
             patch.object(cmd, 'update_sync_log') as mock_update_log:
            
            # Mock sync log
            mock_log = Mock()
            mock_log.id = "sync-123"
            mock_create_log.return_value = mock_log
            
            # Mock failure
            mock_get_tasks.side_effect = Exception("Critical error")
            
            result = cmd.run("CPO", 14, 100)
            
            assert result is False
            mock_update_log.assert_called()


class TestUpdateStatusHistoryIntegration:
    """Integration tests for UpdateStatusHistoryCommand."""

    @pytest.fixture
    def mock_environment(self):
        """Mock environment variables."""
        with patch.dict('os.environ', {
            'TRACKER_API_TOKEN': 'test_token',
            'TRACKER_ORG_ID': 'test_org',
            'DATABASE_URL_SYNC': 'postgresql://test:test@localhost:5432/testdb'
        }):
            yield

    def test_complete_status_history_update_flow(self, mock_environment):
        """Test complete status history update flow."""
        
        # Mock tracker service
        with patch('radiator.commands.update_status_history.tracker_service') as mock_service:
            mock_service.search_tasks.return_value = ["TEST-1", "TEST-2"]
            mock_service.get_task_changelog.return_value = [
                {
                    "updatedAt": "2024-01-15T10:30:00Z",
                    "fields": [
                        {
                            "field": {"id": "status"},
                            "to": {"key": "open", "display": "Открыт"}
                        }
                    ]
                }
            ]
            mock_service.extract_status_history.return_value = [
                {
                    "status": "open",
                    "status_display": "Открыт",
                    "start_date": datetime.now(timezone.utc),
                    "end_date": None
                }
            ]
            
            # Create command
            with patch('radiator.commands.update_status_history.logger'):
                cmd = UpdateStatusHistoryCommand()
                
                # Mock CRUD operations
                with patch('radiator.commands.update_status_history.tracker_task') as mock_task_crud:
                    with patch('radiator.commands.update_status_history.tracker_task_history') as mock_history_crud:
                        # Mock task operations
                        mock_task = Mock()
                        mock_task.id = 1
                        mock_task_crud.get_by_tracker_id.return_value = mock_task
                        mock_history_crud.delete_by_task_id.return_value = 1
                        mock_history_crud.bulk_create.return_value = 1
                        
                        # Mock database session
                        with patch.object(cmd, 'db') as mock_db:
                            mock_db.add.return_value = None
                            mock_db.commit.return_value = None
                            mock_db.refresh.return_value = None
                            
                            # Run command
                            result = cmd.run("CPO", 14, 100)
                            
                            assert result is True
                            mock_service.search_tasks.assert_called_once()
                            mock_service.get_task_changelog.assert_called()
                            mock_service.extract_status_history.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
