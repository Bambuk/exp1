"""Tests for TrackerAPIService full_data and customer field support."""

from unittest.mock import Mock, patch

import pytest

from radiator.services.tracker_service import TrackerAPIService


class TestTrackerAPIServiceFullDataSupport:
    """Tests for TrackerAPIService with full_data and customer field support."""

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

    def test_extract_task_data_includes_customer_field(self, service):
        """Test that extract_task_data extracts customer field from task data."""
        # Mock task data with customer field
        task_data = {
            "id": "12345",
            "key": "TEST-123",
            "summary": "Test Task",
            "status": {"display": "Open"},
            "createdBy": {"display": "Test Author"},
            "assignee": {"display": "Test Assignee"},
            "businessClient": [{"display": "Test Customer"}],
            "63515d47fe387b7ce7b9fc55--team": "Test Team",
            "63515d47fe387b7ce7b9fc55--prodteam": "Test ProdTeam",
            "63515d47fe387b7ce7b9fc55--profitForecast": "High",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
            "links": [],
        }

        result = service.extract_task_data(task_data)

        # Verify customer field is extracted
        assert result["customer"] == "Test Customer"
        assert result["tracker_id"] == "12345"
        assert result["key"] == "TEST-123"
        assert result["summary"] == "Test Task"

    def test_extract_task_data_handles_missing_customer_field(self, service):
        """Test that extract_task_data handles missing customer field gracefully."""
        # Mock task data without customer field
        task_data = {
            "id": "12345",
            "key": "TEST-123",
            "summary": "Test Task",
            "status": {"display": "Open"},
            "createdBy": {"display": "Test Author"},
            "assignee": {"display": "Test Assignee"},
            "businessClient": None,  # No customer
            "63515d47fe387b7ce7b9fc55--team": "Test Team",
            "63515d47fe387b7ce7b9fc55--prodteam": "Test ProdTeam",
            "63515d47fe387b7ce7b9fc55--profitForecast": "High",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
            "links": [],
        }

        result = service.extract_task_data(task_data)

        # Verify customer field is empty string when missing
        assert result["customer"] == ""
        assert result["tracker_id"] == "12345"
        assert result["key"] == "TEST-123"

    def test_extract_task_data_handles_empty_customer_field(self, service):
        """Test that extract_task_data handles empty customer field gracefully."""
        # Mock task data with empty customer field
        task_data = {
            "id": "12345",
            "key": "TEST-123",
            "summary": "Test Task",
            "status": {"display": "Open"},
            "createdBy": {"display": "Test Author"},
            "assignee": {"display": "Test Assignee"},
            "businessClient": [],  # Empty customer list
            "63515d47fe387b7ce7b9fc55--team": "Test Team",
            "63515d47fe387b7ce7b9fc55--prodteam": "Test ProdTeam",
            "63515d47fe387b7ce7b9fc55--profitForecast": "High",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
            "links": [],
        }

        result = service.extract_task_data(task_data)

        # Verify customer field is empty string when empty
        assert result["customer"] == ""
        assert result["tracker_id"] == "12345"
        assert result["key"] == "TEST-123"

    def test_extract_task_data_handles_multiple_customers(self, service):
        """Test that extract_task_data handles multiple customers correctly."""
        # Mock task data with multiple customers
        task_data = {
            "id": "12345",
            "key": "TEST-123",
            "summary": "Test Task",
            "status": {"display": "Open"},
            "createdBy": {"display": "Test Author"},
            "assignee": {"display": "Test Assignee"},
            "businessClient": [{"display": "Customer 1"}, {"display": "Customer 2"}],
            "63515d47fe387b7ce7b9fc55--team": "Test Team",
            "63515d47fe387b7ce7b9fc55--prodteam": "Test ProdTeam",
            "63515d47fe387b7ce7b9fc55--profitForecast": "High",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
            "links": [],
        }

        result = service.extract_task_data(task_data)

        # Verify multiple customers are joined with comma
        assert result["customer"] == "Customer 1, Customer 2"
        assert result["tracker_id"] == "12345"
        assert result["key"] == "TEST-123"

    def test_extract_task_data_preserves_all_fields(self, service):
        """Test that extract_task_data preserves all existing fields."""
        # Mock task data with all fields
        task_data = {
            "id": "12345",
            "key": "TEST-123",
            "summary": "Test Task",
            "description": "Test Description",
            "status": {"display": "Open"},
            "createdBy": {"display": "Test Author"},
            "assignee": {"display": "Test Assignee"},
            "businessClient": [{"display": "Test Customer"}],
            "63515d47fe387b7ce7b9fc55--team": "Test Team",
            "63515d47fe387b7ce7b9fc55--prodteam": "Test ProdTeam",
            "63515d47fe387b7ce7b9fc55--profitForecast": "High",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
            "links": [{"type": "relates", "direction": "outward"}],
        }

        result = service.extract_task_data(task_data)

        # Verify all fields are preserved
        assert result["tracker_id"] == "12345"
        assert result["key"] == "TEST-123"
        assert result["summary"] == "Test Task"
        assert result["description"] == "Test Description"
        assert result["status"] == "Open"
        assert result["author"] == "Test Author"
        assert result["assignee"] == "Test Assignee"
        assert result["customer"] == "Test Customer"
        assert result["team"] == "Test Team"
        assert result["prodteam"] == "Test ProdTeam"
        assert result["profit_forecast"] == "High"
        assert result["links"] == [{"type": "relates", "direction": "outward"}]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
