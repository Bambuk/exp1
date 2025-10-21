"""Tests for TrackerAPIService JSONB data extraction methods."""

from unittest.mock import Mock, patch

import pytest

from radiator.services.tracker_service import TrackerAPIService


class TestTrackerAPIServiceJSONBExtraction:
    """Tests for TrackerAPIService JSONB data extraction methods."""

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

    def test_extract_field_from_full_data_success(self, service):
        """Test extracting a field from full_data JSONB."""
        # Mock full_data JSONB
        full_data = {
            "id": "12345",
            "key": "TEST-123",
            "summary": "Test Task",
            "status": {"display": "Open"},
            "customer": "Test Customer",
            "assignee": {"display": "Test Assignee"},
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
        }

        # Test extracting different fields
        assert service.extract_field_from_full_data(full_data, "id") == "12345"
        assert service.extract_field_from_full_data(full_data, "key") == "TEST-123"
        assert service.extract_field_from_full_data(full_data, "summary") == "Test Task"
        assert (
            service.extract_field_from_full_data(full_data, "customer")
            == "Test Customer"
        )

    def test_extract_field_from_full_data_nested_field(self, service):
        """Test extracting nested fields from full_data JSONB."""
        # Mock full_data JSONB with nested fields
        full_data = {
            "id": "12345",
            "status": {"display": "Open", "key": "open"},
            "assignee": {"display": "Test Assignee", "id": "user123"},
            "createdBy": {"display": "Test Author", "id": "author123"},
        }

        # Test extracting nested fields
        assert (
            service.extract_field_from_full_data(full_data, "status.display") == "Open"
        )
        assert service.extract_field_from_full_data(full_data, "status.key") == "open"
        assert (
            service.extract_field_from_full_data(full_data, "assignee.display")
            == "Test Assignee"
        )
        assert (
            service.extract_field_from_full_data(full_data, "assignee.id") == "user123"
        )

    def test_extract_field_from_full_data_missing_field(self, service):
        """Test extracting missing fields from full_data JSONB."""
        # Mock full_data JSONB
        full_data = {"id": "12345", "key": "TEST-123", "summary": "Test Task"}

        # Test extracting missing fields
        assert service.extract_field_from_full_data(full_data, "customer") is None
        assert service.extract_field_from_full_data(full_data, "assignee") is None
        assert service.extract_field_from_full_data(full_data, "nonexistent") is None

    def test_extract_field_from_full_data_none_full_data(self, service):
        """Test extracting fields when full_data is None."""
        # Test with None full_data
        assert service.extract_field_from_full_data(None, "id") is None
        assert service.extract_field_from_full_data(None, "key") is None

    def test_extract_field_from_full_data_empty_full_data(self, service):
        """Test extracting fields when full_data is empty."""
        # Test with empty full_data
        assert service.extract_field_from_full_data({}, "id") is None
        assert service.extract_field_from_full_data({}, "key") is None

    def test_extract_multiple_fields_from_full_data(self, service):
        """Test extracting multiple fields from full_data JSONB."""
        # Mock full_data JSONB
        full_data = {
            "id": "12345",
            "key": "TEST-123",
            "summary": "Test Task",
            "status": {"display": "Open"},
            "customer": "Test Customer",
            "assignee": {"display": "Test Assignee"},
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
        }

        # Test extracting multiple fields
        fields = [
            "id",
            "key",
            "summary",
            "customer",
            "status.display",
            "assignee.display",
        ]
        result = service.extract_multiple_fields_from_full_data(full_data, fields)

        expected = {
            "id": "12345",
            "key": "TEST-123",
            "summary": "Test Task",
            "customer": "Test Customer",
            "status.display": "Open",
            "assignee.display": "Test Assignee",
        }

        assert result == expected

    def test_extract_multiple_fields_from_full_data_with_missing_fields(self, service):
        """Test extracting multiple fields with some missing fields."""
        # Mock full_data JSONB
        full_data = {"id": "12345", "key": "TEST-123", "summary": "Test Task"}

        # Test extracting multiple fields with some missing
        fields = ["id", "key", "summary", "customer", "assignee.display"]
        result = service.extract_multiple_fields_from_full_data(full_data, fields)

        expected = {
            "id": "12345",
            "key": "TEST-123",
            "summary": "Test Task",
            "customer": None,
            "assignee.display": None,
        }

        assert result == expected

    def test_extract_multiple_fields_from_full_data_none_full_data(self, service):
        """Test extracting multiple fields when full_data is None."""
        # Test with None full_data
        fields = ["id", "key", "summary"]
        result = service.extract_multiple_fields_from_full_data(None, fields)

        expected = {"id": None, "key": None, "summary": None}

        assert result == expected

    def test_get_task_data_from_full_data(self, service):
        """Test getting complete task data from full_data JSONB."""
        # Mock full_data JSONB
        full_data = {
            "id": "12345",
            "key": "TEST-123",
            "summary": "Test Task",
            "description": "Test Description",
            "status": {"display": "Open"},
            "businessClient": [
                {"display": "Test Customer"}
            ],  # Correct format for customer
            "assignee": {"display": "Test Assignee"},
            "createdBy": {"display": "Test Author"},
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
            "links": [{"type": "relates", "direction": "outward"}],
        }

        # Test getting complete task data
        result = service.get_task_data_from_full_data(full_data)

        # Verify all fields are extracted correctly
        assert result["tracker_id"] == "12345"
        assert result["key"] == "TEST-123"
        assert result["summary"] == "Test Task"
        assert result["description"] == "Test Description"
        assert result["status"] == "Open"
        assert result["customer"] == "Test Customer"
        assert result["assignee"] == "Test Assignee"
        assert result["author"] == "Test Author"
        assert result["links"] == [{"type": "relates", "direction": "outward"}]

    def test_get_task_data_from_full_data_none_full_data(self, service):
        """Test getting task data when full_data is None."""
        # Test with None full_data
        result = service.get_task_data_from_full_data(None)

        # Should return empty dict or None
        assert result is None or result == {}

    def test_get_task_data_from_full_data_empty_full_data(self, service):
        """Test getting task data when full_data is empty."""
        # Test with empty full_data
        result = service.get_task_data_from_full_data({})

        # Should return empty dict or None
        assert result is None or result == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
