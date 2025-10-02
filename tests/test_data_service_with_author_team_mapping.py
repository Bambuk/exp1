"""Tests for DataService with AuthorTeamMappingService integration."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from radiator.commands.models.time_to_market_models import (
    GroupBy,
    StatusMapping,
    TaskData,
)
from radiator.commands.services.author_team_mapping_service import (
    AuthorTeamMappingService,
)
from radiator.commands.services.data_service import DataService


class TestDataServiceWithAuthorTeamMapping:
    """Test cases for DataService with AuthorTeamMappingService integration."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def author_team_mapping_service(self):
        """Create AuthorTeamMappingService with test data."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Александр Тихонов;Корзинка и заказ\n")
            f.write("Александр Черкасов;Каталог\n")
            f.write("Александра Степаненкова;Гео и сервисы\n")
            f.write("Алексей Какурин;Каталог\n")
            f.write("Алексей Красников;Оплаты\n")
            f.write("Алексей Никишанин;\n")  # Empty team
            temp_file = f.name

        try:
            service = AuthorTeamMappingService(temp_file)
            yield service
        finally:
            Path(temp_file).unlink(missing_ok=True)

    @pytest.fixture
    def status_mapping(self):
        """Create test status mapping."""
        return StatusMapping(
            discovery_statuses=["Готова к разработке"],
            done_statuses=["Готово", "Закрыто"],
        )

    def test_data_service_author_grouping(
        self, mock_db, author_team_mapping_service, status_mapping
    ):
        """Test DataService with author grouping (should work as before)."""
        # Mock database query results
        mock_tasks = [
            (1, "CPO-123", "Александр Тихонов", datetime.now(), "Test task 1"),
            (2, "CPO-124", "Александр Черкасов", datetime.now(), "Test task 2"),
        ]

        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = mock_tasks

        mock_db.query.return_value = mock_query

        data_service = DataService(mock_db, author_team_mapping_service)

        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()

        result = data_service.get_tasks_for_period(
            start_date, end_date, GroupBy.AUTHOR, status_mapping, "both"
        )

        assert len(result) == 2
        assert result[0].author == "Александр Тихонов"
        assert result[0].team is None
        assert result[0].group_value == "Александр Тихонов"
        assert result[1].author == "Александр Черкасов"
        assert result[1].team is None
        assert result[1].group_value == "Александр Черкасов"

    def test_data_service_team_grouping(
        self, mock_db, author_team_mapping_service, status_mapping
    ):
        """Test DataService with team grouping using AuthorTeamMappingService."""
        # Mock database query results
        mock_tasks = [
            (1, "CPO-123", "Александр Тихонов", datetime.now(), "Test task 1"),
            (2, "CPO-124", "Александр Черкасов", datetime.now(), "Test task 2"),
            (3, "CPO-125", "Алексей Никишанин", datetime.now(), "Test task 3"),
            (4, "CPO-126", "Неизвестный Автор", datetime.now(), "Test task 4"),
        ]

        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = mock_tasks

        mock_db.query.return_value = mock_query

        data_service = DataService(mock_db, author_team_mapping_service)

        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()

        result = data_service.get_tasks_for_period(
            start_date, end_date, GroupBy.TEAM, status_mapping, "both"
        )

        assert len(result) == 4

        # Check team mapping
        team_mapping = {
            result[0].group_value: result[0].author,
            result[1].group_value: result[1].author,
            result[2].group_value: result[2].author,
            result[3].group_value: result[3].author,
        }

        assert "Корзинка и заказ" in team_mapping
        assert "Каталог" in team_mapping
        assert "Без команды" in team_mapping

        # Check that authors are preserved
        authors = [task.author for task in result]
        assert "Александр Тихонов" in authors
        assert "Александр Черкасов" in authors
        assert "Алексей Никишанин" in authors
        assert "Неизвестный Автор" in authors

    def test_data_service_team_grouping_without_mapping_service(
        self, mock_db, status_mapping
    ):
        """Test DataService with team grouping without AuthorTeamMappingService (should return empty)."""
        data_service = DataService(mock_db, None)  # No mapping service

        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()

        result = data_service.get_tasks_for_period(
            start_date, end_date, GroupBy.TEAM, status_mapping, "both"
        )

        assert result == []

    def test_data_service_team_grouping_empty_team_mapping(
        self, mock_db, status_mapping
    ):
        """Test DataService with team grouping when author has empty team."""
        # Create mapping service with empty team
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("Алексей Никишанин;\n")  # Empty team
            temp_file = f.name

        try:
            author_team_mapping_service = AuthorTeamMappingService(temp_file)

            # Mock database query results
            mock_tasks = [
                (1, "CPO-123", "Алексей Никишанин", datetime.now(), "Test task 1"),
            ]

            mock_query = Mock()
            mock_query.join.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.distinct.return_value = mock_query
            mock_query.all.return_value = mock_tasks

            mock_db.query.return_value = mock_query

            data_service = DataService(mock_db, author_team_mapping_service)

            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now()

            result = data_service.get_tasks_for_period(
                start_date, end_date, GroupBy.TEAM, status_mapping, "both"
            )

            assert len(result) == 1
            assert result[0].author == "Алексей Никишанин"
            assert result[0].team == "Без команды"
            assert result[0].group_value == "Без команды"
        finally:
            Path(temp_file).unlink(missing_ok=True)

    def test_data_service_team_grouping_unknown_author(
        self, mock_db, author_team_mapping_service, status_mapping
    ):
        """Test DataService with team grouping when author is not in mapping."""
        # Mock database query results
        mock_tasks = [
            (1, "CPO-123", "Неизвестный Автор", datetime.now(), "Test task 1"),
        ]

        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = mock_tasks

        mock_db.query.return_value = mock_query

        data_service = DataService(mock_db, author_team_mapping_service)

        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()

        result = data_service.get_tasks_for_period(
            start_date, end_date, GroupBy.TEAM, status_mapping, "both"
        )

        assert len(result) == 1
        assert result[0].author == "Неизвестный Автор"
        assert result[0].team == "Без команды"
        assert result[0].group_value == "Без команды"

    def test_data_service_ttd_metric_type(
        self, mock_db, author_team_mapping_service, status_mapping
    ):
        """Test DataService with TTD metric type."""
        # Mock database query results
        mock_tasks = [
            (1, "CPO-123", "Александр Тихонов", datetime.now(), "Test task 1"),
        ]

        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = mock_tasks

        mock_db.query.return_value = mock_query

        data_service = DataService(mock_db, author_team_mapping_service)

        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()

        result = data_service.get_tasks_for_period(
            start_date, end_date, GroupBy.TEAM, status_mapping, "ttd"
        )

        assert len(result) == 1
        # Verify that the query was called with correct statuses
        mock_query.filter.assert_called()
        # The actual filter call verification would require more complex mocking

    def test_data_service_ttm_metric_type(
        self, mock_db, author_team_mapping_service, status_mapping
    ):
        """Test DataService with TTM metric type."""
        # Mock database query results
        mock_tasks = [
            (1, "CPO-123", "Александр Тихонов", datetime.now(), "Test task 1"),
        ]

        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.distinct.return_value = mock_query
        mock_query.all.return_value = mock_tasks

        mock_db.query.return_value = mock_query

        data_service = DataService(mock_db, author_team_mapping_service)

        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()

        result = data_service.get_tasks_for_period(
            start_date, end_date, GroupBy.TEAM, status_mapping, "ttm"
        )

        assert len(result) == 1
        # Verify that the query was called with correct statuses
        mock_query.filter.assert_called()
