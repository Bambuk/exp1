"""Tests for GenerateTimeToMarketReportCommand (refactored version)."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from radiator.commands.generate_time_to_market_report import (
    GenerateTimeToMarketReportCommand,
)
from radiator.commands.models.time_to_market_models import GroupBy, ReportType


class TestGenerateTimeToMarketReportCommand:
    """Test cases for GenerateTimeToMarketReportCommand (refactored version)."""

    def test_init_author_grouping(self):
        """Test command initialization with author grouping."""
        cmd = GenerateTimeToMarketReportCommand(group_by=GroupBy.AUTHOR)
        assert cmd.db is not None
        assert cmd.group_by == GroupBy.AUTHOR
        assert cmd.config_dir == "data/config"
        assert cmd.report is None

    def test_init_team_grouping(self):
        """Test command initialization with team grouping."""
        cmd = GenerateTimeToMarketReportCommand(group_by=GroupBy.TEAM)
        assert cmd.group_by == GroupBy.TEAM

    def test_init_custom_config_dir(self):
        """Test command initialization with custom config directory."""
        cmd = GenerateTimeToMarketReportCommand(config_dir="/custom/path")
        assert cmd.config_dir == "/custom/path"

    def test_context_manager(self):
        """Test context manager functionality."""
        with GenerateTimeToMarketReportCommand() as cmd:
            assert cmd.db is not None
        # db should be closed after context exit

    @patch("radiator.commands.generate_time_to_market_report.ConfigService")
    @patch("radiator.commands.generate_time_to_market_report.DataService")
    @patch("radiator.commands.generate_time_to_market_report.MetricsService")
    def test_generate_report_data_success(self, mock_metrics, mock_data, mock_config):
        """Test successful report data generation."""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config_instance.load_quarters.return_value = [
            Mock(
                name="Q1",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 3, 31),
            )
        ]
        mock_config_instance.load_status_mapping.return_value = Mock(
            discovery_statuses=["Discovery"], done_statuses=["Done"]
        )
        mock_config.return_value = mock_config_instance

        mock_data_instance = Mock()
        mock_data_instance.get_tasks_for_period.return_value = []
        mock_data.return_value = mock_data_instance

        mock_metrics_instance = Mock()
        mock_metrics.return_value = mock_metrics_instance

        cmd = GenerateTimeToMarketReportCommand()
        report = cmd.generate_report_data()

        assert report is not None
        assert report.group_by == GroupBy.AUTHOR
        assert len(report.quarters) == 1
        assert len(report.quarter_reports) == 0  # No tasks, so no quarter reports

    @patch("radiator.commands.generate_time_to_market_report.ConfigService")
    def test_generate_report_data_no_quarters(self, mock_config):
        """Test report generation with no quarters."""
        mock_config_instance = Mock()
        mock_config_instance.load_quarters.return_value = []
        mock_config_instance.load_status_mapping.return_value = Mock(
            discovery_statuses=["Discovery"], done_statuses=["Done"]
        )
        mock_config.return_value = mock_config_instance

        cmd = GenerateTimeToMarketReportCommand()
        report = cmd.generate_report_data()

        assert report is not None
        assert len(report.quarters) == 0
        assert len(report.quarter_reports) == 0

    @patch("radiator.commands.generate_time_to_market_report.ConfigService")
    def test_generate_report_data_no_statuses(self, mock_config):
        """Test report generation with no target statuses."""
        mock_config_instance = Mock()
        mock_config_instance.load_quarters.return_value = [
            Mock(
                name="Q1",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 3, 31),
            )
        ]
        mock_config_instance.load_status_mapping.return_value = Mock(
            discovery_statuses=[], done_statuses=[]
        )
        mock_config.return_value = mock_config_instance

        cmd = GenerateTimeToMarketReportCommand()
        report = cmd.generate_report_data()

        assert report is not None
        assert len(report.quarters) == 1
        assert len(report.quarter_reports) == 0

    def test_generate_csv_no_report_data(self):
        """Test CSV generation with no report data."""
        cmd = GenerateTimeToMarketReportCommand()
        result = cmd.generate_csv()
        assert result == ""

    def test_generate_table_no_report_data(self):
        """Test table generation with no report data."""
        cmd = GenerateTimeToMarketReportCommand()
        result = cmd.generate_table()
        assert result == ""

    def test_print_summary_no_report_data(self, capsys):
        """Test print summary with no report data."""
        cmd = GenerateTimeToMarketReportCommand()
        cmd.print_summary()

        captured = capsys.readouterr()
        assert "No report data available" in captured.out

    @patch("radiator.commands.generate_time_to_market_report.CSVRenderer")
    def test_generate_csv_with_report_data(self, mock_renderer):
        """Test CSV generation with report data."""
        mock_renderer_instance = Mock()
        mock_renderer_instance.render.return_value = "/path/to/file.csv"
        mock_renderer.return_value = mock_renderer_instance

        cmd = GenerateTimeToMarketReportCommand()
        cmd.report = Mock()  # Mock report data

        result = cmd.generate_csv()
        assert result == "/path/to/file.csv"
        mock_renderer_instance.render.assert_called_once()

    @patch("radiator.commands.generate_time_to_market_report.TableRenderer")
    def test_generate_table_with_report_data(self, mock_renderer):
        """Test table generation with report data."""
        mock_renderer_instance = Mock()
        mock_renderer_instance.render.return_value = "/path/to/file.png"
        mock_renderer.return_value = mock_renderer_instance

        cmd = GenerateTimeToMarketReportCommand()
        cmd.report = Mock()  # Mock report data

        result = cmd.generate_table()
        assert result == "/path/to/file.png"
        mock_renderer_instance.render.assert_called_once()

    @patch("radiator.commands.generate_time_to_market_report.ConsoleRenderer")
    def test_print_summary_with_report_data(self, mock_renderer):
        """Test print summary with report data."""
        mock_renderer_instance = Mock()
        mock_renderer.return_value = mock_renderer_instance

        cmd = GenerateTimeToMarketReportCommand()
        cmd.report = Mock()  # Mock report data

        cmd.print_summary()
        mock_renderer_instance.render.assert_called_once()

    def test_different_report_types(self):
        """Test different report types."""
        cmd = GenerateTimeToMarketReportCommand()
        # Mock report data with proper structure
        mock_report = Mock()
        mock_report.quarter_reports = {}  # Empty dict for quarters
        cmd.report = mock_report

        # Test TTD only
        cmd.print_summary(report_type=ReportType.TTD)

        # Test TTM only
        cmd.print_summary(report_type=ReportType.TTM)

        # Test both
        cmd.print_summary(report_type=ReportType.BOTH)

    def test_error_handling_in_generate_report_data(self):
        """Test error handling in generate_report_data."""
        with patch(
            "radiator.commands.generate_time_to_market_report.ConfigService"
        ) as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.load_quarters.side_effect = Exception("Config error")
            mock_config.return_value = mock_config_instance

            cmd = GenerateTimeToMarketReportCommand()
            report = cmd.generate_report_data()

            # Should return empty report on error
            assert report is not None
            assert len(report.quarters) == 0
            assert len(report.quarter_reports) == 0


if __name__ == "__main__":
    pytest.main([__file__])
