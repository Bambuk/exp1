"""Integration tests for full report generation including task details CSV."""

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
    StatusHistoryEntry,
    StatusMapping,
    TaskData,
    TimeMetrics,
    TimeToMarketReport,
)


class TestFullReportGenerationIntegration:
    """Integration tests for full report generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Mock database and services
        self.mock_db = Mock()
        self.mock_author_team_mapping_service = Mock()
        self.mock_data_service = Mock()
        self.mock_metrics_service = Mock()
        self.mock_testing_returns_service = Mock()

        # Mock config service
        self.mock_config_service = Mock()
        self.mock_config_service.load_quarters.return_value = [
            Quarter(
                name="2025.Q1",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 3, 31),
            )
        ]
        self.mock_config_service.load_status_mapping.return_value = StatusMapping(
            discovery_statuses=["Discovery backlog"],
            done_statuses=["Done", "Выполнено"],
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_full_report_generation_with_mock_data(self):
        """Test: full report generation works with mock data."""
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

        # Mock task history
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

        # Mock data service responses
        self.mock_data_service.get_tasks_for_period.return_value = [mock_task]
        self.mock_data_service.get_task_history.return_value = mock_history
        self.mock_data_service.get_task_history_by_key.return_value = mock_history

        # Mock metrics calculations
        self.mock_metrics_service.calculate_time_to_delivery.return_value = 5
        self.mock_metrics_service.calculate_time_to_market.return_value = 5
        self.mock_metrics_service.calculate_tail_metric.return_value = 2
        self.mock_metrics_service.calculate_pause_time.return_value = 1
        self.mock_metrics_service.calculate_pause_time_up_to_date.return_value = 0
        self.mock_metrics_service.calculate_status_duration.return_value = 3
        self.mock_metrics_service.calculate_enhanced_statistics_with_status_durations.return_value = TimeMetrics(
            times=[5],
            mean=5.0,
            p85=5.0,
            count=1,
            pause_times=[1],
            pause_mean=1.0,
            pause_p85=1.0,
            discovery_backlog_times=[3],
            discovery_backlog_mean=3.0,
            discovery_backlog_p85=3.0,
            ready_for_dev_times=[3],
            ready_for_dev_mean=3.0,
            ready_for_dev_p85=3.0,
        )
        self.mock_metrics_service.calculate_statistics.return_value = TimeMetrics(
            times=[2], mean=2.0, p85=2.0, count=1
        )

        # Mock testing returns service
        self.mock_testing_returns_service.calculate_testing_returns_for_cpo_task.return_value = (
            1,
            0,
        )

        # Mock the command initialization
        with patch(
            "radiator.commands.generate_time_to_market_report.SessionLocal",
            return_value=self.mock_db,
        ), patch(
            "radiator.commands.generate_time_to_market_report.ConfigService",
            return_value=self.mock_config_service,
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
        ), patch(
            "radiator.commands.generate_time_to_market_report.calculate_enhanced_group_metrics_with_testing_returns"
        ) as mock_calc_group_metrics:
            # Mock group metrics calculation
            mock_group_metrics = GroupMetrics(
                group_name="Test Author",
                ttd_metrics=TimeMetrics(times=[5], mean=5.0, p85=5.0, count=1),
                ttm_metrics=TimeMetrics(times=[5], mean=5.0, p85=5.0, count=1),
                tail_metrics=TimeMetrics(times=[2], mean=2.0, p85=2.0, count=1),
                total_tasks=2,
            )
            mock_calc_group_metrics.return_value = mock_group_metrics

            # Create command
            cmd = GenerateTimeToMarketReportCommand(
                group_by=GroupBy.AUTHOR,
                config_dir="test_config",
                output_dir=self.temp_dir,
            )

            # Generate report data
            report = cmd.generate_report_data()

            # Verify report was generated
            assert report is not None
            assert len(report.quarters) == 1
            assert report.quarters[0].name == "2025.Q1"

            # Generate task details CSV
            details_file = cmd.generate_task_details_csv()

            # Verify details file was generated
            assert details_file != ""
            assert details_file.endswith(".csv")
            assert os.path.exists(details_file)

            # Verify CSV content
            with open(details_file, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.strip().split("\n")

                # Should have header + data row
                assert len(lines) >= 2

                # Check header contains all expected columns
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

                # Check data row contains expected values
                data_row = lines[1]
                assert "Test Author" in data_row
                assert "Test Team" in data_row
                assert "CPO-123" in data_row
                assert "Test Task" in data_row
                assert "2025.Q1" in data_row

    def test_full_report_generation_handles_database_errors(self):
        """Test: full report generation handles database errors gracefully."""
        # Mock database error
        self.mock_data_service.get_tasks_for_period.side_effect = Exception(
            "Database error"
        )

        # Mock the command initialization
        with patch(
            "radiator.commands.generate_time_to_market_report.SessionLocal",
            return_value=self.mock_db,
        ), patch(
            "radiator.commands.generate_time_to_market_report.ConfigService",
            return_value=self.mock_config_service,
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
            # Create command
            cmd = GenerateTimeToMarketReportCommand(
                group_by=GroupBy.AUTHOR,
                config_dir="test_config",
                output_dir=self.temp_dir,
            )

            # Generate report data - should handle errors gracefully
            report = cmd.generate_report_data()

            # Should still return a report object (even if empty)
            assert report is not None

            # Generate task details CSV - should handle errors gracefully
            details_file = cmd.generate_task_details_csv()

            # Should return empty string when no data due to errors
            assert details_file == ""

    def test_full_report_generation_handles_missing_history(self):
        """Test: full report generation handles missing task history gracefully."""
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
        self.mock_data_service.get_tasks_for_period.return_value = [mock_task]
        self.mock_data_service.get_task_history.return_value = []  # Empty history
        self.mock_data_service.get_task_history_by_key.return_value = []

        # Mock the command initialization
        with patch(
            "radiator.commands.generate_time_to_market_report.SessionLocal",
            return_value=self.mock_db,
        ), patch(
            "radiator.commands.generate_time_to_market_report.ConfigService",
            return_value=self.mock_config_service,
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
            # Create command
            cmd = GenerateTimeToMarketReportCommand(
                group_by=GroupBy.AUTHOR,
                config_dir="test_config",
                output_dir=self.temp_dir,
            )

            # Generate report data
            report = cmd.generate_report_data()

            # Should still return a report object
            assert report is not None

            # Generate task details CSV
            details_file = cmd.generate_task_details_csv()

            # Should return empty string when no data due to missing history
            assert details_file == ""

    def test_full_report_generation_creates_all_output_files(self):
        """Test: full report generation creates all expected output files."""
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

        # Mock task history
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

        # Mock data service responses
        self.mock_data_service.get_tasks_for_period.return_value = [mock_task]
        self.mock_data_service.get_task_history.return_value = mock_history
        self.mock_data_service.get_task_history_by_key.return_value = mock_history

        # Mock metrics calculations
        self.mock_metrics_service.calculate_time_to_delivery.return_value = 5
        self.mock_metrics_service.calculate_time_to_market.return_value = 5
        self.mock_metrics_service.calculate_tail_metric.return_value = 2
        self.mock_metrics_service.calculate_pause_time.return_value = 1
        self.mock_metrics_service.calculate_pause_time_up_to_date.return_value = 0
        self.mock_metrics_service.calculate_status_duration.return_value = 3
        self.mock_metrics_service.calculate_enhanced_statistics_with_status_durations.return_value = TimeMetrics(
            times=[5],
            mean=5.0,
            p85=5.0,
            count=1,
            pause_times=[1],
            pause_mean=1.0,
            pause_p85=1.0,
            discovery_backlog_times=[3],
            discovery_backlog_mean=3.0,
            discovery_backlog_p85=3.0,
            ready_for_dev_times=[3],
            ready_for_dev_mean=3.0,
            ready_for_dev_p85=3.0,
        )
        self.mock_metrics_service.calculate_statistics.return_value = TimeMetrics(
            times=[2], mean=2.0, p85=2.0, count=1
        )

        # Mock testing returns service
        self.mock_testing_returns_service.calculate_testing_returns_for_cpo_task.return_value = (
            1,
            0,
        )

        # Mock the command initialization
        with patch(
            "radiator.commands.generate_time_to_market_report.SessionLocal",
            return_value=self.mock_db,
        ), patch(
            "radiator.commands.generate_time_to_market_report.ConfigService",
            return_value=self.mock_config_service,
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
        ), patch(
            "radiator.commands.generate_time_to_market_report.calculate_enhanced_group_metrics_with_testing_returns"
        ) as mock_calc_group_metrics, patch(
            "radiator.commands.generate_time_to_market_report.CSVRenderer"
        ) as mock_csv_renderer, patch(
            "radiator.commands.generate_time_to_market_report.TableRenderer"
        ) as mock_table_renderer:
            # Mock group metrics calculation
            mock_group_metrics = GroupMetrics(
                group_name="Test Author",
                ttd_metrics=TimeMetrics(times=[5], mean=5.0, p85=5.0, count=1),
                ttm_metrics=TimeMetrics(times=[5], mean=5.0, p85=5.0, count=1),
                tail_metrics=TimeMetrics(times=[2], mean=2.0, p85=2.0, count=1),
                total_tasks=2,
            )
            mock_calc_group_metrics.return_value = mock_group_metrics

            # Mock renderers
            mock_csv_renderer.return_value.render.return_value = "test_ttd.csv"
            mock_table_renderer.return_value.render.return_value = "test_ttd_table.png"

            # Create command
            cmd = GenerateTimeToMarketReportCommand(
                group_by=GroupBy.AUTHOR,
                config_dir="test_config",
                output_dir=self.temp_dir,
            )

            # Generate report data
            report = cmd.generate_report_data()

            # Generate all report files
            ttd_csv = cmd.generate_csv(None, "ttd", "wide")
            ttd_table = cmd.generate_table(None, "ttd")
            ttm_csv = cmd.generate_csv(None, "ttm", "wide")
            ttm_table = cmd.generate_table(None, "ttm")
            details_csv = cmd.generate_task_details_csv()

            # Verify all files were generated
            assert ttd_csv != ""
            assert ttd_table != ""
            assert ttm_csv != ""
            assert ttm_table != ""
            assert details_csv != ""
            assert details_csv.endswith(".csv")
            assert os.path.exists(details_csv)
