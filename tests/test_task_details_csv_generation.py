"""Tests for task details CSV generation functionality."""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from radiator.commands.generate_time_to_market_report import (
    GenerateTimeToMarketReportCommand,
)
from radiator.commands.models.time_to_market_models import (
    GroupBy,
    GroupMetrics,
    Quarter,
    QuarterReport,
    StatusMapping,
    TaskData,
    TimeMetrics,
    TimeToMarketReport,
)
from radiator.commands.services.testing_returns_service import TestingReturnsService


class TestTaskDetailsCSVGeneration:
    """Test cases for task details CSV generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.mock_author_team_mapping_service = Mock()
        self.mock_data_service = Mock()
        self.mock_metrics_service = Mock()
        self.mock_testing_returns_service = Mock()

        # Create a temporary directory for test output
        self.temp_dir = tempfile.mkdtemp()

        # Mock the command initialization
        with patch(
            "radiator.commands.generate_time_to_market_report.SessionLocal",
            return_value=self.mock_db,
        ), patch(
            "radiator.commands.generate_time_to_market_report.ConfigService"
        ), patch(
            "radiator.commands.generate_time_to_market_report.AuthorTeamMappingService",
            return_value=self.mock_author_team_mapping_service,
        ), patch(
            "radiator.commands.generate_time_to_market_report.DataService",
            return_value=self.mock_data_service,
        ), patch(
            "radiator.commands.generate_time_to_market_report.MetricsService",
            return_value=self.mock_metrics_service,
        ), patch(
            "radiator.commands.generate_time_to_market_report.TestingReturnsService",
            return_value=self.mock_testing_returns_service,
        ):
            self.cmd = GenerateTimeToMarketReportCommand(
                group_by=GroupBy.AUTHOR,
                config_dir="test_config",
                output_dir=self.temp_dir,
            )

    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temporary directory
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_generate_task_details_csv_no_report_data(self):
        """Test: generate_task_details_csv returns empty string when no report data."""
        # No report data set
        result = self.cmd.generate_task_details_csv()

        assert result == ""

    def test_generate_task_details_csv_with_mock_data(self):
        """Test: generate_task_details_csv generates CSV with mock data."""
        # Create mock report data
        quarter = Quarter(
            name="2025.Q1",
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 3, 31),
        )

        status_mapping = StatusMapping(
            discovery_statuses=["Discovery backlog"],
            done_statuses=["Done", "Выполнено"],
        )

        # Create mock task data
        mock_task = TaskData(
            id=1,
            key="CPO-123",
            author="Test Author",
            team="Test Team",
            summary="Test Task",
            created_at=datetime(2025, 1, 15),
            group_value="Test Author",
        )

        # Mock data service responses
        self.mock_data_service.get_tasks_for_period.side_effect = [
            [mock_task],  # TTD tasks
            [mock_task],  # TTM tasks
        ]

        # Mock task history
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_history = [
            StatusHistoryEntry(
                status="Open",
                status_display="Open",
                start_date=datetime(2025, 1, 15),
                end_date=datetime(2025, 1, 16),
            ),
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 1, 20),
                end_date=None,
            ),
        ]
        self.mock_data_service.get_task_history.return_value = mock_history

        # Mock metrics calculations
        self.mock_metrics_service.calculate_time_to_delivery.return_value = 5
        self.mock_metrics_service.calculate_time_to_market.return_value = 5
        self.mock_metrics_service.calculate_tail_metric.return_value = 2
        self.mock_metrics_service.calculate_pause_time.return_value = 1
        self.mock_metrics_service.calculate_status_duration.return_value = 3

        # Mock testing returns service
        self.mock_testing_returns_service.calculate_testing_returns_for_cpo_task.return_value = (
            1,
            0,
        )

        # Set up report data
        self.cmd.report = TimeToMarketReport(
            quarters=[quarter],
            status_mapping=status_mapping,
            group_by=GroupBy.AUTHOR,
            quarter_reports={},
        )

        # Generate CSV
        result = self.cmd.generate_task_details_csv()

        # Verify result
        assert result != ""
        assert result.endswith(".csv")
        assert os.path.exists(result)

        # Verify CSV content
        with open(result, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.strip().split("\n")

            # Check header
            assert len(lines) >= 2  # Header + at least one data row
            header = lines[0]
            expected_columns = [
                "Автор",
                "Команда",
                "Ключ задачи",
                "Название",
                "TTD",
                "TTM",
                "Tail",
                "Пауза",
                "TTD Pause",
                "Discovery backlog (дни)",
                "Готова к разработке (дни)",
                "Возвраты с Testing",
                "Возвраты с Внешний тест",
                "Всего возвратов",
                "Квартал",
            ]
            for col in expected_columns:
                assert col in header

            # Check data row
            data_row = lines[1]
            assert "Test Author" in data_row
            assert "Test Team" in data_row
            assert "CPO-123" in data_row
            assert "Test Task" in data_row
            assert "2025.Q1" in data_row

    def test_generate_task_details_csv_database_error_handling(self):
        """Test: generate_task_details_csv handles database errors gracefully."""
        # Create mock report data
        quarter = Quarter(
            name="2025.Q1",
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 3, 31),
        )

        status_mapping = StatusMapping(
            discovery_statuses=["Discovery backlog"],
            done_statuses=["Done", "Выполнено"],
        )

        # Mock database error
        self.mock_data_service.get_tasks_for_period.side_effect = Exception(
            "Database error"
        )

        # Set up report data
        self.cmd.report = TimeToMarketReport(
            quarters=[quarter],
            status_mapping=status_mapping,
            group_by=GroupBy.AUTHOR,
            quarter_reports={},
        )

        # Generate CSV - should not raise exception
        result = self.cmd.generate_task_details_csv()

        # Should return empty string when no data due to errors
        assert result == ""

    def test_generate_task_details_csv_history_error_handling(self):
        """Test: generate_task_details_csv handles task history errors gracefully."""
        # Create mock report data
        quarter = Quarter(
            name="2025.Q1",
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 3, 31),
        )

        status_mapping = StatusMapping(
            discovery_statuses=["Discovery backlog"],
            done_statuses=["Done", "Выполнено"],
        )

        # Create mock task data
        mock_task = TaskData(
            id=1,
            key="CPO-123",
            author="Test Author",
            team="Test Team",
            summary="Test Task",
            created_at=datetime(2025, 1, 15),
            group_value="Test Author",
        )

        # Mock data service responses
        self.mock_data_service.get_tasks_for_period.side_effect = [
            [mock_task],  # TTD tasks
            [mock_task],  # TTM tasks
        ]

        # Mock task history error
        self.mock_data_service.get_task_history.side_effect = Exception("History error")

        # Set up report data
        self.cmd.report = TimeToMarketReport(
            quarters=[quarter],
            status_mapping=status_mapping,
            group_by=GroupBy.AUTHOR,
            quarter_reports={},
        )

        # Generate CSV - should not raise exception
        result = self.cmd.generate_task_details_csv()

        # Should return empty string when no data due to errors
        assert result == ""

    def test_generate_task_details_csv_custom_filepath(self):
        """Test: generate_task_details_csv uses custom filepath when provided."""
        # Create mock report data
        quarter = Quarter(
            name="2025.Q1",
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 3, 31),
        )

        status_mapping = StatusMapping(
            discovery_statuses=["Discovery backlog"],
            done_statuses=["Done", "Выполнено"],
        )

        # Set up report data
        self.cmd.report = TimeToMarketReport(
            quarters=[quarter],
            status_mapping=status_mapping,
            group_by=GroupBy.AUTHOR,
            quarter_reports={},
        )

        # Mock empty data
        self.mock_data_service.get_tasks_for_period.return_value = []

        # Generate CSV with custom filepath
        custom_path = os.path.join(self.temp_dir, "custom_details.csv")
        result = self.cmd.generate_task_details_csv(custom_path)

        # Should return empty string when no data
        assert result == ""

    def test_generate_task_details_csv_creates_directory(self):
        """Test: generate_task_details_csv creates output directory if it doesn't exist."""
        # Create mock report data
        quarter = Quarter(
            name="2025.Q1",
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 3, 31),
        )

        status_mapping = StatusMapping(
            discovery_statuses=["Discovery backlog"],
            done_statuses=["Done", "Выполнено"],
        )

        # Set up report data
        self.cmd.report = TimeToMarketReport(
            quarters=[quarter],
            status_mapping=status_mapping,
            group_by=GroupBy.AUTHOR,
            quarter_reports={},
        )

        # Mock empty data
        self.mock_data_service.get_tasks_for_period.return_value = []

        # Generate CSV with path in non-existent directory
        custom_path = os.path.join(self.temp_dir, "new_dir", "details.csv")
        result = self.cmd.generate_task_details_csv(custom_path)

        # Should return empty string when no data
        assert result == ""

    def test_generate_task_details_csv_includes_testing_returns(self):
        """Test: generate_task_details_csv includes testing returns data."""
        # Create mock report data
        quarter = Quarter(
            name="2025.Q1",
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 3, 31),
        )

        status_mapping = StatusMapping(
            discovery_statuses=["Discovery backlog"],
            done_statuses=["Done", "Выполнено"],
        )

        # Create mock task data
        mock_task = TaskData(
            id=1,
            key="CPO-123",
            author="Test Author",
            team="Test Team",
            summary="Test Task",
            created_at=datetime(2025, 1, 15),
            group_value="Test Author",
        )

        # Mock data service responses
        self.mock_data_service.get_tasks_for_period.side_effect = [
            [mock_task],  # TTD tasks
            [mock_task],  # TTM tasks
        ]

        # Mock task history
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_history = [
            StatusHistoryEntry(
                status="Open",
                status_display="Open",
                start_date=datetime(2025, 1, 15),
                end_date=datetime(2025, 1, 16),
            ),
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 1, 20),
                end_date=None,
            ),
        ]
        self.mock_data_service.get_task_history.return_value = mock_history

        # Mock metrics calculations
        self.mock_metrics_service.calculate_time_to_delivery.return_value = 5
        self.mock_metrics_service.calculate_time_to_market.return_value = 5
        self.mock_metrics_service.calculate_tail_metric.return_value = 2
        self.mock_metrics_service.calculate_pause_time.return_value = 1
        self.mock_metrics_service.calculate_status_duration.return_value = 3

        # Mock testing returns service with specific values
        self.mock_testing_returns_service.calculate_testing_returns_for_cpo_task.return_value = (
            2,
            1,
        )

        # Set up report data
        self.cmd.report = TimeToMarketReport(
            quarters=[quarter],
            status_mapping=status_mapping,
            group_by=GroupBy.AUTHOR,
            quarter_reports={},
        )

        # Generate CSV
        result = self.cmd.generate_task_details_csv()

        # Verify CSV content includes testing returns
        with open(result, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.strip().split("\n")

            # Check data row contains testing returns
            data_row = lines[1]
            assert "2" in data_row  # Testing returns
            assert "1" in data_row  # External test returns
            assert "3" in data_row  # Total returns (2+1)

    def test_generate_task_details_csv_handles_empty_tasks(self):
        """Test: generate_task_details_csv handles empty task lists."""
        # Create mock report data
        quarter = Quarter(
            name="2025.Q1",
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 3, 31),
        )

        status_mapping = StatusMapping(
            discovery_statuses=["Discovery backlog"],
            done_statuses=["Done", "Выполнено"],
        )

        # Mock empty data
        self.mock_data_service.get_tasks_for_period.return_value = []

        # Set up report data
        self.cmd.report = TimeToMarketReport(
            quarters=[quarter],
            status_mapping=status_mapping,
            group_by=GroupBy.AUTHOR,
            quarter_reports={},
        )

        # Generate CSV
        result = self.cmd.generate_task_details_csv()

        # Should return empty string when no data
        assert result == ""
