"""Tests for TTM Details Report generator."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from radiator.commands.generate_ttm_details_report import TTMDetailsReportGenerator


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
        assert (
            row1["Команда"] == "Без команды"
        )  # AuthorTeamMappingService returns "Без команды" for unknown authors
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
                "Пауза": "",
                "Tail": "",
                "DevLT": "",
                "TTD": "",
                "TTD Pause": "",
                "Квартал TTD": "",
            },
            {
                "Ключ задачи": "CPO-456",
                "Название": "Task 2",
                "Автор": "Author2",
                "Команда": "",
                "Квартал": "Q1",
                "TTM": 20,
                "Пауза": "",
                "Tail": "",
                "DevLT": "",
                "TTD": "",
                "TTD Pause": "",
                "Квартал TTD": "",
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
                "Пауза",
                "Tail",
                "DevLT",
                "TTD",
                "TTD Pause",
                "Квартал TTD",
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
                    "Пауза",
                    "Tail",
                    "DevLT",
                    "TTD",
                    "TTD Pause",
                    "Квартал TTD",
                ]
                assert headers == expected_headers

                # If there are data rows, check format
                if len(rows) > 1:
                    # Check that data rows have correct number of columns
                    for i, row in enumerate(rows[1:], 1):
                        assert (
                            len(row) == 12
                        ), f"Row {i} has {len(row)} columns, expected 12"

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

    def test_ttm_details_csv_has_tail_column(self, test_reports_dir):
        """Test that TTM Details CSV has Tail column after TTM."""
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock CSV rows data with Tail column
        mock_rows = [
            {
                "Ключ задачи": "CPO-123",
                "Название": "Task 1",
                "Автор": "Author1",
                "Команда": "",
                "Квартал": "Q1",
                "TTM": 15,
                "Пауза": "",
                "Tail": "",
                "DevLT": "",
                "TTD": "",
                "TTD Pause": "",
                "Квартал TTD": "",
            }
        ]
        generator._collect_csv_rows = Mock(return_value=mock_rows)

        # Test generating CSV
        output_path = f"{test_reports_dir}/ttm_details_with_tail.csv"
        result_path = generator.generate_csv(output_path)

        # Verify file was created
        assert Path(result_path).exists()
        assert result_path == output_path

        # Verify CSV content has Tail column
        import csv

        with open(result_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            lines = list(reader)

            # Should have header + 1 data row
            assert len(lines) == 2

            # Check headers include Tail after TTM
            headers = lines[0]
            expected_headers = [
                "Ключ задачи",
                "Название",
                "Автор",
                "Команда",
                "Квартал",
                "TTM",
                "Пауза",
                "Tail",
                "DevLT",
                "TTD",
                "TTD Pause",
                "Квартал TTD",
            ]
            assert headers == expected_headers

            # Check first data row has Tail column
            row1 = lines[1]
            assert (
                len(row1) == 12
            )  # 12 columns including Пауза, Tail, DevLT, TTD, TTD Pause, and Квартал TTD
            assert row1[0] == "CPO-123"
            assert row1[5] == "15"  # TTM
            assert row1[6] == ""  # Tail (empty)
            assert row1[7] == ""  # DevLT (empty)

    def test_ttm_details_csv_has_devlt_column(self, test_reports_dir):
        """Test that TTM Details CSV has DevLT column after Tail."""
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock CSV rows data with DevLT column
        mock_rows = [
            {
                "Ключ задачи": "CPO-123",
                "Название": "Task 1",
                "Автор": "Author1",
                "Команда": "",
                "Квартал": "Q1",
                "TTM": 15,
                "Пауза": "",
                "Tail": "",
                "DevLT": "",
                "TTD": "",
                "TTD Pause": "",
                "Квартал TTD": "",
            }
        ]
        generator._collect_csv_rows = Mock(return_value=mock_rows)

        # Test generating CSV
        output_path = f"{test_reports_dir}/ttm_details_with_devlt.csv"
        result_path = generator.generate_csv(output_path)

        # Verify file was created
        assert Path(result_path).exists()
        assert result_path == output_path

        # Verify CSV content has DevLT column
        import csv

        with open(result_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            lines = list(reader)

            # Should have header + 1 data row
            assert len(lines) == 2

            # Check headers include DevLT after Tail
            headers = lines[0]
            expected_headers = [
                "Ключ задачи",
                "Название",
                "Автор",
                "Команда",
                "Квартал",
                "TTM",
                "Пауза",
                "Tail",
                "DevLT",
                "TTD",
                "TTD Pause",
                "Квартал TTD",
            ]
            assert headers == expected_headers

            # Check first data row has DevLT column
            row1 = lines[1]
            assert (
                len(row1) == 12
            )  # 12 columns including Пауза, DevLT, TTD, TTD Pause, and Квартал TTD
            assert row1[0] == "CPO-123"
            assert row1[5] == "15"  # TTM
            assert row1[6] == ""  # Tail (empty)
            assert row1[7] == ""  # DevLT (empty)

    def test_calculate_devlt_for_task_with_valid_statuses(self, test_reports_dir):
        """Test calculating DevLT for task with МП / В работе and МП / Внешний тест statuses."""
        from datetime import datetime
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock MetricsService
        generator.metrics_service = Mock()
        generator.metrics_service.calculate_dev_lead_time.return_value = 10

        # Mock task history with МП / В работе and МП / Внешний тест
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 1, 1),
                end_date=None,
            ),
            StatusHistoryEntry(
                status="МП / В работе",
                status_display="МП / В работе",
                start_date=datetime(2025, 1, 5),
                end_date=None,
            ),
            StatusHistoryEntry(
                status="МП / Внешний тест",
                status_display="МП / Внешний тест",
                start_date=datetime(2025, 1, 15),
                end_date=None,
            ),
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 1, 20),
                end_date=None,
            ),
        ]

        # Replace data_service with mock
        generator.data_service = Mock()
        generator.data_service.get_task_history.return_value = mock_history

        # Test calculating DevLT
        devlt = generator._calculate_devlt(task_id=1, history=mock_history)

        # Verify DevLT was calculated
        assert devlt == 10

        # Verify MetricsService was called with correct parameters
        generator.metrics_service.calculate_dev_lead_time.assert_called_once()
        call_args = generator.metrics_service.calculate_dev_lead_time.call_args
        assert call_args[0][0] == mock_history  # history

    def test_calculate_devlt_returns_none_without_required_statuses(
        self, test_reports_dir
    ):
        """Test that DevLT returns None for task without МП / В работе or МП / Внешний тест statuses."""
        from datetime import datetime
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock MetricsService to return None (no required statuses)
        generator.metrics_service = Mock()
        generator.metrics_service.calculate_dev_lead_time.return_value = None

        # Mock task history without МП / В работе or МП / Внешний тест
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 1, 1),
                end_date=None,
            ),
            StatusHistoryEntry(
                status="В работе",
                status_display="В работе",
                start_date=datetime(2025, 1, 2),
                end_date=None,
            ),
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 1, 10),
                end_date=None,
            ),
        ]

        # Replace data_service with mock
        generator.data_service = Mock()
        generator.data_service.get_task_history.return_value = mock_history

        # Test calculating DevLT
        devlt = generator._calculate_devlt(task_id=1, history=mock_history)

        # Verify DevLT returns None
        assert devlt is None

        # Verify MetricsService was called with correct parameters
        generator.metrics_service.calculate_dev_lead_time.assert_called_once()
        call_args = generator.metrics_service.calculate_dev_lead_time.call_args
        assert call_args[0][0] == mock_history  # history

    def test_format_task_row_with_devlt_none(self, test_reports_dir):
        """Test that DevLT = None is formatted as empty string."""
        from datetime import datetime
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock task data
        from radiator.commands.models.time_to_market_models import TaskData

        task = TaskData(
            id=1,
            key="CPO-123",
            group_value="Author1",
            author="Author1",
            team=None,
            created_at=datetime.now(),
            summary="Task 1",
        )

        # Test formatting with DevLT = None
        row = generator._format_task_row(
            task, ttm=15, quarter_name="Q1", tail=None, devlt=None
        )

        # Verify DevLT is formatted as empty string
        assert row["Ключ задачи"] == "CPO-123"
        assert row["Название"] == "Task 1"
        assert row["Автор"] == "Author1"
        assert row["Команда"] == "Без команды"
        assert row["Квартал"] == "Q1"
        assert row["TTM"] == 15
        assert row["Tail"] == ""  # None formatted as empty string
        assert row["DevLT"] == ""  # None formatted as empty string

        # Test formatting with DevLT = 10
        row_with_devlt = generator._format_task_row(
            task, ttm=15, quarter_name="Q1", tail=5, devlt=10
        )

        # Verify DevLT is formatted correctly
        assert row_with_devlt["TTM"] == 15
        assert row_with_devlt["Tail"] == 5
        assert row_with_devlt["DevLT"] == 10  # Valid value preserved

    def test_calculate_tail_for_task_with_mp_external_test(self, test_reports_dir):
        """Test calculating Tail for task with МП / Внешний тест status."""
        from datetime import datetime
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock MetricsService
        generator.metrics_service = Mock()
        generator.metrics_service.calculate_tail_metric.return_value = 5

        # Mock task history with МП / Внешний тест
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 1, 1),
                end_date=None,
            ),
            StatusHistoryEntry(
                status="МП / Внешний тест",
                status_display="МП / Внешний тест",
                start_date=datetime(2025, 1, 10),
                end_date=None,
            ),
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 1, 15),
                end_date=None,
            ),
        ]

        # Replace data_service with mock
        generator.data_service = Mock()
        generator.data_service.get_task_history.return_value = mock_history

        # Mock done statuses
        done_statuses = ["Done", "Закрыт"]

        # Test calculating Tail
        tail = generator._calculate_tail(
            task_id=1, done_statuses=done_statuses, history=mock_history
        )

        # Verify Tail was calculated
        assert tail == 5

        # Verify MetricsService was called with correct parameters
        generator.metrics_service.calculate_tail_metric.assert_called_once()
        call_args = generator.metrics_service.calculate_tail_metric.call_args
        assert call_args[0][0] == mock_history  # history
        assert call_args[0][1] == done_statuses  # done_statuses

    def test_calculate_tail_returns_none_without_mp_external_test(
        self, test_reports_dir
    ):
        """Test that Tail returns None for task without МП / Внешний тест status."""
        from datetime import datetime
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock MetricsService to return None (no МП / Внешний тест)
        generator.metrics_service = Mock()
        generator.metrics_service.calculate_tail_metric.return_value = None

        # Mock task history without МП / Внешний тест
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 1, 1),
                end_date=None,
            ),
            StatusHistoryEntry(
                status="В работе",
                status_display="В работе",
                start_date=datetime(2025, 1, 2),
                end_date=None,
            ),
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 1, 10),
                end_date=None,
            ),
        ]

        # Replace data_service with mock
        generator.data_service = Mock()
        generator.data_service.get_task_history.return_value = mock_history

        # Mock done statuses
        done_statuses = ["Done", "Закрыт"]

        # Test calculating Tail
        tail = generator._calculate_tail(
            task_id=1, done_statuses=done_statuses, history=mock_history
        )

        # Verify Tail returns None
        assert tail is None

        # Verify MetricsService was called with correct parameters
        generator.metrics_service.calculate_tail_metric.assert_called_once()
        call_args = generator.metrics_service.calculate_tail_metric.call_args
        assert call_args[0][0] == mock_history  # history
        assert call_args[0][1] == done_statuses  # done_statuses

    def test_collect_csv_rows_with_tail(self, test_reports_dir):
        """Test collecting CSV rows with Tail metric calculation."""
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

        # Mock TTM, Tail, and DevLT calculations
        generator._calculate_ttm = Mock(
            side_effect=[15, 20, 10]
        )  # TTM for tasks 1, 2, 3
        generator._calculate_tail = Mock(
            side_effect=[5, None, 3]
        )  # Tail for tasks 1, 2, 3
        generator._calculate_devlt = Mock(
            side_effect=[8, None, 6]
        )  # DevLT for tasks 1, 2, 3

        # Test collecting CSV rows
        rows = generator._collect_csv_rows()

        # Verify rows were collected
        assert len(rows) == 3

        # Check first row (with Tail and DevLT)
        row1 = rows[0]
        assert row1["Ключ задачи"] == "CPO-123"
        assert row1["Название"] == "Task 1"
        assert row1["Автор"] == "Author1"
        assert (
            row1["Команда"] == "Без команды"
        )  # AuthorTeamMappingService returns "Без команды" for unknown authors
        assert row1["Квартал"] == "Q1"
        assert row1["TTM"] == 15
        assert row1["Tail"] == 5
        assert row1["DevLT"] == 8

        # Check second row (without Tail and DevLT)
        row2 = rows[1]
        assert row2["Ключ задачи"] == "CPO-456"
        assert row2["TTM"] == 20
        assert row2["Tail"] == ""  # None formatted as empty string
        assert row2["DevLT"] == ""  # None formatted as empty string

        # Check third row (with Tail and DevLT)
        row3 = rows[2]
        assert row3["Ключ задачи"] == "CPO-789"
        assert row3["TTM"] == 10
        assert row3["Tail"] == 3
        assert row3["DevLT"] == 6

        # Verify methods were called
        generator._load_quarters.assert_called_once()
        generator._load_done_statuses.assert_called_once()
        assert generator._get_ttm_tasks_for_quarter.call_count == 2
        assert generator._calculate_ttm.call_count == 3
        assert generator._calculate_tail.call_count == 3
        assert generator._calculate_devlt.call_count == 3

    def test_format_task_row_with_tail_none(self, test_reports_dir):
        """Test that Tail = None is formatted as empty string."""
        from datetime import datetime
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock task data
        from radiator.commands.models.time_to_market_models import TaskData

        task = TaskData(
            id=1,
            key="CPO-123",
            group_value="Author1",
            author="Author1",
            team=None,
            created_at=datetime.now(),
            summary="Task 1",
        )

        # Test formatting with Tail = None
        row = generator._format_task_row(task, ttm=15, quarter_name="Q1", tail=None)

        # Verify Tail is formatted as empty string
        assert row["Ключ задачи"] == "CPO-123"
        assert row["Название"] == "Task 1"
        assert row["Автор"] == "Author1"
        assert (
            row["Команда"] == "Без команды"
        )  # AuthorTeamMappingService returns "Без команды" for unknown authors
        assert row["Квартал"] == "Q1"
        assert row["TTM"] == 15
        assert row["Tail"] == ""  # None formatted as empty string

        # Test formatting with Tail = 5
        row_with_tail = generator._format_task_row(
            task, ttm=15, quarter_name="Q1", tail=5
        )

        # Verify Tail is formatted correctly
        assert row_with_tail["TTM"] == 15
        assert row_with_tail["Tail"] == 5  # Valid value preserved

    def test_integration_ttm_details_with_tail(self, test_reports_dir):
        """Test integration with real test database and Tail column generation."""
        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )
        from radiator.core.database import SessionLocal

        # Use real database session
        with SessionLocal() as db:
            # Create generator with real database
            generator = TTMDetailsReportGenerator(db=db)

            # Test generating CSV with real data
            output_path = f"{test_reports_dir}/ttm_details_integration_with_tail.csv"
            result_path = generator.generate_csv(output_path)

            # Verify file was created
            assert Path(result_path).exists()
            assert result_path == output_path

            # Verify CSV content has headers including Tail
            import csv

            with open(result_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)

                # Should have at least headers
                assert len(rows) >= 1

                # Check headers include Tail and DevLT after TTM
                headers = rows[0]
                expected_headers = [
                    "Ключ задачи",
                    "Название",
                    "Автор",
                    "Команда",
                    "Квартал",
                    "TTM",
                    "Пауза",
                    "Tail",
                    "DevLT",
                    "TTD",
                    "TTD Pause",
                    "Квартал TTD",
                ]
                assert headers == expected_headers

                # If there are data rows, check format
                if len(rows) > 1:
                    # Check that data rows have correct number of columns
                    for i, row in enumerate(rows[1:], 1):
                        assert (
                            len(row) == 12
                        ), f"Row {i} has {len(row)} columns, expected 12"

                        # Check that TTM column is numeric or empty
                        ttm_value = row[5]
                        if ttm_value:  # Not empty
                            try:
                                int(ttm_value)
                            except ValueError:
                                assert (
                                    False
                                ), f"TTM value '{ttm_value}' in row {i} is not numeric"

                        # Check that Tail column is numeric or empty
                        tail_value = row[6]
                        if tail_value:  # Not empty
                            try:
                                int(tail_value)
                            except ValueError:
                                assert (
                                    False
                                ), f"Tail value '{tail_value}' in row {i} is not numeric"

                        # Check that DevLT column is numeric or empty
                        devlt_value = row[7]
                        if devlt_value:  # Not empty
                            try:
                                int(devlt_value)
                            except ValueError:
                                assert (
                                    False
                                ), f"DevLT value '{devlt_value}' in row {i} is not numeric"

            # Log the result for debugging
            print(
                f"Integration test with Tail generated CSV with {len(rows)-1} data rows"
            )

    def test_team_field_populated_from_author_mapping(self, test_reports_dir):
        """Test that team field is populated using AuthorTeamMappingService."""
        import tempfile
        from datetime import datetime
        from pathlib import Path
        from unittest.mock import Mock, patch

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Create temporary directory and author-team mapping file
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "cpo_authors.txt"
            with open(mapping_file, "w", encoding="utf-8") as f:
                f.write("Александр Тихонов;Корзинка и заказ\n")
                f.write("Александр Черкасов;Каталог\n")
                f.write("Алексей Никишанин;\n")  # Empty team

            # Mock database session
            mock_db = Mock()

            # Create generator with custom config dir containing mapping file
            generator = TTMDetailsReportGenerator(db=mock_db, config_dir=temp_dir)

            # Mock task data
            from radiator.commands.models.time_to_market_models import TaskData

            task = TaskData(
                id=1,
                key="CPO-123",
                group_value="Александр Тихонов",
                author="Александр Тихонов",
                team=None,  # Will be populated by AuthorTeamMappingService
                created_at=datetime.now(),
                summary="Test task",
            )

            # Test formatting task row - should populate team field
            row = generator._format_task_row(task, ttm=15, quarter_name="Q1", tail=5)

            # Verify team field is populated from AuthorTeamMappingService
            assert row["Ключ задачи"] == "CPO-123"
            assert row["Автор"] == "Александр Тихонов"
            assert (
                row["Команда"] == "Корзинка и заказ"
            )  # Should be populated from mapping
            assert row["TTM"] == 15
            assert row["Tail"] == 5

    def test_team_field_uses_existing_team_if_available(self, test_reports_dir):
        """Test that existing team is used if available, not AuthorTeamMappingService."""
        import tempfile
        from datetime import datetime
        from pathlib import Path
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Create temporary directory and author-team mapping file
        with tempfile.TemporaryDirectory() as temp_dir:
            mapping_file = Path(temp_dir) / "cpo_authors.txt"
            with open(mapping_file, "w", encoding="utf-8") as f:
                f.write("Александр Тихонов;Корзинка и заказ\n")
                f.write("Александр Черкасов;Каталог\n")

            # Mock database session
            mock_db = Mock()

            # Create generator with custom config dir containing mapping file
            generator = TTMDetailsReportGenerator(db=mock_db, config_dir=temp_dir)

            # Mock task data with existing team
            from radiator.commands.models.time_to_market_models import TaskData

            task = TaskData(
                id=1,
                key="CPO-123",
                group_value="Александр Тихонов",
                author="Александр Тихонов",
                team="Существующая команда",  # Already has team
                created_at=datetime.now(),
                summary="Test task",
            )

            # Test formatting task row - should use existing team, not mapping
            row = generator._format_task_row(task, ttm=15, quarter_name="Q1", tail=5)

            # Verify existing team is used, not AuthorTeamMappingService result
            assert row["Ключ задачи"] == "CPO-123"
            assert row["Автор"] == "Александр Тихонов"
            assert row["Команда"] == "Существующая команда"  # Should use existing team
            assert row["TTM"] == 15
            assert row["Tail"] == 5

    def test_ttm_details_csv_has_ttd_columns(self, test_reports_dir):
        """Test that generated CSV includes TTD and Квартал TTD columns."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock the methods to return empty data
        generator._collect_csv_rows = Mock(return_value=[])
        generator._load_quarters = Mock(return_value=[])
        generator._load_done_statuses = Mock(return_value=[])

        # Generate CSV
        output_path = f"{test_reports_dir}/ttm_details_ttd.csv"
        result_path = generator.generate_csv(output_path)

        # Verify file was created
        assert Path(result_path).exists()

        # Check CSV headers include TTD columns
        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.strip().split("\n")
        headers = lines[0].split(",")

        # Check headers include TTD and Квартал TTD after DevLT
        expected_headers = [
            "Ключ задачи",
            "Название",
            "Автор",
            "Команда",
            "Квартал",
            "TTM",
            "Пауза",
            "Tail",
            "DevLT",
            "TTD",  # New TTD column
            "TTD Pause",  # New TTD pause column
            "Квартал TTD",  # New TTD quarter column
        ]
        assert headers == expected_headers

    def test_calculate_ttd_for_task_with_ready_status(self, test_reports_dir):
        """Test TTD calculation for task with ready status."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock metrics service
        generator.metrics_service.calculate_time_to_delivery = Mock(return_value=10)

        # Mock history data
        mock_history = [
            Mock(status="Создана", start_date=datetime(2025, 1, 1)),
            Mock(status="Готова к разработке", start_date=datetime(2025, 1, 5)),
        ]

        # Mock discovery statuses
        discovery_statuses = ["Готова к разработке"]

        # Test TTD calculation
        result = generator._calculate_ttd(1, discovery_statuses, mock_history)

        # Verify metrics service was called correctly
        generator.metrics_service.calculate_time_to_delivery.assert_called_once_with(
            mock_history, discovery_statuses
        )
        assert result == 10

    def test_get_ttd_target_date_finds_first_ready_status(self, test_reports_dir):
        """Test finding first ready status for TTD target date."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock history with multiple statuses
        mock_history = [
            Mock(status="Создана", start_date=datetime(2025, 1, 1)),
            Mock(status="В работе", start_date=datetime(2025, 1, 2)),
            Mock(
                status="Готова к разработке", start_date=datetime(2025, 1, 5)
            ),  # First ready
            Mock(status="В разработке", start_date=datetime(2025, 1, 6)),
            Mock(
                status="Готова к разработке", start_date=datetime(2025, 1, 8)
            ),  # Second ready
        ]

        # Test finding first ready status
        result = generator._get_ttd_target_date(mock_history)

        # Should return date of first "Готова к разработке"
        assert result == datetime(2025, 1, 5)

    def test_determine_quarter_for_date(self, test_reports_dir):
        """Test determining quarter for a given date."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock quarters
        from radiator.commands.models.time_to_market_models import Quarter

        quarters = [
            Quarter(
                name="2025.Q1",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 3, 31),
            ),
            Quarter(
                name="2025.Q2",
                start_date=datetime(2025, 4, 1),
                end_date=datetime(2025, 6, 30),
            ),
        ]

        # Test date in Q1
        result = generator._determine_quarter_for_date(datetime(2025, 2, 15), quarters)
        assert result == "2025.Q1"

        # Test date in Q2
        result = generator._determine_quarter_for_date(datetime(2025, 5, 15), quarters)
        assert result == "2025.Q2"

        # Test date outside quarters
        result = generator._determine_quarter_for_date(datetime(2024, 12, 31), quarters)
        assert result is None

    def test_collect_csv_rows_with_ttd(self, test_reports_dir):
        """Test collecting CSV rows with TTD calculation."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock quarters and tasks
        from radiator.commands.models.time_to_market_models import Quarter, TaskData

        quarters = [
            Quarter(
                name="2025.Q1",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 3, 31),
            )
        ]
        tasks = [
            TaskData(
                id=1,
                key="CPO-123",
                group_value="Author1",
                author="Author1",
                team=None,
                summary="Task 1",
                created_at=datetime(2025, 1, 1),
            ),
            TaskData(
                id=2,
                key="CPO-456",
                group_value="Author2",
                author="Author2",
                team=None,
                summary="Task 2",
                created_at=datetime(2025, 1, 1),
            ),
        ]

        # Mock methods
        generator._load_quarters = Mock(return_value=quarters)
        generator._load_done_statuses = Mock(return_value=["done"])
        generator._get_ttm_tasks_for_quarter = Mock(return_value=tasks)
        generator.data_service.get_task_history = Mock(return_value=[])  # Mock history
        generator._calculate_ttm = Mock(side_effect=[15, 20, 10])
        generator._calculate_tail = Mock(side_effect=[5, None, 3])
        generator._calculate_devlt = Mock(side_effect=[8, None, 6])
        generator._calculate_ttd = Mock(side_effect=[12, None, 9])  # Mock TTD
        generator._get_ttd_target_date = Mock(
            side_effect=[datetime(2025, 1, 5), None, datetime(2025, 1, 8)]
        )
        generator._determine_quarter_for_date = Mock(
            side_effect=["2025.Q1", None, "2025.Q1"]
        )

        # Test collecting rows
        rows = generator._collect_csv_rows()

        # Verify TTD and quarter are calculated
        assert len(rows) == 2
        row1, row2 = rows

        # Check TTD values
        assert row1["TTD"] == 12
        assert row1["Квартал TTD"] == "2025.Q1"
        assert row2["TTD"] == ""
        assert row2["Квартал TTD"] == ""

        # Verify TTD methods were called
        assert generator._calculate_ttd.call_count == 2
        assert (
            generator._get_ttd_target_date.call_count == 1
        )  # Only called when TTD is not None
        assert (
            generator._determine_quarter_for_date.call_count == 1
        )  # Only called when target date is found

    def test_format_task_row_with_ttd_none(self, test_reports_dir):
        """Test formatting task row with TTD None values."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        from radiator.commands.models.time_to_market_models import TaskData

        task = TaskData(
            id=1,
            key="CPO-123",
            group_value="Author1",
            author="Author1",
            team=None,
            summary="Test Task",
            created_at=datetime(2025, 1, 1),
        )

        # Test with TTD None
        row = generator._format_task_row(
            task, ttm=15, quarter_name="Q1", tail=5, devlt=8, ttd=None, ttd_quarter=None
        )

        assert row["TTD"] == ""
        assert row["Квартал TTD"] == ""

        # Test with TTD values
        row = generator._format_task_row(
            task,
            ttm=15,
            quarter_name="Q1",
            tail=5,
            devlt=8,
            ttd=12,
            ttd_quarter="2025.Q1",
        )

        assert row["TTD"] == 12
        assert row["Квартал TTD"] == "2025.Q1"

    def test_ttm_details_csv_has_pause_columns(self, test_reports_dir):
        """Test that generated CSV includes Пауза and TTD Pause columns."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock the methods to return empty data
        generator._collect_csv_rows = Mock(return_value=[])
        generator._load_quarters = Mock(return_value=[])
        generator._load_done_statuses = Mock(return_value=[])

        # Generate CSV
        output_path = f"{test_reports_dir}/ttm_details_pause.csv"
        result_path = generator.generate_csv(output_path)

        # Verify file was created
        assert Path(result_path).exists()

        # Check CSV headers include pause columns
        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.strip().split("\n")
        headers = lines[0].split(",")

        # Check headers include Пауза after TTM and TTD Pause after TTD
        expected_headers = [
            "Ключ задачи",
            "Название",
            "Автор",
            "Команда",
            "Квартал",
            "TTM",
            "Пауза",  # New pause column after TTM
            "Tail",
            "DevLT",
            "TTD",
            "TTD Pause",  # New TTD pause column after TTD
            "Квартал TTD",
        ]
        assert headers == expected_headers

    def test_calculate_pause_for_task_with_pause_status(self, test_reports_dir):
        """Test pause calculation for task with pause status."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock metrics service
        generator.metrics_service.calculate_pause_time = Mock(return_value=5)

        # Mock history data
        mock_history = [
            Mock(status="Создана", start_date=datetime(2025, 1, 1)),
            Mock(status="Приостановлено", start_date=datetime(2025, 1, 5)),
            Mock(status="В работе", start_date=datetime(2025, 1, 8)),
        ]

        # Test pause calculation
        result = generator._calculate_pause(1, mock_history)

        # Verify metrics service was called correctly
        generator.metrics_service.calculate_pause_time.assert_called_once_with(
            mock_history
        )
        assert result == 5

    def test_calculate_ttd_pause_for_task_with_ready_status(self, test_reports_dir):
        """Test TTD pause calculation for task with ready status."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock metrics service
        generator.metrics_service.calculate_pause_time_up_to_date = Mock(return_value=3)

        # Mock history data with ready status
        mock_history = [
            Mock(status="Создана", start_date=datetime(2025, 1, 1)),
            Mock(status="Приостановлено", start_date=datetime(2025, 1, 3)),
            Mock(status="Готова к разработке", start_date=datetime(2025, 1, 5)),
        ]

        # Test TTD pause calculation
        result = generator._calculate_ttd_pause(1, mock_history)

        # Verify metrics service was called correctly
        generator.metrics_service.calculate_pause_time_up_to_date.assert_called_once_with(
            mock_history, datetime(2025, 1, 5)
        )
        assert result == 3

    def test_collect_csv_rows_with_pause_metrics(self, test_reports_dir):
        """Test collecting CSV rows with pause metrics calculation."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock quarters and tasks
        from radiator.commands.models.time_to_market_models import Quarter, TaskData

        quarters = [
            Quarter(
                name="2025.Q1",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 3, 31),
            )
        ]
        tasks = [
            TaskData(
                id=1,
                key="CPO-123",
                group_value="Author1",
                author="Author1",
                team=None,
                summary="Task 1",
                created_at=datetime(2025, 1, 1),
            ),
            TaskData(
                id=2,
                key="CPO-456",
                group_value="Author2",
                author="Author2",
                team=None,
                summary="Task 2",
                created_at=datetime(2025, 1, 1),
            ),
        ]

        # Mock methods
        generator._load_quarters = Mock(return_value=quarters)
        generator._load_done_statuses = Mock(return_value=["done"])
        generator._get_ttm_tasks_for_quarter = Mock(return_value=tasks)
        generator.data_service.get_task_history = Mock(return_value=[])  # Mock history
        generator._calculate_ttm = Mock(side_effect=[15, 20])
        generator._calculate_tail = Mock(side_effect=[5, None])
        generator._calculate_devlt = Mock(side_effect=[8, None])
        generator._calculate_ttd = Mock(side_effect=[12, None])
        generator._get_ttd_target_date = Mock(side_effect=[datetime(2025, 1, 5), None])
        generator._determine_quarter_for_date = Mock(side_effect=["2025.Q1", None])
        generator._calculate_pause = Mock(side_effect=[3, 7])  # Mock pause
        generator._calculate_ttd_pause = Mock(side_effect=[2, None])  # Mock TTD pause

        # Test collecting rows
        rows = generator._collect_csv_rows()

        # Verify pause metrics are calculated
        assert len(rows) == 2
        row1, row2 = rows

        # Check pause values
        assert row1["Пауза"] == 3
        assert row1["TTD Pause"] == 2
        assert row2["Пауза"] == 7
        assert row2["TTD Pause"] == ""

        # Verify pause methods were called
        assert generator._calculate_pause.call_count == 2
        assert generator._calculate_ttd_pause.call_count == 2

    def test_format_task_row_with_pause_none(self, test_reports_dir):
        """Test formatting task row with pause None values."""
        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        from radiator.commands.models.time_to_market_models import TaskData

        task = TaskData(
            id=1,
            key="CPO-123",
            group_value="Author1",
            author="Author1",
            team=None,
            summary="Test Task",
            created_at=datetime(2025, 1, 1),
        )

        # Test with pause None
        row = generator._format_task_row(
            task,
            ttm=15,
            quarter_name="Q1",
            tail=5,
            devlt=8,
            ttd=12,
            ttd_quarter="2025.Q1",
            pause=None,
            ttd_pause=None,
        )

        assert row["Пауза"] == ""
        assert row["TTD Pause"] == ""

        # Test with pause values
        row = generator._format_task_row(
            task,
            ttm=15,
            quarter_name="Q1",
            tail=5,
            devlt=8,
            ttd=12,
            ttd_quarter="2025.Q1",
            pause=3,
            ttd_pause=2,
        )

        assert row["Пауза"] == 3
        assert row["TTD Pause"] == 2


if __name__ == "__main__":
    pytest.main([__file__])
