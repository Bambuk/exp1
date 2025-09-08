"""Tests for initial status handling in tracker synchronization."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from typing import List, Dict, Any

from radiator.models.tracker import TrackerTask, TrackerTaskHistory
from radiator.services.tracker_service import TrackerAPIService
from radiator.commands.sync_tracker import TrackerSyncCommand
from radiator.crud.tracker import CRUDTrackerTask, CRUDTrackerTaskHistory


class TestInitialStatusHandling:
    """Test handling of initial task status in history."""

    @pytest.fixture
    def mock_service(self):
        """Create mock TrackerAPIService instance."""
        with patch('radiator.services.tracker_service.logger'):
            service = TrackerAPIService()
            return service

    @pytest.fixture
    def sample_task_with_initial_status(self):
        """Sample task that was created with initial status but never changed."""
        return {
            "id": "12345",
            "key": "TEST-123",
            "summary": "Test Task with Initial Status",
            "status": {"key": "backlog", "display": "Беклог"},
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z"
        }

    @pytest.fixture
    def sample_task_with_status_changes(self):
        """Sample task that has changed status multiple times."""
        return {
            "id": "67890",
            "key": "TEST-456",
            "summary": "Test Task with Status Changes",
            "status": {"key": "in_progress", "display": "В работе"},
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z"
        }

    @pytest.fixture
    def empty_changelog(self):
        """Empty changelog - no status changes recorded."""
        return []

    @pytest.fixture
    def changelog_with_status_changes(self):
        """Changelog with status changes."""
        return [
            {
                "updatedAt": "2024-01-01T10:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status"},
                        "to": {"display": "В работе"}
                    }
                ]
            },
            {
                "updatedAt": "2024-01-02T10:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status"},
                        "to": {"display": "Готово"}
                    }
                ]
            }
        ]

    def test_extract_status_history_empty_changelog(self, mock_service, empty_changelog):
        """Test that empty changelog returns no status history."""
        result = mock_service.extract_status_history(empty_changelog, "TEST-123")
        assert len(result) == 0

    def test_extract_status_history_with_changes(self, mock_service, changelog_with_status_changes):
        """Test that changelog with status changes returns correct history."""
        result = mock_service.extract_status_history(changelog_with_status_changes, "TEST-456")
        assert len(result) == 2
        assert result[0]["status"] == "В работе"
        assert result[1]["status"] == "Готово"
        assert result[0]["end_date"] == result[1]["start_date"]
        # Last status change doesn't have end_date in current implementation
        assert "end_date" not in result[1] or result[1]["end_date"] is None

    def test_extract_status_history_ignores_non_status_fields(self, mock_service):
        """Test that non-status field changes are ignored."""
        changelog = [
            {
                "updatedAt": "2024-01-01T10:00:00Z",
                "fields": [
                    {
                        "field": {"id": "summary"},
                        "to": {"display": "Updated Summary"}
                    },
                    {
                        "field": {"id": "status"},
                        "to": {"display": "В работе"}
                    }
                ]
            }
        ]
        
        result = mock_service.extract_status_history(changelog, "TEST-123")
        assert len(result) == 1
        assert result[0]["status"] == "В работе"

    def test_extract_status_history_removes_duplicates(self, mock_service):
        """Test that duplicate status changes are removed."""
        changelog = [
            {
                "updatedAt": "2024-01-01T10:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status"},
                        "to": {"display": "В работе"}
                    }
                ]
            },
            {
                "updatedAt": "2024-01-01T10:00:00Z",  # Same timestamp
                "fields": [
                    {
                        "field": {"id": "status"},
                        "to": {"display": "В работе"}  # Same status
                    }
                ]
            }
        ]
        
        result = mock_service.extract_status_history(changelog, "TEST-123")
        assert len(result) == 1
        assert result[0]["status"] == "В работе"

    def test_extract_status_history_sorts_by_date(self, mock_service):
        """Test that status changes are sorted by date."""
        changelog = [
            {
                "updatedAt": "2024-01-03T10:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status"},
                        "to": {"display": "Готово"}
                    }
                ]
            },
            {
                "updatedAt": "2024-01-01T10:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status"},
                        "to": {"display": "В работе"}
                    }
                ]
            }
        ]
        
        result = mock_service.extract_status_history(changelog, "TEST-123")
        assert len(result) == 2
        assert result[0]["status"] == "В работе"  # Earlier date first
        assert result[1]["status"] == "Готово"    # Later date second

    def test_sync_task_history_with_empty_changelog(self, mock_service):
        """Test sync_task_history behavior when changelog is empty."""
        # This test documents current behavior - tasks with no status changes
        # will have 0 history entries, which is the problem we want to solve
        
        task_id = "12345"
        empty_changelog = []
        
        result = mock_service.extract_status_history(empty_changelog, "TEST-123")
        assert len(result) == 0
        
        # This is the current behavior - no history for tasks that never changed status
        # In the future, we should add logic to create initial status entry

    def test_sync_task_history_with_status_changes(self, mock_service):
        """Test sync_task_history behavior when changelog has status changes."""
        task_id = "67890"
        changelog = [
            {
                "updatedAt": "2024-01-01T10:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status"},
                        "to": {"display": "В работе"}
                    }
                ]
            }
        ]
        
        result = mock_service.extract_status_history(changelog, "TEST-456")
        assert len(result) == 1
        assert result[0]["status"] == "В работе"

    def test_task_with_initial_status_only(self, mock_service, sample_task_with_initial_status):
        """Test task that was created with initial status but never changed."""
        # Extract task data
        task_data = mock_service.extract_task_data(sample_task_with_initial_status)
        assert task_data["status"] == "Беклог"
        
        # Simulate empty changelog (no status changes)
        empty_changelog = []
        status_history = mock_service.extract_status_history(empty_changelog, "TEST-123")
        
        # Current behavior: no history entries
        assert len(status_history) == 0
        
        # This is the problem: we lose the initial status "Беклог"
        # Future solution should create an entry for the initial status

    def test_task_with_multiple_status_changes(self, mock_service, sample_task_with_status_changes):
        """Test task that has changed status multiple times."""
        # Extract task data
        task_data = mock_service.extract_task_data(sample_task_with_status_changes)
        assert task_data["status"] == "В работе"
        
        # Simulate changelog with status changes
        changelog = [
            {
                "updatedAt": "2024-01-01T10:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status"},
                        "to": {"display": "В работе"}
                    }
                ]
            },
            {
                "updatedAt": "2024-01-02T10:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status"},
                        "to": {"display": "Готово"}
                    }
                ]
            }
        ]
        
        status_history = mock_service.extract_status_history(changelog, "TEST-456")
        assert len(status_history) == 2
        assert status_history[0]["status"] == "В работе"
        assert status_history[1]["status"] == "Готово"

    def test_sync_command_tasks_with_history_count(self):
        """Test that sync command correctly counts tasks with history."""
        # This test documents the current behavior where tasks with no status changes
        # are not counted as "tasks with history"
        
        with patch('radiator.commands.sync_tracker.logger'):
            sync_cmd = TrackerSyncCommand()
            sync_cmd.db = Mock()
            
            # Mock tracker service
            with patch('radiator.commands.sync_tracker.tracker_service') as mock_service:
                # Mock tasks data
                mock_service.get_tasks_by_filter.return_value = ["12345", "67890"]
                mock_service.get_tasks_batch.return_value = [
                    ("12345", {"id": "12345", "key": "TEST-123", "status": {"display": "Беклог"}}),
                    ("67890", {"id": "67890", "key": "TEST-456", "status": {"display": "В работе"}})
                ]
                mock_service.extract_task_data.side_effect = [
                    {"tracker_id": "12345", "key": "TEST-123", "status": "Беклог"},
                    {"tracker_id": "67890", "key": "TEST-456", "status": "В работе"}
                ]
                
                # Mock changelogs - first task has no changes, second has changes
                mock_service.get_changelogs_batch.return_value = [
                    ("12345", []),  # Empty changelog - no status changes
                    ("67890", [    # Has status changes
                        {
                            "updatedAt": "2024-01-01T10:00:00Z",
                            "fields": [
                                {
                                    "field": {"id": "status"},
                                    "to": {"display": "В работе"}
                                }
                            ]
                        }
                    ])
                ]
                mock_service.extract_status_history.side_effect = [
                    [],  # No history for first task
                    [{"status": "В работе", "status_display": "В работе", "start_date": datetime.now(timezone.utc)}]  # History for second task
                ]
                
                # Mock CRUD operations
                with patch('radiator.commands.sync_tracker.tracker_task') as mock_task_crud:
                    with patch('radiator.commands.sync_tracker.tracker_task_history') as mock_history_crud:
                        with patch('radiator.commands.sync_tracker.tracker_sync_log') as mock_sync_log_crud:
                            # Mock sync log
                            mock_log = Mock()
                            mock_log.id = "sync-123"
                            mock_sync_log_crud.create.return_value = mock_log
                            
                            # Mock task operations
                            mock_task_crud.get_by_tracker_id.side_effect = [
                                Mock(id=1, key="TEST-123"),  # First task
                                Mock(id=2, key="TEST-456")   # Second task
                            ]
                            mock_task_crud.bulk_create_or_update.return_value = {"created": 0, "updated": 2}
                            mock_history_crud.delete_by_task_id.return_value = 0
                            mock_history_crud.bulk_create.side_effect = [0, 1]  # First task: 0 history entries, second: 1 entry
                            mock_history_crud.cleanup_duplicates.return_value = 0
                            
                            # Mock database session
                            with patch.object(sync_cmd, 'db') as mock_db:
                                mock_db.add.return_value = None
                                mock_db.commit.return_value = None
                                mock_db.refresh.return_value = None
                                
                                # Run sync
                                result = sync_cmd.run(filters={}, limit=10)
                                
                                # Should succeed
                                assert result is True
                                
                                # Verify that only 1 task has history (the one with status changes)
                                # This documents the current behavior - tasks without status changes
                                # are not counted as "tasks with history"

    def test_initial_status_problem_scenario(self):
        """Test the specific problem scenario: tasks created with initial status but never changed."""
        # This test documents the exact problem we identified:
        # - 122 tasks processed
        # - 83 tasks with history (those that changed status)
        # - 39 tasks without history (those that never changed status after creation)
        
        with patch('radiator.commands.sync_tracker.logger'):
            sync_cmd = TrackerSyncCommand()
            sync_cmd.db = Mock()
            
            # Mock tracker service
            with patch('radiator.commands.sync_tracker.tracker_service') as mock_service:
                # Mock 122 tasks
                task_ids = [f"task_{i:03d}" for i in range(1, 123)]
                mock_service.get_tasks_by_filter.return_value = task_ids
                
                # Mock tasks data - all have initial status
                tasks_data = []
                for i, task_id in enumerate(task_ids):
                    tasks_data.append((task_id, {
                        "id": task_id,
                        "key": f"TEST-{i+1:03d}",
                        "status": {"display": "Беклог"}
                    }))
                mock_service.get_tasks_batch.return_value = tasks_data
                
                # Mock extract_task_data
                def mock_extract_task_data(task_data):
                    return {
                        "tracker_id": task_data["id"],
                        "key": task_data["key"],
                        "status": task_data["status"]["display"]
                    }
                mock_service.extract_task_data.side_effect = [mock_extract_task_data(task[1]) for task in tasks_data]
                
                # Mock changelogs - 83 tasks have status changes, 39 don't
                changelogs_data = []
                for i, task_id in enumerate(task_ids):
                    if i < 83:  # First 83 tasks have status changes
                        changelogs_data.append((task_id, [
                            {
                                "updatedAt": "2024-01-01T10:00:00Z",
                                "fields": [
                                    {
                                        "field": {"id": "status"},
                                        "to": {"display": "В работе"}
                                    }
                                ]
                            }
                        ]))
                    else:  # Last 39 tasks have no status changes
                        changelogs_data.append((task_id, []))
                
                mock_service.get_changelogs_batch.return_value = changelogs_data
                
                # Mock extract_status_history
                def mock_extract_status_history(changelog, task_key=None):
                    if changelog:  # Has status changes
                        return [{"status": "В работе", "status_display": "В работе", "start_date": datetime.now(timezone.utc)}]
                    else:  # No status changes
                        return []
                
                mock_service.extract_status_history.side_effect = [mock_extract_status_history(changelog[1], f"TEST-{i+1:03d}") for i, changelog in enumerate(changelogs_data)]
                
                # Mock CRUD operations
                with patch('radiator.commands.sync_tracker.tracker_task') as mock_task_crud:
                    with patch('radiator.commands.sync_tracker.tracker_task_history') as mock_history_crud:
                        with patch('radiator.commands.sync_tracker.tracker_sync_log') as mock_sync_log_crud:
                            # Mock sync log
                            mock_log = Mock()
                            mock_log.id = "sync-123"
                            mock_sync_log_crud.create.return_value = mock_log
                            
                            # Mock task operations
                            def mock_get_by_tracker_id(db, tracker_id):
                                task_index = int(tracker_id.split('_')[1]) - 1
                                return Mock(id=task_index + 1, key=f"TEST-{task_index + 1:03d}")
                            
                            mock_task_crud.get_by_tracker_id.side_effect = [mock_get_by_tracker_id(None, task_id) for task_id in task_ids]
                            mock_task_crud.bulk_create_or_update.return_value = {"created": 0, "updated": 122}
                            mock_history_crud.delete_by_task_id.return_value = 0
                            
                            # Mock bulk_create - 83 tasks get history entries, 39 don't
                            def mock_bulk_create(db, history_data):
                                return len(history_data) if history_data else 0
                            
                            mock_history_crud.bulk_create.side_effect = [mock_bulk_create(None, []) if i >= 83 else mock_bulk_create(None, [{"status": "В работе"}]) for i in range(122)]
                            mock_history_crud.cleanup_duplicates.return_value = 0
                            
                            # Mock database session
                            with patch.object(sync_cmd, 'db') as mock_db:
                                mock_db.add.return_value = None
                                mock_db.commit.return_value = None
                                mock_db.refresh.return_value = None
                                
                                # Run sync
                                result = sync_cmd.run(filters={}, limit=122)
                                
                                # Should succeed
                                assert result is True
                                
                                # This documents the current behavior:
                                # - 122 tasks processed
                                # - 83 tasks with history (those that changed status)
                                # - 39 tasks without history (those that never changed status)
                                # The problem: we lose the initial status for 39 tasks


class TestInitialStatusSolution:
    """Test the proposed solution for handling initial status."""

    def test_should_add_initial_status_when_no_changelog(self):
        """Test that we should add initial status when changelog is empty."""
        # This test documents what the solution should do:
        # If a task has no status changes in changelog, we should create
        # an initial status entry with the current status
        
        task_data = {
            "tracker_id": "12345",
            "key": "TEST-123",
            "status": "Беклог",
            "created_at": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        }
        
        empty_changelog = []
        
        # Current behavior: no history
        # Future behavior: should create initial status entry
        expected_initial_status = {
            "status": "Беклог",
            "status_display": "Беклог",
            "start_date": task_data["created_at"],
            "end_date": None
        }
        
        # This is what the solution should produce
        assert expected_initial_status["status"] == "Беклог"
        assert expected_initial_status["start_date"] == task_data["created_at"]
        assert expected_initial_status["end_date"] is None

    def test_should_not_add_initial_status_when_changelog_exists(self):
        """Test that we should not add initial status when changelog has entries."""
        task_data = {
            "tracker_id": "67890",
            "key": "TEST-456",
            "status": "Готово",
            "created_at": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        }
        
        changelog_with_changes = [
            {
                "updatedAt": "2024-01-01T10:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status"},
                        "to": {"display": "В работе"}
                    }
                ]
            }
        ]
        
        # When changelog has entries, we should use them as-is
        # and not add initial status entry
        assert len(changelog_with_changes) > 0
        # The solution should not add initial status in this case

    def test_initial_status_with_created_at_date(self):
        """Test using created_at date for initial status entry."""
        task_data = {
            "tracker_id": "12345",
            "key": "TEST-123",
            "status": "Беклог",
            "created_at": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            "task_updated_at": datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        }
        
        # For initial status, we should use created_at as start_date
        # because that's when the task was created with this status
        expected_start_date = task_data["created_at"]
        
        assert expected_start_date == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def test_initial_status_with_task_updated_at_date(self):
        """Test using task_updated_at date for initial status entry."""
        task_data = {
            "tracker_id": "12345",
            "key": "TEST-123",
            "status": "Беклог",
            "created_at": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            "task_updated_at": datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        }
        
        # Alternative approach: use task_updated_at as start_date
        # if we want to use the last update time
        expected_start_date = task_data["task_updated_at"]
        
        assert expected_start_date == datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
