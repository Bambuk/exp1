"""Tests for FULLSTACK links extraction from task data."""

from unittest.mock import MagicMock, Mock

import pytest

from radiator.commands.services.testing_returns_service import TestingReturnsService
from radiator.models.tracker import TrackerTask


class TestFullstackLinksExtraction:
    """Test cases for FULLSTACK links extraction."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.service = TestingReturnsService(self.mock_db)

    def test_extract_fullstack_links_from_task(self):
        """Test: extract FULLSTACK links from task with links data."""
        # Mock task with links
        mock_task = Mock()
        mock_task.links = [
            {
                "type": {"id": "relates"},
                "direction": "inward",
                "object": {"key": "FULLSTACK-123", "queue": {"key": "FULLSTACK"}},
            },
            {
                "type": {"id": "relates"},
                "direction": "inward",
                "object": {"key": "FULLSTACK-456", "queue": {"key": "FULLSTACK"}},
            },
            {
                "type": {"id": "depends"},
                "direction": "inward",
                "object": {"key": "FULLSTACK-789", "queue": {"key": "FULLSTACK"}},
            },
            {
                "type": {"id": "relates"},
                "direction": "outward",
                "object": {"key": "FULLSTACK-999", "queue": {"key": "FULLSTACK"}},
            },
        ]

        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_task
        )

        result = self.service.get_fullstack_links("CPO-123")

        # Should return both inward and outward relates links (not depends)
        assert result == ["FULLSTACK-123", "FULLSTACK-456", "FULLSTACK-999"]

    def test_filter_relates_only(self):
        """Test: only relates links are returned (both directions)."""
        mock_task = Mock()
        mock_task.links = [
            {
                "type": {"id": "relates"},
                "direction": "inward",
                "object": {"key": "FULLSTACK-123", "queue": {"key": "FULLSTACK"}},
            },
            {
                "type": {"id": "relates"},
                "direction": "outward",  # Should be included
                "object": {"key": "FULLSTACK-456", "queue": {"key": "FULLSTACK"}},
            },
            {
                "type": {"id": "depends"},  # Should be ignored (wrong type)
                "direction": "inward",
                "object": {"key": "FULLSTACK-789", "queue": {"key": "FULLSTACK"}},
            },
        ]

        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_task
        )

        result = self.service.get_fullstack_links("CPO-123")

        # Should return both inward and outward relates, but not depends
        assert result == ["FULLSTACK-123", "FULLSTACK-456"]

    def test_no_fullstack_links_returns_empty(self):
        """Test: task with no FULLSTACK links returns empty list."""
        mock_task = Mock()
        mock_task.links = [
            {
                "type": {"id": "relates"},
                "direction": "inward",
                "object": {"key": "CPO-456", "queue": {"key": "CPO"}},
            },
            {
                "type": {"id": "relates"},
                "direction": "inward",
                "object": {"key": "BACKEND-789", "queue": {"key": "BACKEND"}},
            },
        ]

        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_task
        )

        result = self.service.get_fullstack_links("CPO-123")

        assert result == []

    def test_links_field_missing_returns_empty(self):
        """Test: task with no links field returns empty list."""
        mock_task = Mock()
        mock_task.links = None

        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_task
        )

        result = self.service.get_fullstack_links("CPO-123")

        assert result == []

    def test_task_not_found_returns_empty(self):
        """Test: task not found in database returns empty list."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = None

        result = self.service.get_fullstack_links("CPO-123")

        assert result == []

    def test_empty_links_list_returns_empty(self):
        """Test: task with empty links list returns empty list."""
        mock_task = Mock()
        mock_task.links = []

        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_task
        )

        result = self.service.get_fullstack_links("CPO-123")

        assert result == []

    def test_malformed_links_handled_gracefully(self):
        """Test: malformed links are handled gracefully."""
        mock_task = Mock()
        mock_task.links = [
            {
                "type": {"id": "relates"},
                "direction": "inward",
                "object": {"key": "FULLSTACK-123", "queue": {"key": "FULLSTACK"}},
            },
            {
                # Missing required fields
                "type": {"id": "relates"},
                "direction": "inward",
            },
            {
                "type": {"id": "relates"},
                "direction": "inward",
                "object": {"key": "FULLSTACK-456", "queue": {"key": "FULLSTACK"}},
            },
            None,  # None entry
            {},  # Empty dict
        ]

        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_task
        )

        result = self.service.get_fullstack_links("CPO-123")

        # Should only return valid links
        assert result == ["FULLSTACK-123", "FULLSTACK-456"]

    def test_database_error_handled_gracefully(self):
        """Test: database error is handled gracefully."""
        self.mock_db.query.return_value.filter.return_value.first.side_effect = (
            Exception("Database error")
        )

        result = self.service.get_fullstack_links("CPO-123")

        assert result == []

    def test_mixed_queue_types_filtered_correctly(self):
        """Test: only FULLSTACK queue links are returned."""
        mock_task = Mock()
        mock_task.links = [
            {
                "type": {"id": "relates"},
                "direction": "inward",
                "object": {"key": "FULLSTACK-123", "queue": {"key": "FULLSTACK"}},
            },
            {
                "type": {"id": "relates"},
                "direction": "inward",
                "object": {"key": "BACKEND-456", "queue": {"key": "BACKEND"}},
            },
            {
                "type": {"id": "relates"},
                "direction": "inward",
                "object": {"key": "FRONTEND-789", "queue": {"key": "FRONTEND"}},
            },
        ]

        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_task
        )

        result = self.service.get_fullstack_links("CPO-123")

        assert result == ["FULLSTACK-123"]
