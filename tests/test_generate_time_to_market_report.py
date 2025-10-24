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
                    "МП / В работе",
                    "МП / В работе",
                    datetime(2024, 1, 5),
                    datetime(2024, 1, 8),
                ),
                StatusHistoryEntry("Testing", "Testing", datetime(2024, 1, 10), None),
                StatusHistoryEntry(
                    "МП / Внешний тест",
                    "МП / Внешний тест",
                    datetime(2024, 1, 15),
                    None,
                ),
                StatusHistoryEntry(
                    "Done", "Done", datetime(2024, 1, 20), None
                ),  # Done status for TTM
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

    def test_generate_task_details_csv_devlt_follows_ttm_quarter(
        self, test_reports_dir
    ):
        """Test that DevLT is shown when TTM is in quarter, regardless of МП/Внешний тест date."""
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

            # Mock history with "МП / Внешний тест" outside quarter but Done in quarter
            mock_history = [
                StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
                StatusHistoryEntry(
                    "МП / В работе",
                    "МП / В работе",
                    datetime(2024, 1, 5),
                    datetime(2024, 1, 15),
                ),
                StatusHistoryEntry("Testing", "Testing", datetime(2024, 1, 10), None),
                StatusHistoryEntry(
                    "МП / Внешний тест",
                    "МП / Внешний тест",
                    datetime(2024, 4, 15),
                    None,
                ),  # Outside Q1
                StatusHistoryEntry(
                    "Done", "Done", datetime(2024, 3, 20), None
                ),  # Done in Q1
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

                    # DevLT should be present when TTM is in quarter
                    assert (
                        devlt_value != ""
                    ), "DevLT should be present when TTM is in quarter"


class TestTTMDetailsReport:
    """Test cases for TTM Details Report generator."""

    def test_generate_empty_ttm_details_csv(self, test_reports_dir):
        """Test creation of empty CSV file with correct headers."""
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Generate CSV
        output_path = f"{test_reports_dir}/ttm_details.csv"
        result_path = generator.generate_csv(output_path)

        # Verify file was created
        assert Path(result_path).exists()
        assert result_path == output_path

        # Verify CSV content
        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check headers
        expected_headers = "Ключ задачи,Название,Автор,Команда,Квартал,TTM"
        assert expected_headers in content

        # Should only have headers (no data rows)
        lines = content.strip().split("\n")
        assert len(lines) == 1  # Only header row

    def test_load_quarters_from_config(self, test_reports_dir):
        """Test loading quarters from ConfigService."""
        from datetime import datetime
        from unittest.mock import Mock, patch

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock ConfigService
        with patch.object(
            generator.config_service, "load_quarters"
        ) as mock_load_quarters:
            from radiator.commands.models.time_to_market_models import Quarter

            mock_quarters = [
                Quarter(
                    name="Q1",
                    start_date=datetime(2025, 1, 1),
                    end_date=datetime(2025, 3, 31),
                ),
                Quarter(
                    name="Q2",
                    start_date=datetime(2025, 4, 1),
                    end_date=datetime(2025, 6, 30),
                ),
            ]
            mock_load_quarters.return_value = mock_quarters

            # Test loading quarters
            quarters = generator._load_quarters()

            # Verify quarters were loaded
            assert len(quarters) == 2
            assert quarters[0].name == "Q1"
            assert quarters[1].name == "Q2"
            mock_load_quarters.assert_called_once()

    def test_load_done_statuses(self, test_reports_dir):
        """Test loading done statuses from ConfigService."""
        from unittest.mock import Mock, patch

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock ConfigService
        with patch.object(
            generator.config_service, "load_status_mapping"
        ) as mock_load_status_mapping:
            mock_status_mapping = Mock()
            mock_status_mapping.done_statuses = ["Done", "Закрыт", "Выполнено"]
            mock_load_status_mapping.return_value = mock_status_mapping

            # Test loading done statuses
            done_statuses = generator._load_done_statuses()

            # Verify done statuses were loaded
            assert len(done_statuses) == 3
            assert "Done" in done_statuses
            assert "Закрыт" in done_statuses
            assert "Выполнено" in done_statuses
            mock_load_status_mapping.assert_called_once()

    def test_get_ttm_tasks_for_quarter(self, test_reports_dir):
        """Test getting TTM tasks for a quarter."""
        from datetime import datetime
        from unittest.mock import Mock, patch

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock DataService
        from radiator.commands.models.time_to_market_models import TaskData

        mock_tasks = [
            TaskData(
                id=1,
                key="CPO-123",
                group_value="Author1",
                author="Author1",
                team=None,
                created_at=datetime.now(),
                summary="Task 1",
            ),
            TaskData(
                id=2,
                key="CPO-456",
                group_value="Author2",
                author="Author2",
                team=None,
                created_at=datetime.now(),
                summary="Task 2",
            ),
        ]

        # Replace data_service with mock
        generator.data_service = Mock()
        generator.data_service.get_tasks_for_period.return_value = mock_tasks

        # Mock quarter
        from radiator.commands.models.time_to_market_models import Quarter

        quarter = Quarter(
            name="Q1", start_date=datetime(2025, 1, 1), end_date=datetime(2025, 3, 31)
        )

        # Test getting TTM tasks
        tasks = generator._get_ttm_tasks_for_quarter(quarter)

        # Verify tasks were retrieved
        assert len(tasks) == 2
        assert tasks[0].key == "CPO-123"
        assert tasks[1].key == "CPO-456"

        # Verify DataService was called with correct parameters
        generator.data_service.get_tasks_for_period.assert_called_once()
        call_args = generator.data_service.get_tasks_for_period.call_args
        assert call_args[1]["metric_type"] == "ttm"
        assert call_args[1]["start_date"] == quarter.start_date
        assert call_args[1]["end_date"] == quarter.end_date

    def test_calculate_ttm_for_task(self, test_reports_dir):
        """Test calculating TTM for a task."""
        from datetime import datetime
        from unittest.mock import Mock, patch

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock MetricsService
        generator.metrics_service = Mock()
        generator.metrics_service.calculate_time_to_market.return_value = 15

        # Mock task history
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 1, 1),
                end_date=None,
            ),
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 1, 16),
                end_date=None,
            ),
        ]

        # Replace data_service with mock
        generator.data_service = Mock()
        generator.data_service.get_task_history.return_value = mock_history

        # Mock done statuses
        done_statuses = ["Done", "Закрыт"]

        # Test calculating TTM
        ttm = generator._calculate_ttm(123, done_statuses)

        # Verify TTM was calculated
        assert ttm == 15

        # Verify MetricsService was called with correct parameters
        generator.metrics_service.calculate_time_to_market.assert_called_once()
        call_args = generator.metrics_service.calculate_time_to_market.call_args
        assert call_args[0][0] == mock_history  # history
        assert call_args[0][1] == done_statuses  # done_statuses

    def test_collect_csv_rows(self, test_reports_dir):
        """Test collecting CSV rows data."""
        from datetime import datetime
        from unittest.mock import Mock, patch

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock quarters
        from radiator.commands.models.time_to_market_models import Quarter

        mock_quarters = [
            Quarter(
                name="Q1",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 3, 31),
            ),
            Quarter(
                name="Q2",
                start_date=datetime(2025, 4, 1),
                end_date=datetime(2025, 6, 30),
            ),
        ]
        generator._load_quarters = Mock(return_value=mock_quarters)

        # Mock done statuses
        mock_done_statuses = ["Done", "Закрыт"]
        generator._load_done_statuses = Mock(return_value=mock_done_statuses)

        # Mock tasks for quarters
        from radiator.commands.models.time_to_market_models import TaskData

        mock_tasks_q1 = [
            TaskData(
                id=1,
                key="CPO-123",
                group_value="Author1",
                author="Author1",
                team=None,
                created_at=datetime.now(),
                summary="Task 1",
            ),
            TaskData(
                id=2,
                key="CPO-456",
                group_value="Author2",
                author="Author2",
                team=None,
                created_at=datetime.now(),
                summary="Task 2",
            ),
        ]
        mock_tasks_q2 = [
            TaskData(
                id=3,
                key="CPO-789",
                group_value="Author1",
                author="Author1",
                team=None,
                created_at=datetime.now(),
                summary="Task 3",
            )
        ]

        generator._get_ttm_tasks_for_quarter = Mock(
            side_effect=[mock_tasks_q1, mock_tasks_q2]
        )

        # Mock TTM calculations
        generator._calculate_ttm = Mock(
            side_effect=[15, 20, 10]
        )  # TTM for tasks 1, 2, 3

        # Test collecting CSV rows
        rows = generator._collect_csv_rows()

        # Verify rows were collected
        assert len(rows) == 3

        # Check first row
        row1 = rows[0]
        assert row1["Ключ задачи"] == "CPO-123"
        assert row1["Название"] == "Task 1"
        assert row1["Автор"] == "Author1"
        assert row1["Команда"] == ""
        assert row1["Квартал"] == "Q1"
        assert row1["TTM"] == 15

        # Check second row
        row2 = rows[1]
        assert row2["Ключ задачи"] == "CPO-456"
        assert row2["TTM"] == 20
        assert row2["Квартал"] == "Q1"

        # Check third row
        row3 = rows[2]
        assert row3["Ключ задачи"] == "CPO-789"
        assert row3["TTM"] == 10
        assert row3["Квартал"] == "Q2"

        # Verify methods were called
        generator._load_quarters.assert_called_once()
        generator._load_done_statuses.assert_called_once()
        assert generator._get_ttm_tasks_for_quarter.call_count == 2
        assert generator._calculate_ttm.call_count == 3

    def test_write_csv_with_data(self, test_reports_dir):
        """Test writing CSV with real data."""
        from datetime import datetime
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock CSV rows data
        mock_rows = [
            {
                "Ключ задачи": "CPO-123",
                "Название": "Task 1",
                "Автор": "Author1",
                "Команда": "",
                "Квартал": "Q1",
                "TTM": 15,
            },
            {
                "Ключ задачи": "CPO-456",
                "Название": "Task 2",
                "Автор": "Author2",
                "Команда": "",
                "Квартал": "Q1",
                "TTM": 20,
            },
        ]
        generator._collect_csv_rows = Mock(return_value=mock_rows)

        # Test writing CSV
        output_path = f"{test_reports_dir}/ttm_details_with_data.csv"
        result_path = generator.generate_csv(output_path)

        # Verify file was created
        assert Path(result_path).exists()
        assert result_path == output_path

        # Verify CSV content
        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.strip().split("\n")

            # Should have header + 2 data rows
            assert len(lines) == 3

            # Check headers
            headers = lines[0].split(",")
            expected_headers = [
                "Ключ задачи",
                "Название",
                "Автор",
                "Команда",
                "Квартал",
                "TTM",
            ]
            assert headers == expected_headers

            # Check first data row
            row1 = lines[1].split(",")
            assert row1[0] == "CPO-123"
            assert row1[1] == "Task 1"
            assert row1[2] == "Author1"
            assert row1[3] == ""
            assert row1[4] == "Q1"
            assert row1[5] == "15"

            # Check second data row
            row2 = lines[2].split(",")
            assert row2[0] == "CPO-456"
            assert row2[5] == "20"

        # Verify _collect_csv_rows was called
        generator._collect_csv_rows.assert_called_once()

    def test_integration_with_real_db(self, test_reports_dir):
        """Test integration with real test database."""
        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )
        from radiator.core.database import SessionLocal

        # Use real database session
        with SessionLocal() as db:
            # Create generator with real database
            generator = TTMDetailsReportGenerator(db=db)

            # Test generating CSV with real data
            output_path = f"{test_reports_dir}/ttm_details_integration.csv"
            result_path = generator.generate_csv(output_path)

            # Verify file was created
            assert Path(result_path).exists()
            assert result_path == output_path

            # Verify CSV content has headers
            import csv

            with open(result_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)

                # Should have at least headers
                assert len(rows) >= 1

                # Check headers
                headers = rows[0]
                expected_headers = [
                    "Ключ задачи",
                    "Название",
                    "Автор",
                    "Команда",
                    "Квартал",
                    "TTM",
                ]
                assert headers == expected_headers

                # If there are data rows, check format
                if len(rows) > 1:
                    # Check that data rows have correct number of columns
                    for i, row in enumerate(rows[1:], 1):
                        assert (
                            len(row) == 6
                        ), f"Row {i} has {len(row)} columns, expected 6"

                        # Check that TTM column is numeric or empty
                        ttm_value = row[5]
                        if ttm_value:  # Not empty
                            try:
                                int(ttm_value)
                            except ValueError:
                                assert (
                                    False
                                ), f"TTM value '{ttm_value}' in row {i} is not numeric"

            # Log the result for debugging
            print(f"Integration test generated CSV with {len(rows)-1} data rows")


if __name__ == "__main__":
    pytest.main([__file__])
