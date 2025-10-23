"""Tests for DataService filtering functionality."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from radiator.commands.models.time_to_market_models import StatusHistoryEntry
from radiator.commands.services.author_team_mapping_service import (
    AuthorTeamMappingService,
)
from radiator.commands.services.data_service import DataService


class TestDataServiceFiltering:
    """Test filtering of short status transitions in DataService."""

    def test_get_task_history_filters_short_transitions(self):
        """Test that get_task_history filters out statuses shorter than 5 minutes."""
        # Arrange
        mock_db = Mock()
        mock_author_team_mapping = Mock(spec=AuthorTeamMappingService)
        data_service = DataService(mock_db, mock_author_team_mapping)

        # Mock database query result with short transitions
        # The algorithm checks duration from start_date to next entry's start_date
        start_time = datetime(2025, 1, 1, 10, 0, 0)
        short_transition_time = start_time + timedelta(seconds=30)  # 30 seconds later
        very_short_time = start_time + timedelta(seconds=60)  # 1 minute later
        long_transition_time = start_time + timedelta(minutes=10)  # 10 minutes later

        mock_history_data = [
            ("Идея", "Идея", start_time, short_transition_time),  # 30 seconds duration
            (
                "Готова к разработке",
                "Готова к разработке",
                short_transition_time,
                very_short_time,
            ),  # 30 seconds duration (SHORT!)
            (
                "Выполнено",
                "Выполнено",
                very_short_time,
                long_transition_time,
            ),  # 9 minutes duration
            ("Done", "Done", long_transition_time, None),  # Last status
        ]

        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = (
            mock_history_data
        )
        mock_db.query.return_value = mock_query

        # Act
        result = data_service.get_task_history(123)

        # Assert
        assert (
            len(result) == 3
        )  # First entry + long transition + last status (short one filtered)
        assert result[0].status == "Идея"
        assert (
            result[1].status == "Выполнено"
        )  # Short "Готова к разработке" filtered out
        assert result[2].status == "Done"  # Last status preserved

    def test_get_task_history_by_key_filters_short_transitions(self):
        """Test that get_task_history_by_key filters out statuses shorter than 5 minutes."""
        # Arrange
        mock_db = Mock()
        mock_author_team_mapping = Mock(spec=AuthorTeamMappingService)
        data_service = DataService(mock_db, mock_author_team_mapping)

        # Mock database query result with short transitions
        # The algorithm checks duration from start_date to next entry's start_date
        start_time = datetime(2025, 1, 1, 10, 0, 0)
        short_transition_time = start_time + timedelta(seconds=30)  # 30 seconds later
        very_short_time = start_time + timedelta(seconds=60)  # 1 minute later
        long_transition_time = start_time + timedelta(minutes=10)  # 10 minutes later

        mock_history_data = [
            ("Идея", "Идея", start_time, short_transition_time),  # 30 seconds duration
            (
                "Готова к разработке",
                "Готова к разработке",
                short_transition_time,
                very_short_time,
            ),  # 30 seconds duration (SHORT!)
            (
                "Выполнено",
                "Выполнено",
                very_short_time,
                long_transition_time,
            ),  # 9 minutes duration
            ("Done", "Done", long_transition_time, None),  # Last status
        ]

        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = (
            mock_history_data
        )
        mock_db.query.return_value = mock_query

        # Act
        result = data_service.get_task_history_by_key("CPO-123")

        # Assert
        assert (
            len(result) == 3
        )  # First entry + long transition + last status (short one filtered)
        assert result[0].status == "Идея"
        assert (
            result[1].status == "Выполнено"
        )  # Short "Готова к разработке" filtered out
        assert result[2].status == "Done"  # Last status preserved

    def test_last_status_always_preserved_even_if_short(self):
        """Test that the last status is always preserved even if it's short."""
        # Arrange
        mock_db = Mock()
        mock_author_team_mapping = Mock(spec=AuthorTeamMappingService)
        data_service = DataService(mock_db, mock_author_team_mapping)

        # Mock database query result with short last status
        start_time = datetime(2025, 1, 1, 10, 0, 0)
        short_last_time = start_time + timedelta(minutes=10)

        mock_history_data = [
            (
                "Идея",
                "Идея",
                start_time,
                start_time + timedelta(minutes=10),
            ),  # Long transition
            (
                "Выполнено",
                "Выполнено",
                short_last_time,
                short_last_time + timedelta(seconds=30),
            ),  # Short last status
        ]

        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = (
            mock_history_data
        )
        mock_db.query.return_value = mock_query

        # Act
        result = data_service.get_task_history(123)

        # Assert
        assert len(result) == 2  # Both entries preserved
        assert result[0].status == "Идея"
        assert (
            result[1].status == "Выполнено"
        )  # Last status preserved despite being short

    def test_first_status_always_preserved(self):
        """Test that the first status (creation) is always preserved."""
        # Arrange
        mock_db = Mock()
        mock_author_team_mapping = Mock(spec=AuthorTeamMappingService)
        data_service = DataService(mock_db, mock_author_team_mapping)

        # Mock database query result with only short transitions
        start_time = datetime(2025, 1, 1, 10, 0, 0)
        short_transition_time = start_time + timedelta(seconds=30)  # 30 seconds later
        very_short_time = start_time + timedelta(seconds=60)  # 1 minute later

        mock_history_data = [
            ("Идея", "Идея", start_time, short_transition_time),  # 30 seconds duration
            (
                "Готова к разработке",
                "Готова к разработке",
                short_transition_time,
                very_short_time,
            ),  # 30 seconds duration (SHORT!)
        ]

        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = (
            mock_history_data
        )
        mock_db.query.return_value = mock_query

        # Act
        result = data_service.get_task_history(123)

        # Assert
        assert (
            len(result) == 2
        )  # First entry + last entry (last is always kept even if short)
        assert result[0].status == "Идея"
        assert result[1].status == "Готова к разработке"  # Last entry always preserved

    def test_long_statuses_not_filtered(self):
        """Test that statuses longer than 5 minutes are not filtered."""
        # Arrange
        mock_db = Mock()
        mock_author_team_mapping = Mock(spec=AuthorTeamMappingService)
        data_service = DataService(mock_db, mock_author_team_mapping)

        # Mock database query result with only long transitions
        start_time = datetime(2025, 1, 1, 10, 0, 0)

        mock_history_data = [
            (
                "Идея",
                "Идея",
                start_time,
                start_time + timedelta(minutes=10),
            ),  # 10 minutes
            (
                "Готова к разработке",
                "Готова к разработке",
                start_time + timedelta(minutes=10),
                start_time + timedelta(minutes=20),
            ),  # 10 minutes
            (
                "Выполнено",
                "Выполнено",
                start_time + timedelta(minutes=20),
                None,
            ),  # Last status
        ]

        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = (
            mock_history_data
        )
        mock_db.query.return_value = mock_query

        # Act
        result = data_service.get_task_history(123)

        # Assert
        assert len(result) == 3  # All entries preserved
        assert result[0].status == "Идея"
        assert result[1].status == "Готова к разработке"
        assert result[2].status == "Выполнено"

    def test_empty_history_returns_empty_list(self):
        """Test that empty history returns empty list."""
        # Arrange
        mock_db = Mock()
        mock_author_team_mapping = Mock(spec=AuthorTeamMappingService)
        data_service = DataService(mock_db, mock_author_team_mapping)

        # Mock empty database query result
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
        mock_db.query.return_value = mock_query

        # Act
        result = data_service.get_task_history(123)

        # Assert
        assert result == []

    def test_database_error_returns_empty_list(self):
        """Test that database errors return empty list."""
        # Arrange
        mock_db = Mock()
        mock_author_team_mapping = Mock(spec=AuthorTeamMappingService)
        data_service = DataService(mock_db, mock_author_team_mapping)

        # Mock database error
        mock_db.query.side_effect = Exception("Database error")

        # Act
        result = data_service.get_task_history(123)

        # Assert
        assert result == []
        mock_db.rollback.assert_called_once()
