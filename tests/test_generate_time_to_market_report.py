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

    def test_init_author_grouping(self, test_reports_dir):
        """Test command initialization with author grouping."""
        cmd = GenerateTimeToMarketReportCommand(
            group_by=GroupBy.AUTHOR, output_dir=test_reports_dir
        )
        assert cmd.db is not None
        assert cmd.group_by == GroupBy.AUTHOR
        assert cmd.config_dir == "data/config"
        assert cmd.report is None

    def test_init_team_grouping(self, test_reports_dir):
        """Test command initialization with team grouping."""
        cmd = GenerateTimeToMarketReportCommand(
            group_by=GroupBy.TEAM, output_dir=test_reports_dir
        )
        assert cmd.group_by == GroupBy.TEAM

    def test_init_custom_config_dir(self, test_reports_dir):
        """Test command initialization with custom config directory."""
        cmd = GenerateTimeToMarketReportCommand(
            config_dir="/custom/path", output_dir=test_reports_dir
        )
        assert cmd.config_dir == "/custom/path"

    def test_context_manager(self, test_reports_dir):
        """Test context manager functionality."""
        with GenerateTimeToMarketReportCommand(output_dir=test_reports_dir) as cmd:
            assert cmd.db is not None
            assert cmd.output_dir == test_reports_dir
        # db should be closed after context exit

    @patch("radiator.commands.generate_time_to_market_report.ConfigService")
    @patch("radiator.commands.generate_time_to_market_report.DataService")
    @patch("radiator.commands.generate_time_to_market_report.MetricsService")
    def test_generate_report_data_success(
        self, mock_metrics, mock_data, mock_config, test_reports_dir
    ):
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

        cmd = GenerateTimeToMarketReportCommand(output_dir=test_reports_dir)
        report = cmd.generate_report_data()

        assert report is not None
        assert report.group_by == GroupBy.AUTHOR
        assert len(report.quarters) == 1
        assert len(report.quarter_reports) == 0  # No tasks, so no quarter reports

    @patch("radiator.commands.generate_time_to_market_report.ConfigService")
    def test_generate_report_data_no_quarters(self, mock_config, test_reports_dir):
        """Test report generation with no quarters."""
        mock_config_instance = Mock()
        mock_config_instance.load_quarters.return_value = []
        mock_config_instance.load_status_mapping.return_value = Mock(
            discovery_statuses=["Discovery"], done_statuses=["Done"]
        )
        mock_config.return_value = mock_config_instance

        cmd = GenerateTimeToMarketReportCommand(output_dir=test_reports_dir)
        report = cmd.generate_report_data()

        assert report is not None
        assert len(report.quarters) == 0
        assert len(report.quarter_reports) == 0

    @patch("radiator.commands.generate_time_to_market_report.ConfigService")
    def test_generate_report_data_no_statuses(self, mock_config, test_reports_dir):
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

        cmd = GenerateTimeToMarketReportCommand(output_dir=test_reports_dir)
        report = cmd.generate_report_data()

        assert report is not None
        assert len(report.quarters) == 1
        assert len(report.quarter_reports) == 0

    def test_generate_csv_no_report_data(self, test_reports_dir):
        """Test CSV generation with no report data."""
        cmd = GenerateTimeToMarketReportCommand(output_dir=test_reports_dir)
        result = cmd.generate_csv()
        assert result == ""

    def test_generate_table_no_report_data(self, test_reports_dir):
        """Test table generation with no report data."""
        cmd = GenerateTimeToMarketReportCommand(output_dir=test_reports_dir)
        result = cmd.generate_table()
        assert result == ""

    def test_print_summary_no_report_data(self, capsys, test_reports_dir):
        """Test print summary with no report data."""
        cmd = GenerateTimeToMarketReportCommand(output_dir=test_reports_dir)
        cmd.print_summary()

        captured = capsys.readouterr()
        assert "No report data available" in captured.out

    @patch("radiator.commands.generate_time_to_market_report.CSVRenderer")
    def test_generate_csv_with_report_data(self, mock_renderer, test_reports_dir):
        """Test CSV generation with report data."""
        mock_renderer_instance = Mock()
        mock_renderer_instance.render.return_value = "/path/to/file.csv"
        mock_renderer.return_value = mock_renderer_instance

        cmd = GenerateTimeToMarketReportCommand(output_dir=test_reports_dir)
        cmd.report = Mock()  # Mock report data

        result = cmd.generate_csv()
        assert result == "/path/to/file.csv"
        mock_renderer_instance.render.assert_called_once()
        # Verify that output_dir was passed to renderer
        mock_renderer.assert_called_once_with(cmd.report, test_reports_dir)

    @patch("radiator.commands.generate_time_to_market_report.TableRenderer")
    def test_generate_table_with_report_data(self, mock_renderer, test_reports_dir):
        """Test table generation with report data."""
        mock_renderer_instance = Mock()
        mock_renderer_instance.render.return_value = "/path/to/file.png"
        mock_renderer.return_value = mock_renderer_instance

        cmd = GenerateTimeToMarketReportCommand(output_dir=test_reports_dir)
        cmd.report = Mock()  # Mock report data

        result = cmd.generate_table()
        assert result == "/path/to/file.png"
        mock_renderer_instance.render.assert_called_once()
        # Verify that output_dir was passed to renderer
        mock_renderer.assert_called_once_with(cmd.report, test_reports_dir)

    @patch("radiator.commands.generate_time_to_market_report.ConsoleRenderer")
    def test_print_summary_with_report_data(self, mock_renderer, test_reports_dir):
        """Test print summary with report data."""
        mock_renderer_instance = Mock()
        mock_renderer.return_value = mock_renderer_instance

        cmd = GenerateTimeToMarketReportCommand(output_dir=test_reports_dir)
        cmd.report = Mock()  # Mock report data

        cmd.print_summary()
        mock_renderer_instance.render.assert_called_once()

    def test_different_report_types(self, test_reports_dir):
        """Test different report types."""
        cmd = GenerateTimeToMarketReportCommand(output_dir=test_reports_dir)
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

    def test_error_handling_in_generate_report_data(self, test_reports_dir):
        """Test error handling in generate_report_data."""
        with patch(
            "radiator.commands.generate_time_to_market_report.ConfigService"
        ) as mock_config:
            mock_config_instance = Mock()
            mock_config_instance.load_quarters.side_effect = Exception("Config error")
            mock_config.return_value = mock_config_instance

            cmd = GenerateTimeToMarketReportCommand(output_dir=test_reports_dir)
            report = cmd.generate_report_data()

            # Should return empty report on error
            assert report is not None
            assert len(report.quarters) == 0
            assert len(report.quarter_reports) == 0

    def test_generate_task_details_csv_includes_devlt(self, test_reports_dir):
        """Test that DevLT column is included in task details CSV."""
        from datetime import datetime

        from radiator.commands.models.time_to_market_models import (
            Quarter,
            StatusHistoryEntry,
            StatusMapping,
            TaskData,
        )

        # Create mock command
        with GenerateTimeToMarketReportCommand(output_dir=test_reports_dir) as cmd:
            # Mock report data
            quarter = Quarter("Q1 2024", datetime(2024, 1, 1), datetime(2024, 3, 31))
            status_mapping = StatusMapping(
                discovery_statuses=["Discovery"], done_statuses=["Done"]
            )

            # Create mock report
            cmd.report = MagicMock()
            cmd.report.quarters = [quarter]
            cmd.report.status_mapping = status_mapping
            cmd.report.group_by = GroupBy.AUTHOR

            # Mock data service to return task with DevLT history
            mock_task = TaskData(
                id=1,
                key="CPO-123",
                summary="Test task",
                author="Test Author",
                team="Test Team",
                group_value="Test Author",
                created_at=datetime(2024, 1, 1),
            )

            # Mock history with DevLT flow
            mock_history = [
                StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
                StatusHistoryEntry(
                    "МП / В работе", "МП / В работе", datetime(2024, 1, 5), None
                ),
                StatusHistoryEntry("Testing", "Testing", datetime(2024, 1, 10), None),
                StatusHistoryEntry(
                    "МП / Внешний тест",
                    "МП / Внешний тест",
                    datetime(2024, 1, 15),
                    None,
                ),
            ]

            # Mock data service methods
            cmd.data_service = Mock()
            cmd.data_service.get_tasks_for_period.side_effect = [
                [mock_task],  # TTD tasks
                [mock_task],  # TTM tasks
            ]
            cmd.data_service.get_task_history.return_value = mock_history

            # Generate CSV
            csv_file = cmd.generate_task_details_csv()

            # Verify CSV was created
            assert csv_file != ""
            assert Path(csv_file).exists()

            # Read CSV content
            with open(csv_file, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.strip().split("\n")

                # Check headers
                headers = lines[0].split(",")
                assert "DevLT (дни)" in headers

                # Check data row
                if len(lines) > 1:
                    data_row = lines[1].split(",")
                    devlt_index = headers.index("DevLT (дни)")
                    devlt_value = data_row[devlt_index]

                    # Should be 10 days (1/5 to 1/15)
                    assert devlt_value == "10"

    def test_generate_task_details_csv_devlt_empty_when_status_missing(
        self, test_reports_dir
    ):
        """Test that DevLT is empty when required statuses are missing."""
        from datetime import datetime

        from radiator.commands.models.time_to_market_models import (
            Quarter,
            StatusHistoryEntry,
            StatusMapping,
            TaskData,
        )

        # Create mock command
        with GenerateTimeToMarketReportCommand(output_dir=test_reports_dir) as cmd:
            # Mock report data
            quarter = Quarter("Q1 2024", datetime(2024, 1, 1), datetime(2024, 3, 31))
            status_mapping = StatusMapping(
                discovery_statuses=["Discovery"], done_statuses=["Done"]
            )

            # Create mock report
            cmd.report = MagicMock()
            cmd.report.quarters = [quarter]
            cmd.report.status_mapping = status_mapping
            cmd.report.group_by = GroupBy.AUTHOR

            # Mock task
            mock_task = TaskData(
                id=1,
                key="CPO-123",
                summary="Test task",
                author="Test Author",
                team="Test Team",
                group_value="Test Author",
                created_at=datetime(2024, 1, 1),
            )

            # Mock history without "МП / В работе" status
            mock_history = [
                StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
                StatusHistoryEntry("Testing", "Testing", datetime(2024, 1, 10), None),
                StatusHistoryEntry(
                    "МП / Внешний тест",
                    "МП / Внешний тест",
                    datetime(2024, 1, 15),
                    None,
                ),
            ]

            # Mock data service methods
            cmd.data_service = Mock()
            cmd.data_service.get_tasks_for_period.side_effect = [
                [mock_task],  # TTD tasks
                [mock_task],  # TTM tasks
            ]
            cmd.data_service.get_task_history.return_value = mock_history

            # Generate CSV
            csv_file = cmd.generate_task_details_csv()

            # Read CSV content
            with open(csv_file, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.strip().split("\n")

                # Check headers
                headers = lines[0].split(",")
                assert "DevLT (дни)" in headers

                # Check data row
                if len(lines) > 1:
                    data_row = lines[1].split(",")
                    devlt_index = headers.index("DevLT (дни)")
                    devlt_value = data_row[devlt_index]

                    # Should be empty when status missing
                    assert devlt_value == ""

    def test_generate_task_details_csv_devlt_quarter_filtering(self, test_reports_dir):
        """Test that DevLT is only shown when last 'МП / Внешний тест' is in quarter."""
        from datetime import datetime

        from radiator.commands.models.time_to_market_models import (
            Quarter,
            StatusHistoryEntry,
            StatusMapping,
            TaskData,
        )

        # Create mock command
        with GenerateTimeToMarketReportCommand(output_dir=test_reports_dir) as cmd:
            # Mock report data - Q1 2024
            quarter = Quarter("Q1 2024", datetime(2024, 1, 1), datetime(2024, 3, 31))
            status_mapping = StatusMapping(
                discovery_statuses=["Discovery"], done_statuses=["Done"]
            )

            # Create mock report
            cmd.report = MagicMock()
            cmd.report.quarters = [quarter]
            cmd.report.status_mapping = status_mapping
            cmd.report.group_by = GroupBy.AUTHOR

            # Mock task
            mock_task = TaskData(
                id=1,
                key="CPO-123",
                summary="Test task",
                author="Test Author",
                team="Test Team",
                group_value="Test Author",
                created_at=datetime(2024, 1, 1),
            )

            # Mock history with "МП / Внешний тест" outside quarter (April 2024)
            mock_history = [
                StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
                StatusHistoryEntry(
                    "МП / В работе", "МП / В работе", datetime(2024, 1, 5), None
                ),
                StatusHistoryEntry("Testing", "Testing", datetime(2024, 1, 10), None),
                StatusHistoryEntry(
                    "МП / Внешний тест",
                    "МП / Внешний тест",
                    datetime(2024, 4, 15),
                    None,
                ),  # Outside Q1
            ]

            # Mock data service methods
            cmd.data_service = Mock()
            cmd.data_service.get_tasks_for_period.side_effect = [
                [mock_task],  # TTD tasks
                [mock_task],  # TTM tasks
            ]
            cmd.data_service.get_task_history.return_value = mock_history

            # Generate CSV
            csv_file = cmd.generate_task_details_csv()

            # Read CSV content
            with open(csv_file, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.strip().split("\n")

                # Check headers
                headers = lines[0].split(",")
                assert "DevLT (дни)" in headers

                # Check data row
                if len(lines) > 1:
                    data_row = lines[1].split(",")
                    devlt_index = headers.index("DevLT (дни)")
                    devlt_value = data_row[devlt_index]

                    # Should be empty when last "МП / Внешний тест" is outside quarter
                    assert devlt_value == ""


if __name__ == "__main__":
    pytest.main([__file__])
