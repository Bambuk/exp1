#!/usr/bin/env python3
"""Tests for automatic scroll detection based on X-Total-Count."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from radiator.services.tracker_service import TrackerAPIService


class TestShouldUseScroll:
    """Tests for should_use_scroll method."""

    def test_should_use_scroll_returns_true_when_count_is_10000(self):
        """Should return True when X-Total-Count is exactly 10000."""
        service = TrackerAPIService()

        with patch.object(service, "get_total_tasks_count", return_value=10000):
            result = service.should_use_scroll("Queue: FULLSTACK")
            assert result is True

    def test_should_use_scroll_returns_true_when_count_greater_than_10000(self):
        """Should return True when X-Total-Count is greater than 10000."""
        service = TrackerAPIService()

        with patch.object(service, "get_total_tasks_count", return_value=15000):
            result = service.should_use_scroll("Queue: FULLSTACK")
            assert result is True

    def test_should_use_scroll_returns_false_when_count_less_than_10000(self):
        """Should return False when X-Total-Count is less than 10000."""
        service = TrackerAPIService()

        with patch.object(service, "get_total_tasks_count", return_value=6541):
            result = service.should_use_scroll("Queue: CPO")
            assert result is False

    def test_should_use_scroll_returns_true_on_error(self):
        """Should return True when get_total_tasks_count raises an exception."""
        service = TrackerAPIService()

        with patch.object(
            service, "get_total_tasks_count", side_effect=Exception("API Error")
        ):
            with patch("radiator.services.tracker_service.logger") as mock_logger:
                result = service.should_use_scroll("Queue: FULLSTACK")
                assert result is True
                mock_logger.warning.assert_called_once()


class TestAutoPaginationSelection:
    """Tests for automatic pagination method selection."""

    def test_auto_uses_scroll_when_total_count_is_10000(self):
        """Should use scroll when X-Total-Count is 10000."""
        service = TrackerAPIService()

        with patch.object(
            service, "should_use_scroll", return_value=True
        ) as mock_should_use_scroll:
            with patch.object(
                service, "_search_tasks_with_scroll", return_value=["task1", "task2"]
            ) as mock_scroll:
                result = service.search_tasks_with_data("Queue: FULLSTACK", limit=None)

                mock_should_use_scroll.assert_called_once_with("Queue: FULLSTACK")
                mock_scroll.assert_called_once_with(
                    "Queue: FULLSTACK",
                    limit=999999,
                    extract_full_data=True,
                    expand=None,
                )
                assert result == ["task1", "task2"]

    def test_auto_uses_v2_when_total_count_less_than_10000(self):
        """Should use v2 pagination when X-Total-Count is less than 10000."""
        service = TrackerAPIService()

        with patch.object(
            service, "should_use_scroll", return_value=False
        ) as mock_should_use_scroll:
            with patch.object(
                service, "get_total_tasks_count", return_value=6541
            ) as mock_get_count:
                # Mock the v2 pagination by patching the internal logic
                with patch.object(service, "_make_request") as mock_request:
                    # Mock successful v2 response
                    mock_response = Mock()
                    mock_response.json.return_value = [{"id": "task1"}, {"id": "task2"}]
                    mock_response.headers = {"X-Total-Count": "6541"}
                    mock_request.return_value = mock_response

                    result = service.search_tasks_with_data("Queue: CPO", limit=None)

                    mock_should_use_scroll.assert_called_once_with("Queue: CPO")
                    mock_get_count.assert_called_once_with("Queue: CPO")
                    # Should call v2 API with calculated limit - check that it was called
                    assert mock_request.called
                    # Result should contain some data
                    assert len(result) > 0

    def test_explicit_limit_overrides_auto_detection(self):
        """Should use explicit limit and ignore auto detection."""
        service = TrackerAPIService()

        # Should not call should_use_scroll when limit is explicitly provided
        with patch.object(service, "should_use_scroll") as mock_should_use_scroll:
            with patch.object(service, "_make_request") as mock_request:
                # Mock successful v2 response
                mock_response = Mock()
                mock_response.json.return_value = [{"id": "task1"}]
                mock_response.headers = {"X-Total-Count": "100"}
                mock_request.return_value = mock_response

                result = service.search_tasks_with_data("Queue: CPO", limit=100)

                mock_should_use_scroll.assert_not_called()
                # Should call v2 API with explicit limit - check that it was called
                assert mock_request.called
                # Result should contain some data
                assert len(result) > 0


class TestScrollCompletion:
    """Tests for scroll completion behavior."""

    def test_scroll_stops_when_no_more_data(self):
        """Scroll should stop when receiving empty response."""
        service = TrackerAPIService()

        # Mock first response with data
        first_response = Mock()
        first_response.json.return_value = [{"id": "task1"}, {"id": "task2"}]
        first_response.headers = {"X-Scroll-Id": "scroll123"}

        # Mock second response with empty data
        second_response = Mock()
        second_response.json.return_value = []
        second_response.headers = {"X-Scroll-Id": None}

        with patch.object(
            service, "_make_request", side_effect=[first_response, second_response]
        ):
            with patch("radiator.services.tracker_service.logger") as mock_logger:
                result = service._search_tasks_with_scroll(
                    "Queue: FULLSTACK", limit=1000, extract_full_data=False
                )

                # Should stop after second empty response
                assert len(result) == 2
                assert result == ["task1", "task2"]
                # Check that the completion log was called
                mock_logger.info.assert_any_call(
                    "Scroll завершен: получен пустой ответ"
                )

    def test_scroll_stops_when_no_scroll_id(self):
        """Scroll should stop when no new scroll ID is provided."""
        service = TrackerAPIService()

        # Mock response with data but no scroll ID
        response = Mock()
        response.json.return_value = [{"id": "task1"}, {"id": "task2"}]
        response.headers = {"X-Scroll-Id": None}

        with patch.object(service, "_make_request", return_value=response):
            with patch("radiator.services.tracker_service.logger") as mock_logger:
                result = service._search_tasks_with_scroll(
                    "Queue: FULLSTACK", limit=1000, extract_full_data=False
                )

                assert len(result) == 2
                assert result == ["task1", "task2"]
                # Check that the completion log was called
                mock_logger.info.assert_any_call(
                    "Scroll завершен: нет больше scroll ID"
                )


class TestIntegration:
    """Integration tests for large queue handling."""

    def test_get_all_tasks_from_large_queue(self):
        """Should get all tasks from a large queue using scroll."""
        service = TrackerAPIService()

        # Mock that should_use_scroll returns True for large queue
        with patch.object(service, "should_use_scroll", return_value=True):
            with patch.object(
                service,
                "_search_tasks_with_scroll",
                return_value=["task1", "task2", "task3"],
            ) as mock_scroll:
                result = service.search_tasks_with_data("Queue: FULLSTACK", limit=None)

                mock_scroll.assert_called_once_with(
                    "Queue: FULLSTACK",
                    limit=999999,
                    extract_full_data=True,
                    expand=None,
                )
                assert len(result) == 3

    def test_scroll_ttl_fix(self):
        """Should use correct scrollTTLMillis value (60000 instead of 300000)."""
        service = TrackerAPIService()

        with patch.object(service, "_make_request") as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_response.headers = {"X-Scroll-Id": None}
            mock_request.return_value = mock_response

            service._search_tasks_with_scroll("Queue: FULLSTACK", limit=1000)

            # Check that correct TTL was used
            calls = mock_request.call_args_list
            assert len(calls) >= 1

            # First call should have scrollTTLMillis: 60000
            first_call = calls[0]
            call_kwargs = first_call[1]
            params = call_kwargs.get("params", {})
            assert params.get("scrollTTLMillis") == 60000
