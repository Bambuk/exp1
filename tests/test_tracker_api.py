"""Tests for Yandex Tracker API service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import requests

from radiator.services.tracker_service import TrackerAPIService


class TestTrackerAPIService:
    """Test TrackerAPIService class."""

    @pytest.fixture
    def service(self):
        """Create TrackerAPIService instance for testing."""
        with patch('radiator.services.tracker_service.logger'):
            service = TrackerAPIService()
            service.api_token = "test_token_123"
            service.org_id = "test_org_456"
            service.base_url = "https://api.tracker.yandex.net/v2/"
            service.max_workers = 5
            service.request_delay = 0.1
            return service

    @pytest.fixture
    def mock_response_success(self):
        """Create mock successful API response."""
        mock = Mock()
        mock.status_code = 200
        mock.json.return_value = {
            "issues": [
                {
                    "id": "TEST-1",
                    "key": "TEST-1",
                    "summary": "Test Task 1",
                    "status": {"key": "open", "display": "Open"},
                    "assignee": {"id": "user1", "display": "Test User 1"},
                    "createdAt": "2024-01-01T00:00:00Z",
                    "updatedAt": "2024-01-02T00:00:00Z"
                },
                {
                    "id": "TEST-2",
                    "key": "TEST-2",
                    "summary": "Test Task 2",
                    "status": {"key": "in_progress", "display": "In Progress"},
                    "assignee": {"id": "user2", "display": "Test User 2"},
                    "createdAt": "2024-01-01T00:00:00Z",
                    "updatedAt": "2024-01-03T00:00:00Z"
                }
            ]
        }
        return mock

    @pytest.fixture
    def mock_response_error(self):
        """Create mock error API response."""
        mock = Mock()
        mock.status_code = 400
        mock.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Client Error")
        return mock

    @pytest.fixture
    def mock_task_data(self):
        """Sample task data from API."""
        return {
            "id": "TEST-1",
            "key": "TEST-1",
            "summary": "Test Task",
            "description": "Test Description",
            "status": {"key": "open", "display": "Open"},
            "priority": {"key": "normal", "display": "Normal"},
            "assignee": {"id": "user1", "display": "Test User"},
            "reporter": {"id": "user2", "display": "Reporter User"},
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
            "resolvedAt": None,
            "dueDate": None,
            "tags": ["test", "bug"],
            "components": ["frontend"],
            "versions": ["v1.0"],
            "labels": ["urgent"]
        }

    @pytest.fixture
    def mock_changelog_data(self):
        """Sample changelog data from API."""
        return [
            {
                "id": 1,
                "updatedAt": "2024-01-01T10:00:00Z",
                "field": {"id": "status", "display": "Status"},
                "from": {"display": "Open"},
                "to": {"display": "In Progress"},
                "author": {"id": "user1", "display": "Test User"}
            },
            {
                "id": 2,
                "updatedAt": "2024-01-01T15:00:00Z",
                "field": {"id": "assignee", "display": "Assignee"},
                "from": None,
                "to": {"id": "user2", "display": "Another User"},
                "author": {"id": "user1", "display": "Test User"}
            }
        ]

    def test_init(self, service):
        """Test service initialization."""
        assert service.api_token == "test_token_123"
        assert service.org_id == "test_org_456"
        assert service.base_url == "https://api.tracker.yandex.net/v2/"
        assert service.max_workers == 5
        assert service.request_delay == 0.1

    def test_make_request_success(self, service, mock_response_success):
        """Test successful API request."""
        with patch('requests.get', return_value=mock_response_success):
            response = service._make_request("https://api.tracker.yandex.net/v2/issues")
            assert response.status_code == 200
            data = response.json()
            assert "issues" in data
            assert len(data["issues"]) == 2

    def test_make_request_with_headers(self, service, mock_response_success):
        """Test API request with proper headers."""
        with patch('requests.get', return_value=mock_response_success) as mock_get:
            service._make_request("https://api.tracker.yandex.net/v2/issues")
            
            # Check that headers were set correctly
            call_args = mock_get.call_args
            headers = call_args[1]['headers']
            assert headers['Authorization'] == 'OAuth test_token_123'
            assert headers['X-Org-ID'] == 'test_org_456'
            assert headers['Content-Type'] == 'application/json'

    def test_make_request_error(self, service, mock_response_error):
        """Test API request error handling."""
        with patch('requests.get', return_value=mock_response_error):
            with pytest.raises(requests.exceptions.HTTPError):
                service._make_request("https://api.tracker.yandex.net/v2/issues")

    def test_make_request_connection_error(self, service):
        """Test connection error handling."""
        with patch('requests.get', side_effect=requests.exceptions.ConnectionError("Connection failed")):
            with pytest.raises(requests.exceptions.ConnectionError):
                service._make_request("https://api.tracker.yandex.net/v2/issues")

    def test_search_tasks_success(self, service, mock_response_success):
        """Test successful task search."""
        with patch('requests.get', return_value=mock_response_success):
            result = service.search_tasks("Updated: >2024-01-01", limit=10)
            assert len(result) == 2
            assert "TEST-1" in result
            assert "TEST-2" in result

    def test_search_tasks_different_response_format(self, service):
        """Test task search with different response format."""
        # Test response as list
        mock_response_list = Mock()
        mock_response_list.status_code = 200
        mock_response_list.json.return_value = [
            {"id": "TEST-1", "key": "TEST-1"},
            {"id": "TEST-2", "key": "TEST-2"}
        ]
        
        with patch('requests.get', return_value=mock_response_list):
            result = service.search_tasks("test query")
            assert len(result) == 2
            assert "TEST-1" in result
            assert "TEST-2" in result

    def test_search_tasks_api_error(self, service):
        """Test API error handling in task search."""
        with patch('requests.get', side_effect=Exception("API Error")):
            result = service.search_tasks("test query")
            assert result == []

    def test_get_recent_tasks(self, service, mock_response_success):
        """Test getting recent tasks."""
        with patch('requests.get', return_value=mock_response_success):
            result = service.get_recent_tasks(days=7, limit=10)
            assert len(result) == 2
            assert "TEST-1" in result
            assert "TEST-2" in result

    def test_get_recent_tasks_custom_days(self, service, mock_response_success):
        """Test getting recent tasks with custom days."""
        with patch('requests.get', return_value=mock_response_success):
            result = service.get_recent_tasks(days=30, limit=5)
            assert len(result) == 2

    def test_get_active_tasks(self, service, mock_response_success):
        """Test getting active tasks."""
        with patch('requests.get', return_value=mock_response_success):
            result = service.get_active_tasks(limit=10)
            assert len(result) == 2

    def test_get_active_tasks_fallback(self, service):
        """Test active tasks fallback when complex query fails."""
        # Mock first call to fail with 422
        mock_response_error = Mock()
        mock_response_error.status_code = 422
        mock_response_error.raise_for_status.side_effect = requests.exceptions.HTTPError("422 Client Error")
        
        # Mock second call to succeed
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "issues": [{"id": "TEST-1"}, {"id": "TEST-2"}]
        }
        
        with patch('requests.get', side_effect=[mock_response_error, mock_response_success]):
            result = service.get_active_tasks(limit=10)
            assert len(result) == 2

    def test_get_tasks_by_filter(self, service, mock_response_success):
        """Test getting tasks by filter."""
        with patch('requests.get', return_value=mock_response_success):
            filters = {
                "status": "Open",
                "assignee": "test_user",
                "team": "frontend",
                "author": "user1",
                "updated_since": datetime(2024, 1, 1),
                "created_since": datetime(2024, 1, 1)
            }
            result = service.get_tasks_by_filter(filters, limit=10)
            assert len(result) == 2

    def test_get_tasks_by_filter_empty(self, service, mock_response_success):
        """Test getting tasks by filter with empty filters."""
        with patch('requests.get', return_value=mock_response_success):
            result = service.get_tasks_by_filter({}, limit=10)
            assert len(result) == 2

    def test_get_tasks_by_filter_string_dates(self, service, mock_response_success):
        """Test getting tasks by filter with string dates."""
        with patch('requests.get', return_value=mock_response_success):
            filters = {
                "updated_since": "2024-01-01",
                "created_since": "2024-01-01"
            }
            result = service.get_tasks_by_filter(filters, limit=10)
            assert len(result) == 2

    def test_get_task_success(self, service):
        """Test getting single task."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "TEST-1",
            "key": "TEST-1",
            "summary": "Test Task"
        }
        
        with patch('requests.get', return_value=mock_response):
            result = service.get_task("TEST-1")
            assert result["id"] == "TEST-1"
            assert result["key"] == "TEST-1"
            assert result["summary"] == "Test Task"

    def test_get_task_not_found(self, service):
        """Test getting non-existent task."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        
        with patch('requests.get', return_value=mock_response):
            with pytest.raises(requests.exceptions.HTTPError):
                service.get_task("NONEXISTENT")

    def test_get_task_changelog_success(self, service):
        """Test getting task changelog."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": 1,
                "updatedAt": "2024-01-01T10:00:00Z",
                "field": {"id": "status"},
                "from": {"display": "Open"},
                "to": {"display": "In Progress"}
            }
        ]
        
        with patch('requests.get', return_value=mock_response):
            result = service.get_task_changelog("TEST-1")
            assert len(result) == 1
            assert result[0]["field"]["id"] == "status"

    def test_get_task_changelog_empty(self, service):
        """Test getting empty changelog."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        
        with patch('requests.get', return_value=mock_response):
            result = service.get_task_changelog("TEST-1")
            assert result == []

    def test_extract_task_data(self, service, mock_task_data):
        """Test task data extraction."""
        result = service.extract_task_data(mock_task_data)
        
        assert result["tracker_id"] == "TEST-1"
        assert result["key"] == "TEST-1"
        assert result["summary"] == "Test Task"
        assert result["description"] == "Test Description"
        assert result["status"] == "open"
        assert result["priority"] == "normal"
        assert result["assignee_id"] == "user1"
        assert result["assignee_name"] == "Test User"
        assert result["reporter_id"] == "user2"
        assert result["reporter_name"] == "Reporter User"
        assert result["tags"] == ["test", "bug"]
        assert result["components"] == ["frontend"]
        assert result["versions"] == ["v1.0"]
        assert result["labels"] == ["urgent"]

    def test_extract_task_data_minimal(self, service):
        """Test task data extraction with minimal data."""
        minimal_task = {
            "id": "TEST-1",
            "key": "TEST-1",
            "summary": "Test Task"
        }
        
        result = service.extract_task_data(minimal_task)
        
        assert result["tracker_id"] == "TEST-1"
        assert result["key"] == "TEST-1"
        assert result["summary"] == "Test Task"
        assert result["status"] is None
        assert result["assignee_id"] is None

    def test_extract_status_history(self, service, mock_changelog_data):
        """Test status history extraction."""
        result = service.extract_status_history("TEST-1", mock_changelog_data)
        
        assert len(result) == 1  # Only status changes
        assert result[0]["tracker_id"] == "TEST-1"
        assert result[0]["old_status"] == "Open"
        assert result[0]["new_status"] == "In Progress"
        assert result[0]["start_date"] is not None
        assert result[0]["end_date"] is not None

    def test_extract_status_history_no_status_changes(self, service):
        """Test status history extraction with no status changes."""
        changelog = [
            {
                "id": 1,
                "updatedAt": "2024-01-01T10:00:00Z",
                "field": {"id": "assignee"},
                "from": None,
                "to": {"id": "user1", "display": "Test User"}
            }
        ]
        
        result = service.extract_status_history("TEST-1", changelog)
        assert result == []

    def test_format_user_list(self, service):
        """Test user list formatting."""
        users = [
            {"id": "user1", "display": "User 1"},
            {"id": "user2", "display": "User 2"}
        ]
        
        result = service._format_user_list(users)
        assert result == ["user1", "user2"]

    def test_format_user_list_single_user(self, service):
        """Test single user formatting."""
        user = {"id": "user1", "display": "User 1"}
        
        result = service._format_user_list(user)
        assert result == ["user1"]

    def test_format_user_list_none(self, service):
        """Test user list formatting with None."""
        result = service._format_user_list(None)
        assert result == []

    def test_get_tasks_batch(self, service, mock_response_success):
        """Test batch task retrieval."""
        with patch.object(service, 'get_task', return_value={"id": "TEST-1"}):
            task_ids = ["TEST-1", "TEST-2", "TEST-3"]
            result = service.get_tasks_batch(task_ids)
            
            assert len(result) == 3
            assert all(task["id"] == "TEST-1" for task in result)

    def test_get_changelogs_batch(self, service):
        """Test batch changelog retrieval."""
        with patch.object(service, 'get_task_changelog', return_value=[]):
            task_ids = ["TEST-1", "TEST-2", "TEST-3"]
            result = service.get_changelogs_batch(task_ids)
            
            assert len(result) == 3
            assert all(changelog == [] for changelog in result)

    def test_rate_limiting(self, service, mock_response_success):
        """Test rate limiting between requests."""
        with patch('requests.get', return_value=mock_response_success):
            with patch('time.sleep') as mock_sleep:
                service.search_tasks("test query")
                service.search_tasks("another query")
                
                # Check that sleep was called between requests
                assert mock_sleep.call_count >= 1

    def test_parallel_processing(self, service):
        """Test parallel processing of requests."""
        with patch.object(service, 'get_task', return_value={"id": "TEST-1"}):
            with patch('concurrent.futures.ThreadPoolExecutor') as mock_executor:
                mock_executor.return_value.__enter__.return_value.map.return_value = [{"id": "TEST-1"}]
                
                service.get_tasks_batch(["TEST-1", "TEST-2"])
                
                # Check that ThreadPoolExecutor was used
                mock_executor.assert_called_once_with(max_workers=5)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
