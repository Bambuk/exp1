"""Integration tests for Yandex Tracker API service."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
import requests

from radiator.services.tracker_service import TrackerAPIService


class TestTrackerAPIServiceIntegration:
    """Integration tests for TrackerAPIService with real API calls."""

    @pytest.fixture
    def service(self):
        """Create TrackerAPIService instance for testing."""
        with patch("radiator.services.tracker_service.logger"):
            service = TrackerAPIService()
            # Set test configuration
            service.headers = {
                "Authorization": "OAuth test_token_123",
                "X-Org-ID": "test_org_456",
                "Content-Type": "application/json",
            }
            service.base_url = "https://api.tracker.yandex.net/v2/"
            service.max_workers = 5
            service.request_delay = 0.1
            return service

    def test_service_initialization(self, service):
        """Test that service initializes with correct configuration."""
        assert service.headers["Authorization"] == "OAuth test_token_123"
        assert service.headers["X-Org-ID"] == "test_org_456"
        assert service.base_url == "https://api.tracker.yandex.net/v2/"
        assert service.max_workers == 5
        assert service.request_delay == 0.1

    def test_make_request_with_real_http_call(self, service):
        """Test making actual HTTP request (with mocked response)."""
        # Mock the actual HTTP request but test the request construction
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}

        with patch(
            "radiator.services.tracker_service.requests.request",
            return_value=mock_response,
        ) as mock_request:
            response = service._make_request("https://api.tracker.yandex.net/v2/issues")

            # Verify the request was made with correct parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args

            # Check URL
            assert call_args[0][0] == "GET"
            assert call_args[0][1] == "https://api.tracker.yandex.net/v2/issues"

            # Check headers
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "OAuth test_token_123"
            assert headers["X-Org-ID"] == "test_org_456"
            assert headers["Content-Type"] == "application/json"

            # Check response
            assert response.status_code == 200
            assert response.json() == {"test": "data"}

    def test_search_tasks_integration(self, service):
        """Test search_tasks with real API call structure."""
        # Mock response that simulates real API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"X-Total-Pages": "1", "X-Total-Count": "2"}
        mock_response.json.return_value = [
            {
                "id": "12345",
                "key": "TEST-123",
                "summary": "Test Task 1",
                "status": {"key": "open", "display": "Open"},
                "assignee": {"id": "user1", "display": "Test User 1"},
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-02T00:00:00Z",
            },
            {
                "id": "67890",
                "key": "TEST-456",
                "summary": "Test Task 2",
                "status": {"key": "in_progress", "display": "In Progress"},
                "assignee": {"id": "user2", "display": "Test User 2"},
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-03T00:00:00Z",
            },
        ]

        with patch(
            "radiator.services.tracker_service.requests.request",
            return_value=mock_response,
        ) as mock_request:
            result = service.search_tasks("Updated: >2024-01-01", limit=10)

            # Verify the search was called with correct parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args

            # Check that the query was properly constructed
            assert "Updated: >2024-01-01" in str(call_args[1].get("json", {}))

            # Verify result processing
            assert len(result) == 2
            assert "12345" in result
            assert "67890" in result

    def test_get_task_integration(self, service):
        """Test getting single task with real API call structure."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
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
            "labels": ["urgent"],
        }

        with patch(
            "radiator.services.tracker_service.requests.request",
            return_value=mock_response,
        ) as mock_request:
            result = service.get_task("12345")

            # Verify the request was made to correct endpoint
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert "12345" in call_args[0][1]  # Task ID in URL

            # Verify result processing
            assert result["id"] == "12345"
            assert result["key"] == "TEST-123"
            assert result["summary"] == "Test Task"

    def test_get_task_changelog_integration(self, service):
        """Test getting task changelog with real API call structure."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": 1,
                "updatedAt": "2024-01-01T10:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status", "display": "Status"},
                        "from": {"display": "Open"},
                        "to": {"display": "In Progress"},
                    }
                ],
            },
            {
                "id": 2,
                "updatedAt": "2024-01-01T15:00:00Z",
                "fields": [
                    {
                        "field": {"id": "assignee", "display": "Assignee"},
                        "from": None,
                        "to": {"id": "user2", "display": "Another User"},
                    }
                ],
            },
        ]

        with patch(
            "radiator.services.tracker_service.requests.request",
            return_value=mock_response,
        ) as mock_request:
            result = service.get_task_changelog("12345")

            # Verify the request was made to correct endpoint
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert "12345" in call_args[0][1]  # Task ID in URL
            assert "changelog" in call_args[0][1]  # Changelog endpoint

            # Verify result processing
            assert len(result) == 2
            assert result[0]["fields"][0]["field"]["id"] == "status"
            assert result[1]["fields"][0]["field"]["id"] == "assignee"

    def test_extract_task_data_real_structure(self, service):
        """Test task data extraction with real API response structure."""
        real_task_data = {
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
            "labels": ["urgent"],
        }

        result = service.extract_task_data(real_task_data)

        # Verify all fields are extracted correctly
        assert result["tracker_id"] == "12345"
        assert result["key"] == "TEST-123"
        assert result["summary"] == "Test Task"
        assert result["description"] == "Test Description"
        assert result["status"] == "Open"
        assert result["assignee"] == "Test User"
        assert result["created_at"] == datetime(
            2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc
        )
        assert result["task_updated_at"] == datetime(
            2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc
        )

    def test_extract_status_history_real_structure(self, service):
        """Test status history extraction with real changelog structure."""
        real_changelog = [
            {
                "id": 1,
                "updatedAt": "2024-01-01T10:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status", "display": "Status"},
                        "from": {"display": "Open"},
                        "to": {"display": "In Progress"},
                    }
                ],
            },
            {
                "id": 2,
                "updatedAt": "2024-01-01T15:00:00Z",
                "fields": [
                    {
                        "field": {"id": "status", "display": "Status"},
                        "from": {"display": "In Progress"},
                        "to": {"display": "Done"},
                    }
                ],
            },
        ]

        result = service.extract_status_history(real_changelog)

        # Verify status history extraction
        assert len(result) == 2
        assert result[0]["status"] == "In Progress"
        assert result[0]["status_display"] == "In Progress"
        assert result[0]["start_date"] == datetime(
            2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc
        )
        assert result[1]["status"] == "Done"
        assert result[1]["status_display"] == "Done"
        assert result[1]["start_date"] == datetime(
            2024, 1, 1, 15, 0, 0, tzinfo=timezone.utc
        )

    def test_error_handling_integration(self, service):
        """Test error handling with real error scenarios."""
        # Test HTTP error
        mock_error_response = Mock()
        mock_error_response.status_code = 400
        mock_error_response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError("400 Client Error")
        )

        with patch(
            "radiator.services.tracker_service.requests.request",
            return_value=mock_error_response,
        ):
            with pytest.raises(requests.exceptions.HTTPError):
                service._make_request("https://api.tracker.yandex.net/v2/issues")

        # Test connection error
        with patch(
            "radiator.services.tracker_service.requests.request",
            side_effect=requests.exceptions.ConnectionError("Connection failed"),
        ):
            with pytest.raises(requests.exceptions.ConnectionError):
                service._make_request("https://api.tracker.yandex.net/v2/issues")

    def test_rate_limiting_integration(self, service):
        """Test rate limiting with real timing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "12345"}]

        with patch(
            "radiator.services.tracker_service.requests.request",
            return_value=mock_response,
        ):
            with patch("time.sleep") as mock_sleep:
                service.search_tasks("test query")
                service.search_tasks("another query")

                # Verify sleep was called between requests
                assert mock_sleep.call_count >= 1
                # Verify sleep duration matches request_delay
                assert mock_sleep.call_args[0][0] == service.request_delay

    def test_parallel_processing_integration(self, service):
        """Test parallel processing with real task IDs."""
        mock_task_data = {"id": "12345", "key": "TEST-123", "summary": "Test Task"}

        with patch.object(
            service, "get_task", return_value=mock_task_data
        ) as mock_get_task:
            task_ids = ["12345", "67890", "11111"]
            result = service.get_tasks_batch(task_ids)

            # Verify all tasks were processed
            assert len(result) == 3
            assert all(isinstance(task, tuple) for task in result)
            assert all(task[1]["id"] == "12345" for task in result)

            # Verify get_task was called for each task ID
            assert mock_get_task.call_count == 3

    def test_pagination_integration(self, service):
        """Test pagination with real page structure."""
        # Mock first page
        page1_response = Mock()
        page1_response.status_code = 200
        page1_response.headers = {"X-Total-Pages": "2", "X-Total-Count": "100"}
        page1_response.json.return_value = [{"id": str(i)} for i in range(1, 51)]

        # Mock second page
        page2_response = Mock()
        page2_response.status_code = 200
        page2_response.headers = {"X-Total-Pages": "2", "X-Total-Count": "100"}
        page2_response.json.return_value = [{"id": str(i)} for i in range(51, 101)]

        with patch(
            "radiator.services.tracker_service.requests.request"
        ) as mock_request:
            mock_request.side_effect = [page1_response, page2_response]

            result = service.search_tasks("test query", limit=100)

            # Verify pagination worked correctly
            assert len(result) == 100
            assert "1" in result
            assert "100" in result
            assert mock_request.call_count == 2

    def test_get_active_tasks_fallback_integration(self, service):
        """Test active tasks fallback mechanism."""
        # Mock search_tasks to fail first, then succeed on fallback
        with patch.object(
            service,
            "search_tasks",
            side_effect=[
                Exception("First call fails"),  # First call fails
                ["12345", "67890"],  # Fallback call succeeds
            ],
        ):
            result = service.get_active_tasks(limit=10)

            # Verify fallback worked
            assert len(result) == 2
            assert "12345" in result
            assert "67890" in result

    def test_get_tasks_by_filter_integration(self, service):
        """Test get_tasks_by_filter with real filter structure."""
        with patch.object(
            service, "search_tasks", return_value=["12345", "67890"]
        ) as mock_search:
            filters = {
                "query": "Updated: >2024-01-01",
                "status": "open",
                "assignee": "user1",
            }
            result = service.get_tasks_by_filter(filters, limit=50)

            # Verify search_tasks was called with correct parameters
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert call_args[1]["query"] == "Updated: >2024-01-01"
            assert call_args[1]["limit"] == 50

            # Verify result
            assert result == ["12345", "67890"]

    def test_get_recent_tasks_integration(self, service):
        """Test get_recent_tasks with real date calculation."""
        with patch.object(
            service, "search_tasks", return_value=["12345"]
        ) as mock_search:
            result = service.get_recent_tasks(days=7, limit=25)

            # Verify search_tasks was called with correct parameters
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert call_args[1]["limit"] == 25
            # Verify query contains date filter
            query = call_args[1]["query"]
            assert "Updated: >" in query

            # Verify result
            assert result == ["12345"]


class TestTrackerAPIServiceFieldsParameter:
    """Tests for TrackerAPIService with fields parameter support."""

    @pytest.fixture
    def service(self):
        """Create TrackerAPIService instance for testing."""
        with patch("radiator.services.tracker_service.logger"):
            service = TrackerAPIService()
            # Set test configuration
            service.headers = {
                "Authorization": "OAuth test_token_123",
                "X-Org-ID": "test_org_456",
                "Content-Type": "application/json",
            }
            service.base_url = "https://api.tracker.yandex.net/v2/"
            service.max_workers = 5
            service.request_delay = 0.1
            return service

    def test_get_task_with_fields_parameter(self, service):
        """Test get_task method with fields parameter."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "12345",
            "key": "TEST-123",
            "summary": "Test Task",
            "status": {"display": "Open"},
            "customer": "Test Customer",
        }

        with patch(
            "radiator.services.tracker_service.requests.request",
            return_value=mock_response,
        ) as mock_request:
            result = service.get_task(
                "12345", fields=["id", "key", "summary", "customer"]
            )

            # Verify the request was made with correct parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args

            # Check URL
            assert call_args[0][1] == "https://api.tracker.yandex.net/v2/issues/12345"

            # Check params include fields
            params = call_args[1]["params"]
            assert params["fields"] == "id,key,summary,customer"

            # Check response
            assert result["id"] == "12345"
            assert result["key"] == "TEST-123"
            assert result["customer"] == "Test Customer"

    def test_search_tasks_with_data_with_fields_parameter(self, service):
        """Test search_tasks_with_data method with fields parameter."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"X-Total-Pages": "1", "X-Total-Count": "1"}
        mock_response.json.return_value = [
            {
                "id": "12345",
                "key": "TEST-123",
                "summary": "Test Task",
                "customer": "Test Customer",
            }
        ]

        with patch(
            "radiator.services.tracker_service.requests.request",
            return_value=mock_response,
        ) as mock_request:
            result = service.search_tasks_with_data(
                query="Status: Open",
                limit=10,
                fields=["id", "key", "summary", "customer"],
            )

            # Verify the request was made with correct parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args

            # Check URL
            assert call_args[0][1] == "https://api.tracker.yandex.net/v2/issues/_search"

            # Check params include fields
            params = call_args[1]["params"]
            assert params["fields"] == "id,key,summary,customer"

            # Check response
            assert len(result) == 1
            assert result[0]["id"] == "12345"
            assert result[0]["customer"] == "Test Customer"

    def test_get_task_without_fields_parameter(self, service):
        """Test get_task method without fields parameter (backward compatibility)."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "12345",
            "key": "TEST-123",
            "summary": "Test Task",
        }

        with patch(
            "radiator.services.tracker_service.requests.request",
            return_value=mock_response,
        ) as mock_request:
            result = service.get_task("12345")

            # Verify the request was made without fields parameter
            mock_request.assert_called_once()
            call_args = mock_request.call_args

            # Check params should not include fields
            params = call_args[1].get("params", {})
            assert "fields" not in params

            # Check response
            assert result["id"] == "12345"

    def test_search_tasks_with_data_without_fields_parameter(self, service):
        """Test search_tasks_with_data method without fields parameter (backward compatibility)."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"X-Total-Pages": "1", "X-Total-Count": "1"}
        mock_response.json.return_value = [
            {"id": "12345", "key": "TEST-123", "summary": "Test Task"}
        ]

        with patch(
            "radiator.services.tracker_service.requests.request",
            return_value=mock_response,
        ) as mock_request:
            result = service.search_tasks_with_data(query="Status: Open", limit=10)

            # Verify the request was made without fields parameter
            mock_request.assert_called_once()
            call_args = mock_request.call_args

            # Check params should not include fields
            params = call_args[1].get("params", {})
            assert "fields" not in params

            # Check response
            assert len(result) == 1
            assert result[0]["id"] == "12345"

    def test_get_tasks_by_filter_with_data_with_fields_parameter(self, service):
        """Test get_tasks_by_filter_with_data method with fields parameter."""
        # Mock search_tasks_with_data to return test data
        with patch.object(
            service,
            "search_tasks_with_data",
            return_value=[{"id": "12345", "key": "TEST-123"}],
        ) as mock_search:
            filters = {"query": "Status: Open"}
            fields = ["id", "key", "summary", "customer"]

            result = service.get_tasks_by_filter_with_data(
                filters=filters, limit=10, fields=fields
            )

            # Verify search_tasks_with_data was called with fields parameter
            mock_search.assert_called_once()
            call_args = mock_search.call_args

            # Check that fields parameter was passed
            assert call_args[1]["fields"] == fields
            assert call_args[1]["query"] == "Status: Open"
            assert call_args[1]["limit"] == 10

            # Check response
            assert len(result) == 1
            assert result[0]["id"] == "12345"

    def test_get_tasks_by_filter_with_data_without_fields_parameter(self, service):
        """Test get_tasks_by_filter_with_data method without fields parameter (backward compatibility)."""
        # Mock search_tasks_with_data to return test data
        with patch.object(
            service,
            "search_tasks_with_data",
            return_value=[{"id": "12345", "key": "TEST-123"}],
        ) as mock_search:
            filters = {"query": "Status: Open"}

            result = service.get_tasks_by_filter_with_data(filters=filters, limit=10)

            # Verify search_tasks_with_data was called without fields parameter
            mock_search.assert_called_once()
            call_args = mock_search.call_args

            # Check that fields parameter was not passed
            assert "fields" not in call_args[1] or call_args[1]["fields"] is None
            assert call_args[1]["query"] == "Status: Open"
            assert call_args[1]["limit"] == 10

            # Check response
            assert len(result) == 1
            assert result[0]["id"] == "12345"

    def test_get_tasks_by_filter_with_data_built_query_with_fields(self, service):
        """Test get_tasks_by_filter_with_data with built query and fields parameter."""
        # Mock search_tasks_with_data to return test data
        with patch.object(
            service,
            "search_tasks_with_data",
            return_value=[{"id": "12345", "key": "TEST-123"}],
        ) as mock_search:
            filters = {"status": "open", "assignee": "user1"}
            fields = ["id", "key", "summary"]

            result = service.get_tasks_by_filter_with_data(
                filters=filters, limit=10, fields=fields
            )

            # Verify search_tasks_with_data was called with fields parameter
            mock_search.assert_called_once()
            call_args = mock_search.call_args

            # Check that fields parameter was passed
            assert call_args[1]["fields"] == fields
            assert 'Status: "open"' in call_args[1]["query"]
            assert 'Assignee: "user1"' in call_args[1]["query"]
            assert call_args[1]["limit"] == 10

            # Check response
            assert len(result) == 1
            assert result[0]["id"] == "12345"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
