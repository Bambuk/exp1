"""TDD tests for initial status handling - these tests should FAIL until implementation."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from typing import List, Dict, Any

from radiator.services.tracker_service import TrackerAPIService
from radiator.commands.sync_tracker import TrackerSyncCommand


class TestInitialStatusTDD:
    """TDD tests that should FAIL until we implement initial status handling."""

    @pytest.fixture
    def mock_service(self):
        """Create mock TrackerAPIService instance."""
        with patch('radiator.services.tracker_service.logger'):
            service = TrackerAPIService()
            return service

    def test_extract_status_history_should_add_initial_status_when_empty_changelog(self, mock_service):
        """🔴 RED: This test should FAIL - we need to add initial status when changelog is empty."""
        # Given: Task with initial status but no changelog entries
        task_data = {
            "tracker_id": "12345",
            "key": "TEST-123",
            "status": "Беклог",
            "created_at": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        }
        empty_changelog = []
        
        # When: We extract status history
        # This method doesn't exist yet - it should FAIL
        result = mock_service.extract_status_history_with_initial_status(
            empty_changelog, task_data, "TEST-123"
        )
        
        # Then: We should get one entry with initial status
        assert len(result) == 1, "Should have 1 status entry (initial status)"
        assert result[0]["status"] == "Беклог", "Should preserve initial status"
        assert result[0]["status_display"] == "Беклог", "Should set status_display"
        assert result[0]["start_date"] == task_data["created_at"], "Should use created_at as start_date"
        assert result[0]["end_date"] is None, "Initial status should have no end_date"

    def test_extract_status_history_should_not_add_initial_status_when_changelog_exists(self, mock_service):
        """🔴 RED: This test should FAIL - we should not add initial status when changelog has entries."""
        # Given: Task with changelog entries
        task_data = {
            "tracker_id": "67890",
            "key": "TEST-456",
            "status": "Готово",
            "created_at": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        }
        changelog_with_entries = [
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
        
        # When: We extract status history
        result = mock_service.extract_status_history_with_initial_status(
            changelog_with_entries, task_data, "TEST-456"
        )
        
        # Then: We should get only changelog entries, no initial status
        assert len(result) == 1, "Should have 1 status entry from changelog"
        assert result[0]["status"] == "В работе", "Should use status from changelog"
        assert result[0]["status_display"] == "В работе", "Should set status_display from changelog"

    def test_extract_status_history_should_use_task_updated_at_when_created_at_unavailable(self, mock_service):
        """🔴 RED: This test should FAIL - we should use task_updated_at when created_at is not available."""
        # Given: Task without created_at but with task_updated_at
        task_data = {
            "tracker_id": "99999",
            "key": "TEST-999",
            "status": "Открыто",
            "task_updated_at": datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
            # No created_at field
        }
        empty_changelog = []
        
        # When: We extract status history
        result = mock_service.extract_status_history_with_initial_status(
            empty_changelog, task_data, "TEST-999"
        )
        
        # Then: We should use task_updated_at as start_date
        assert len(result) == 1, "Should have 1 status entry (initial status)"
        assert result[0]["start_date"] == task_data["task_updated_at"], "Should use task_updated_at when created_at unavailable"

    def test_extract_status_history_should_prioritize_created_at_over_task_updated_at(self, mock_service):
        """🔴 RED: This test should FAIL - we should prioritize created_at over task_updated_at."""
        # Given: Task with both created_at and task_updated_at
        task_data = {
            "tracker_id": "88888",
            "key": "TEST-888",
            "status": "Новое",
            "created_at": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            "task_updated_at": datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        }
        empty_changelog = []
        
        # When: We extract status history
        result = mock_service.extract_status_history_with_initial_status(
            empty_changelog, task_data, "TEST-888"
        )
        
        # Then: We should use created_at as start_date
        assert len(result) == 1, "Should have 1 status entry (initial status)"
        assert result[0]["start_date"] == task_data["created_at"], "Should prioritize created_at over task_updated_at"

    def test_sync_task_history_should_count_tasks_with_initial_status(self):
        """🔴 RED: This test should FAIL - sync should count tasks with initial status as having history."""
        # Given: Tasks with and without status changes
        with patch('radiator.commands.sync_tracker.logger'):
            sync_cmd = TrackerSyncCommand()
            sync_cmd.db = Mock()
            
            # Mock tracker service
            with patch('radiator.commands.sync_tracker.tracker_service') as mock_service:
                # Mock 3 tasks: 1 with changes, 2 without changes
                task_ids = ["task1", "task2", "task3"]
                mock_service.get_tasks_by_filter.return_value = task_ids
                
                # Mock tasks data
                tasks_data = [
                    ("task1", {"id": "task1", "key": "TEST-1", "status": {"display": "Беклог"}}),
                    ("task2", {"id": "task2", "key": "TEST-2", "status": {"display": "Открыто"}}),
                    ("task3", {"id": "task3", "key": "TEST-3", "status": {"display": "Новое"}})
                ]
                mock_service.get_tasks_batch.return_value = tasks_data
                
                # Mock extract_task_data
                def mock_extract_task_data(task_data):
                    return {
                        "tracker_id": task_data["id"],
                        "key": task_data["key"],
                        "status": task_data["status"]["display"],
                        "created_at": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
                    }
                mock_service.extract_task_data.side_effect = [mock_extract_task_data(task[1]) for task in tasks_data]
                
                # Mock changelogs: task1 has changes, task2 and task3 don't
                changelogs_data = [
                    ("task1", [{"updatedAt": "2024-01-01T10:00:00Z", "fields": [{"field": {"id": "status"}, "to": {"display": "В работе"}}]}]),
                    ("task2", []),  # No changes
                    ("task3", [])   # No changes
                ]
                mock_service.get_changelogs_batch.return_value = changelogs_data
                
                # Mock extract_status_history_with_initial_status
                def mock_extract_status_history_with_initial_status(changelog, task_data, task_key):
                    if changelog:  # Has changes
                        return [{"status": "В работе", "status_display": "В работе", "start_date": datetime.now(timezone.utc)}]
                    else:  # No changes - should add initial status
                        return [{"status": task_data["status"], "status_display": task_data["status"], "start_date": task_data["created_at"]}]
                
                mock_service.extract_status_history_with_initial_status.side_effect = [
                    mock_extract_status_history_with_initial_status(changelog[1], mock_extract_task_data(tasks_data[i][1]), f"TEST-{i+1}")
                    for i, changelog in enumerate(changelogs_data)
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
                            def mock_get_by_tracker_id(db, tracker_id):
                                task_index = int(tracker_id.replace("task", "")) - 1
                                return Mock(id=task_index + 1, key=f"TEST-{task_index + 1}")
                            
                            mock_task_crud.get_by_tracker_id.side_effect = [mock_get_by_tracker_id(None, task_id) for task_id in task_ids]
                            mock_task_crud.bulk_create_or_update.return_value = {"created": 0, "updated": 3}
                            mock_history_crud.delete_by_task_id.return_value = 0
                            mock_history_crud.bulk_create.side_effect = [1, 1, 1]  # All 3 tasks should have history
                            mock_history_crud.cleanup_duplicates.return_value = 0
                            
                            # Mock database session
                            with patch.object(sync_cmd, 'db') as mock_db:
                                mock_db.add.return_value = None
                                mock_db.commit.return_value = None
                                mock_db.refresh.return_value = None
                                
                                # When: We run sync
                                result = sync_cmd.run(filters={}, limit=3)
                                
                                # Then: All tasks should be counted as having history
                                assert result is True, "Sync should succeed"
                                # This assertion should FAIL until we implement the fix
                                # Currently: 1 task with history, 2 without
                                # After fix: 3 tasks with history (all should have initial status)

    def test_sync_task_history_should_return_correct_counts(self):
        """🔴 RED: This test should FAIL - sync should return correct counts including initial status."""
        # Given: Tasks with mixed status history
        with patch('radiator.commands.sync_tracker.logger'):
            sync_cmd = TrackerSyncCommand()
            sync_cmd.db = Mock()
            
            # Mock tracker service
            with patch('radiator.commands.sync_tracker.tracker_service') as mock_service:
                # Mock 5 tasks: 2 with changes, 3 without changes
                task_ids = [f"task{i}" for i in range(1, 6)]
                mock_service.get_tasks_by_filter.return_value = task_ids
                
                # Mock tasks data
                tasks_data = [(task_id, {"id": task_id, "key": f"TEST-{i}", "status": {"display": "Беклог"}}) for i, task_id in enumerate(task_ids, 1)]
                mock_service.get_tasks_batch.return_value = tasks_data
                
                # Mock extract_task_data
                def mock_extract_task_data(task_data):
                    return {
                        "tracker_id": task_data["id"],
                        "key": task_data["key"],
                        "status": task_data["status"]["display"],
                        "created_at": datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
                    }
                mock_service.extract_task_data.side_effect = [mock_extract_task_data(task[1]) for task in tasks_data]
                
                # Mock changelogs: first 2 tasks have changes, last 3 don't
                changelogs_data = []
                for i, task_id in enumerate(task_ids):
                    if i < 2:  # First 2 tasks have changes
                        changelogs_data.append((task_id, [{"updatedAt": "2024-01-01T10:00:00Z", "fields": [{"field": {"id": "status"}, "to": {"display": "В работе"}}]}]))
                    else:  # Last 3 tasks have no changes
                        changelogs_data.append((task_id, []))
                
                mock_service.get_changelogs_batch.return_value = changelogs_data
                
                # Mock extract_status_history_with_initial_status
                def mock_extract_status_history_with_initial_status(changelog, task_data, task_key):
                    if changelog:  # Has changes
                        return [{"status": "В работе", "status_display": "В работе", "start_date": datetime.now(timezone.utc)}]
                    else:  # No changes - should add initial status
                        return [{"status": task_data["status"], "status_display": task_data["status"], "start_date": task_data["created_at"]}]
                
                mock_service.extract_status_history_with_initial_status.side_effect = [
                    mock_extract_status_history_with_initial_status(changelog[1], mock_extract_task_data(tasks_data[i][1]), f"TEST-{i+1}")
                    for i, changelog in enumerate(changelogs_data)
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
                            def mock_get_by_tracker_id(db, tracker_id):
                                task_index = int(task_id.replace("task", "")) - 1
                                return Mock(id=task_index + 1, key=f"TEST-{task_index + 1}")
                            
                            mock_task_crud.get_by_tracker_id.side_effect = [mock_get_by_tracker_id(None, task_id) for task_id in task_ids]
                            mock_task_crud.bulk_create_or_update.return_value = {"created": 0, "updated": 5}
                            mock_history_crud.delete_by_task_id.return_value = 0
                            mock_history_crud.bulk_create.side_effect = [1, 1, 1, 1, 1]  # All 5 tasks should have history
                            mock_history_crud.cleanup_duplicates.return_value = 0
                            
                            # Mock database session
                            with patch.object(sync_cmd, 'db') as mock_db:
                                mock_db.add.return_value = None
                                mock_db.commit.return_value = None
                                mock_db.refresh.return_value = None
                                
                                # When: We run sync
                                result = sync_cmd.run(filters={}, limit=5)
                                
                                # Then: All tasks should be counted as having history
                                assert result is True, "Sync should succeed"
                                # This assertion should FAIL until we implement the fix
                                # Currently: 2 tasks with history, 3 without
                                # After fix: 5 tasks with history (all should have initial status)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
