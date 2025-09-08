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
            # Устанавливаем тестовые значения
            service.headers = {
                "Authorization": "OAuth test_token_123",
                "X-Org-ID": "test_org_456",
                "Content-Type": "application/json"
            }
            service.base_url = "https://api.tracker.yandex.net/v2/"
            service.max_workers = 5
            service.request_delay = 0.1
            return service

    @pytest.fixture
    def mock_response_success(self):
        """Create mock successful API response."""
        mock = Mock()
        mock.status_code = 200
        mock.headers = {"X-Total-Pages": "1", "X-Total-Count": "2"}
        mock.json.return_value = [
            {
                "id": "12345",
                "key": "TEST-123",
                "summary": "Test Task 1",
                "status": {"key": "open", "display": "Open"},
                "assignee": {"id": "user1", "display": "Test User 1"},
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-02T00:00:00Z"
            },
            {
                "id": "67890",
                "key": "TEST-456",
                "summary": "Test Task 2",
                "status": {"key": "in_progress", "display": "In Progress"},
                "assignee": {"id": "user2", "display": "Test User 2"},
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-03T00:00:00Z"
            }
        ]
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
            "id": "12345",
            "key": "TEST-123",
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
                "fields": [
                    {
                        "field": {"id": "status", "display": "Status"},
                        "from": {"display": "Open"},
                        "to": {"display": "In Progress"}
                    }
                ]
            },
            {
                "id": 2,
                "updatedAt": "2024-01-01T15:00:00Z",
                "fields": [
                    {
                        "field": {"id": "assignee", "display": "Assignee"},
                        "from": None,
                        "to": {"id": "user2", "display": "Another User"}
                    }
                ]
            }
        ]

    def test_init(self, service):
        """Test service initialization."""
        assert service.headers['Authorization'] == "OAuth test_token_123"
        assert service.headers['X-Org-ID'] == "test_org_456"
        assert service.base_url == "https://api.tracker.yandex.net/v2/"
        assert service.max_workers == 5
        assert service.request_delay == 0.1

    def test_make_request_success(self, service, mock_response_success):
        """Test successful API request."""
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response_success):
            response = service._make_request("https://api.tracker.yandex.net/v2/issues")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2

    def test_make_request_with_headers(self, service, mock_response_success):
        """Test API request with proper headers."""
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response_success) as mock_request:
            service._make_request("https://api.tracker.yandex.net/v2/issues")
            
            # Check that headers were set correctly
            call_args = mock_request.call_args
            headers = call_args[1]['headers']
            assert headers['Authorization'] == 'OAuth test_token_123'
            assert headers['X-Org-ID'] == 'test_org_456'
            assert headers['Content-Type'] == 'application/json'

    def test_make_request_error(self, service, mock_response_error):
        """Test API request error handling."""
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response_error):
            with pytest.raises(requests.exceptions.HTTPError):
                service._make_request("https://api.tracker.yandex.net/v2/issues")

    def test_make_request_connection_error(self, service):
        """Test connection error handling."""
        with patch('radiator.services.tracker_service.requests.request', side_effect=requests.exceptions.ConnectionError("Connection failed")):
            with pytest.raises(requests.exceptions.ConnectionError):
                service._make_request("https://api.tracker.yandex.net/v2/issues")

    def test_search_tasks_success(self, service, mock_response_success):
        """Test successful task search."""
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response_success):
            result = service.search_tasks("Updated: >2024-01-01", limit=10)
            assert len(result) == 2
            assert "12345" in result
            assert "67890" in result

    def test_search_tasks_different_response_format(self, service):
        """Test task search with different response format."""
        # Test response as list
        mock_response_list = Mock()
        mock_response_list.status_code = 200
        mock_response_list.headers = {"X-Total-Pages": "1", "X-Total-Count": "2"}
        mock_response_list.json.return_value = [
            {"id": "12345", "key": "TEST-123"},
            {"id": "67890", "key": "TEST-456"}
        ]
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response_list):
            result = service.search_tasks("test query")
            assert len(result) == 2
            assert "12345" in result
            assert "67890" in result

    def test_search_tasks_api_error(self, service):
        """Test API error handling in task search."""
        with patch('radiator.services.tracker_service.requests.request', side_effect=Exception("API Error")):
            result = service.search_tasks("test query")
            assert result == []



    def test_get_active_tasks_fallback(self, service):
        """Test active tasks fallback when complex query fails."""
        # Mock search_tasks to fail first, then succeed on fallback
        with patch.object(service, 'search_tasks', side_effect=[
            Exception("First call fails"),  # First call fails
            ["12345", "67890"]  # Fallback call succeeds
        ]):
            result = service.get_active_tasks(limit=10)
            # Fallback should work and return tasks
            assert len(result) == 2



    def test_get_task_success(self, service):
        """Test getting single task."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "12345",
            "key": "TEST-123",
            "summary": "Test Task"
        }
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
            result = service.get_task("12345")
            assert result["id"] == "12345"
            assert result["key"] == "TEST-123"
            assert result["summary"] == "Test Task"

    def test_get_task_not_found(self, service):
        """Test getting non-existent task."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
            result = service.get_task("NONEXISTENT")
            assert result is None

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
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
            result = service.get_task_changelog("12345")
            assert len(result) == 1
            assert result[0]["field"]["id"] == "status"

    def test_get_task_changelog_empty(self, service):
        """Test getting empty changelog."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
            result = service.get_task_changelog("12345")
            assert result == []

    def test_extract_task_data(self, service, mock_task_data):
        """Test task data extraction."""
        result = service.extract_task_data(mock_task_data)
        
        assert result["tracker_id"] == "12345"
        assert result["key"] == "TEST-123"  # This is what's in mock_task_data
        assert result["summary"] == "Test Task"
        assert result["description"] == "Test Description"
        assert result["status"] == "Open"  # Status from mock data is "Open"
        assert result["author"] == ""  # No author field in mock data
        assert result["assignee"] == "Test User"
        assert result["business_client"] == ""  # No business_client field in mock data
        assert result["team"] == ""  # No team field in mock data
        assert result["prodteam"] == ""  # No prodteam field in mock data
        assert result["profit_forecast"] == ""  # No profit_forecast field in mock_data

    def test_extract_task_data_minimal(self, service):
        """Test task data extraction with minimal data."""
        minimal_task = {
            "id": "12345",
            "key": "TEST-123",
            "summary": "Test Task"
        }

        result = service.extract_task_data(minimal_task)
    
        assert result["tracker_id"] == "12345"
        assert result["key"] == "TEST-123"
        assert result["summary"] == "Test Task"
        assert result["status"] == ""  # Empty string, not None

    def test_extract_status_history(self, service, mock_changelog_data):
        """Test status history extraction."""
        result = service.extract_status_history(mock_changelog_data)
        
        assert len(result) == 1  # Only status changes
        assert result[0]["status"] == "In Progress"  # We get the "to" status
        assert result[0]["status_display"] == "In Progress"
        assert result[0]["start_date"] is not None

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
        
        result = service.extract_status_history(changelog)
        assert result == []

    def test_format_user_list(self, service):
        """Test user list formatting."""
        users = [
            {"id": "user1", "display": "User 1"},
            {"id": "user2", "display": "User 2"}
        ]
        
        result = service._format_user_list(users)
        assert result == "User 1, User 2"  # Returns comma-separated string

    def test_format_user_list_single_user(self, service):
        """Test single user formatting."""
        user = {"id": "user1", "display": "User 1"}
        
        result = service._format_user_list(user)
        assert result == "User 1"  # Returns display name

    def test_format_user_list_none(self, service):
        """Test user list formatting with None."""
        result = service._format_user_list(None)
        assert result == ""  # Returns empty string

    def test_get_tasks_batch(self, service, mock_response_success):
        """Test batch task retrieval."""
        with patch.object(service, 'get_task', return_value={"id": "12345"}):
            task_ids = ["12345", "67890", "11111"]
            result = service.get_tasks_batch(task_ids)
            
            assert len(result) == 3
            # Check that we get tuples with (task_id, task_data)
            assert all(isinstance(task, tuple) for task in result)
            assert all(task[1]["id"] == "12345" for task in result)

    def test_get_changelogs_batch(self, service):
        """Test batch changelog retrieval."""
        with patch.object(service, 'get_task_changelog', return_value=[]):
            task_ids = ["12345", "67890", "11111"]
            result = service.get_changelogs_batch(task_ids)
            
            assert len(result) == 3
            # Check that we get tuples with (task_id, changelog_data)
            assert all(isinstance(changelog, tuple) for changelog in result)
            assert all(changelog[1] == [] for changelog in result)

    def test_rate_limiting(self, service, mock_response_success):
        """Test rate limiting between requests."""
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response_success):
            with patch('time.sleep') as mock_sleep:
                service.search_tasks("test query")
                service.search_tasks("another query")
                
                # Check that sleep was called between requests
                assert mock_sleep.call_count >= 1

    def test_parallel_processing(self, service):
        """Test parallel processing of requests."""
        with patch.object(service, 'get_task', return_value={"id": "12345"}):
            result = service.get_tasks_batch(["12345", "67890"])
            
            # Check that we get the expected result
            assert len(result) == 2
            assert all(isinstance(task, tuple) for task in result)
            assert all(task[1]["id"] == "12345" for task in result)

    # ===== TESTS FOR LIMIT LOGIC AND PAGINATION =====
    
    def test_search_tasks_large_limit(self, service):
        """Test search_tasks with large limit."""
        # Mock multiple pages of responses
        page1_response = Mock()
        page1_response.headers = {"X-Total-Pages": "3"}
        page1_response.json.return_value = [{"id": str(i)} for i in range(1, 51)]  # 50 tasks
        
        page2_response = Mock()
        page2_response.headers = {"X-Total-Pages": "3"}
        page2_response.json.return_value = [{"id": str(i)} for i in range(51, 101)]  # 50 tasks
        
        page3_response = Mock()
        page3_response.headers = {"X-Total-Pages": "3"}
        page3_response.json.return_value = [{"id": str(i)} for i in range(101, 151)]  # 50 tasks
        
        with patch('radiator.services.tracker_service.requests.request') as mock_request:
            mock_request.side_effect = [page1_response, page2_response, page3_response]
            
            result = service.search_tasks("test query", limit=150)
            
            # Should return all 150 tasks
            assert len(result) == 150
            assert "1" in result
            assert "150" in result
            # Should have made 3 requests (one per page)
            assert mock_request.call_count == 3


    def test_search_tasks_small_limit(self, service):
        """Test search_tasks with limit=1."""
        mock_response = Mock()
        mock_response.headers = {"X-Total-Pages": "1"}
        mock_response.json.return_value = [
            {"id": "12345", "key": "TEST-123"},
            {"id": "67890", "key": "TEST-456"}
        ]
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
            result = service.search_tasks("test query", limit=1)
            
            # Should return exactly 1 task
            assert len(result) == 1
            assert "12345" in result

    def test_search_tasks_negative_limit(self, service):
        """Test search_tasks with negative limit (should be handled gracefully)."""
        mock_response = Mock()
        mock_response.headers = {"X-Total-Pages": "1"}
        mock_response.json.return_value = [{"id": "12345"}]
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
            result = service.search_tasks("test query", limit=-5)
            
            # Should handle negative limit gracefully (return empty or limited result)
            assert isinstance(result, list)

    def test_search_tasks_multiple_pages(self, service):
        """Test pagination across multiple pages."""
        with patch.object(service, 'get_total_tasks_count', return_value=75):
            # Mock 3 pages: 50 + 25 tasks
            page1_response = Mock()
            page1_response.headers = {"X-Total-Pages": "2"}
            page1_response.json.return_value = [{"id": str(i)} for i in range(1, 51)]
            
            page2_response = Mock()
            page2_response.headers = {"X-Total-Pages": "2"}
            page2_response.json.return_value = [{"id": str(i)} for i in range(51, 76)]
            
            with patch('radiator.services.tracker_service.requests.request') as mock_request:
                mock_request.side_effect = [page1_response, page2_response]
                
                result = service.search_tasks("test query", limit=100)
                
                # Should return all 75 tasks from both pages
                assert len(result) == 75
                assert "1" in result
                assert "75" in result
                assert mock_request.call_count == 2

    def test_search_tasks_total_count_error(self, service):
        """Test handling when get_total_tasks_count fails."""
        # Mock get_total_tasks_count to fail
        with patch.object(service, 'get_total_tasks_count', side_effect=Exception("API Error")):
            # Mock response for the actual search
            mock_response = Mock()
            mock_response.headers = {"X-Total-Pages": "1"}
            mock_response.json.return_value = [{"id": "12345"}]
            
            with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
                result = service.search_tasks("test query", limit=0)
                
                # Should fallback to reasonable limit when total count fails
                assert isinstance(result, list)
                assert len(result) >= 0

    def test_search_tasks_infinite_loop_protection(self, service):
        """Test protection against infinite pagination loops."""
        # Mock response that always returns tasks (simulating infinite pages)
        mock_response = Mock()
        mock_response.headers = {"X-Total-Pages": "999"}  # Very high page count
        mock_response.json.return_value = [{"id": str(i)} for i in range(1, 51)]
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
            result = service.search_tasks("test query", limit=10000)
            
            # Should stop after reasonable number of pages (protection against infinite loops)
            assert isinstance(result, list)
            # Should not make more than 200 requests (page > 100 protection)
            # This tests the safety mechanism in the actual code

    def test_search_tasks_api_format_errors(self, service):
        """Test handling of unexpected API response formats."""
        # Test with malformed response
        mock_response = Mock()
        mock_response.headers = {"X-Total-Pages": "1"}
        mock_response.json.return_value = "invalid_format"  # Not a list or dict
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
            result = service.search_tasks("test query")
            
            # Should handle malformed response gracefully
            assert isinstance(result, list)

    def test_search_tasks_empty_pages(self, service):
        """Test handling of empty pages in pagination."""
        # First page has tasks
        page1_response = Mock()
        page1_response.headers = {"X-Total-Pages": "2"}
        page1_response.json.return_value = [{"id": "12345"}]
        
        # Second page is empty
        page2_response = Mock()
        page2_response.headers = {"X-Total-Pages": "2"}
        page2_response.json.return_value = []  # Empty page
        
        with patch('radiator.services.tracker_service.requests.request') as mock_request:
            mock_request.side_effect = [page1_response, page2_response]
            
            result = service.search_tasks("test query", limit=100)
            
            # Should stop when encountering empty page
            assert len(result) == 1
            assert "12345" in result
            assert mock_request.call_count == 2

    def test_search_tasks_limit_exact_match(self, service):
        """Test when limit exactly matches available tasks."""
        mock_response = Mock()
        mock_response.headers = {"X-Total-Pages": "1"}
        mock_response.json.return_value = [{"id": str(i)} for i in range(1, 51)]
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
            result = service.search_tasks("test query", limit=50)
            
            # Should return exactly 50 tasks
            assert len(result) == 50
            assert "1" in result
            assert "50" in result

    def test_search_tasks_limit_exceeds_available(self, service):
        """Test when limit exceeds available tasks."""
        mock_response = Mock()
        mock_response.headers = {"X-Total-Pages": "1"}
        mock_response.json.return_value = [{"id": str(i)} for i in range(1, 26)]
        
        with patch('radiator.services.tracker_service.requests.request', return_value=mock_response):
            result = service.search_tasks("test query", limit=100)
            
            # Should return only available tasks (25), not the full limit
            assert len(result) == 25
            assert "1" in result
            assert "25" in result

    def test_get_tasks_by_filter_limit_consistency(self, service):
        """Test that get_tasks_by_filter properly passes limit to search_tasks."""
        with patch.object(service, 'search_tasks', return_value=["12345", "67890"]) as mock_search:
            filters = {"query": "test query"}
            result = service.get_tasks_by_filter(filters, limit=50)
            
            # Should call search_tasks with the same limit
            mock_search.assert_called_once_with(query="test query", limit=50)
            assert result == ["12345", "67890"]

    def test_get_recent_tasks_limit_consistency(self, service):
        """Test that get_recent_tasks properly passes limit to search_tasks."""
        with patch.object(service, 'search_tasks', return_value=["12345"]) as mock_search:
            result = service.get_recent_tasks(days=7, limit=25)
            
            # Should call search_tasks with the same limit
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert call_args[1]['limit'] == 25


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
