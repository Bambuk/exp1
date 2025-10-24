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

        # Mock new method for date range (all tasks at once)
        all_mock_tasks = mock_tasks_q1 + mock_tasks_q2
        generator._get_ttm_tasks_for_date_range_corrected = Mock(
            return_value=all_mock_tasks
        )

        # Mock quarter determination
        generator._determine_quarter_for_ttm = Mock(side_effect=["Q1", "Q1", "Q2"])

        # Mock data service
        generator.data_service.get_task_history = Mock(return_value=[])

        # Mock all calculation methods
        generator._calculate_ttm = Mock(side_effect=[15, 20, 10])
        generator._calculate_tail = Mock(side_effect=[None, None, None])
        generator._calculate_devlt = Mock(side_effect=[None, None, None])
        generator._calculate_ttd = Mock(side_effect=[None, None, None])
        generator._calculate_ttd_quarter = Mock(side_effect=[None, None, None])
        generator._calculate_pause = Mock(side_effect=[None, None, None])
        generator._calculate_ttd_pause = Mock(side_effect=[None, None, None])
        generator._calculate_discovery_backlog_days = Mock(
            side_effect=[None, None, None]
        )
        generator._calculate_ready_for_dev_days = Mock(side_effect=[None, None, None])

        # Mock returns calculation
        generator._calculate_all_returns_batched = Mock(
            return_value={"CPO-123": (0, 0), "CPO-456": (0, 0), "CPO-789": (0, 0)}
        )

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
        generator._get_ttm_tasks_for_date_range_corrected.assert_called_once()
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
                "Discovery backlog (дни)": "",
                "Готова к разработке (дни)": "",
                "Возвраты с Testing": "",
                "Возвраты с Внешний тест": "",
                "Всего возвратов": "",
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
                "Discovery backlog (дни)": "",
                "Готова к разработке (дни)": "",
                "Возвраты с Testing": "",
                "Возвраты с Внешний тест": "",
                "Всего возвратов": "",
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
                "Discovery backlog (дни)",
                "Готова к разработке (дни)",
                "Возвраты с Testing",
                "Возвраты с Внешний тест",
                "Всего возвратов",
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
                    "Discovery backlog (дни)",
                    "Готова к разработке (дни)",
                    "Возвраты с Testing",
                    "Возвраты с Внешний тест",
                    "Всего возвратов",
                    "Квартал TTD",
                ]
                assert headers == expected_headers

                # If there are data rows, check format
                if len(rows) > 1:
                    # Check that data rows have correct number of columns
                    for i, row in enumerate(rows[1:], 1):
                        assert (
                            len(row) == 17
                        ), f"Row {i} has {len(row)} columns, expected 17"

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
                "Discovery backlog (дни)": "",
                "Готова к разработке (дни)": "",
                "Возвраты с Testing": "",
                "Возвраты с Внешний тест": "",
                "Всего возвратов": "",
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
                "Discovery backlog (дни)",
                "Готова к разработке (дни)",
                "Возвраты с Testing",
                "Возвраты с Внешний тест",
                "Всего возвратов",
                "Квартал TTD",
            ]
            assert headers == expected_headers

            # Check first data row has Tail column
            row1 = lines[1]
            assert (
                len(row1) == 17
            )  # 17 columns including Пауза, Tail, DevLT, TTD, TTD Pause, Discovery backlog, Готова к разработке, returns, and Квартал TTD
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
                "Discovery backlog (дни)": "",
                "Готова к разработке (дни)": "",
                "Возвраты с Testing": "",
                "Возвраты с Внешний тест": "",
                "Всего возвратов": "",
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
                "Discovery backlog (дни)",
                "Готова к разработке (дни)",
                "Возвраты с Testing",
                "Возвраты с Внешний тест",
                "Всего возвратов",
                "Квартал TTD",
            ]
            assert headers == expected_headers

            # Check first data row has DevLT column
            row1 = lines[1]
            assert (
                len(row1) == 17
            )  # 17 columns including Пауза, DevLT, TTD, TTD Pause, Discovery backlog, Готова к разработке, returns, and Квартал TTD
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

        # Mock new method for date range (all tasks at once)
        all_mock_tasks = mock_tasks_q1 + mock_tasks_q2
        generator._get_ttm_tasks_for_date_range_corrected = Mock(
            return_value=all_mock_tasks
        )

        # Mock quarter determination
        generator._determine_quarter_for_ttm = Mock(side_effect=["Q1", "Q1", "Q2"])

        # Mock data service
        generator.data_service.get_task_history = Mock(return_value=[])

        # Mock all calculation methods
        generator._calculate_ttm = Mock(side_effect=[15, 20, 10])
        generator._calculate_tail = Mock(side_effect=[5, None, 3])
        generator._calculate_devlt = Mock(side_effect=[8, None, 6])
        generator._calculate_ttd = Mock(side_effect=[None, None, None])
        generator._calculate_ttd_quarter = Mock(side_effect=[None, None, None])
        generator._calculate_pause = Mock(side_effect=[None, None, None])
        generator._calculate_ttd_pause = Mock(side_effect=[None, None, None])
        generator._calculate_discovery_backlog_days = Mock(
            side_effect=[None, None, None]
        )
        generator._calculate_ready_for_dev_days = Mock(side_effect=[None, None, None])

        # Mock returns calculation
        generator._calculate_all_returns_batched = Mock(
            return_value={"CPO-123": (0, 0), "CPO-456": (0, 0), "CPO-789": (0, 0)}
        )

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
        generator._get_ttm_tasks_for_date_range_corrected.assert_called_once()
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
                    "Discovery backlog (дни)",
                    "Готова к разработке (дни)",
                    "Возвраты с Testing",
                    "Возвраты с Внешний тест",
                    "Всего возвратов",
                    "Квартал TTD",
                ]
                assert headers == expected_headers

                # If there are data rows, check format
                if len(rows) > 1:
                    # Check that data rows have correct number of columns
                    for i, row in enumerate(rows[1:], 1):
                        assert (
                            len(row) == 17
                        ), f"Row {i} has {len(row)} columns, expected 17"

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
            "Discovery backlog (дни)",
            "Готова к разработке (дни)",
            "Возвраты с Testing",
            "Возвраты с Внешний тест",
            "Всего возвратов",
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
        # Mock new method for date range (all tasks at once)
        generator._get_ttm_tasks_for_date_range_corrected = Mock(return_value=tasks)

        # Mock quarter determination
        generator._determine_quarter_for_ttm = Mock(return_value="2025.Q1")

        # Mock data service
        generator.data_service.get_task_history = Mock(return_value=[])

        # Mock all calculation methods
        generator._calculate_ttm = Mock(side_effect=[15, 20])
        generator._calculate_tail = Mock(side_effect=[None, None])
        generator._calculate_devlt = Mock(side_effect=[None, None])
        generator._calculate_ttd = Mock(side_effect=[12, None])
        generator._get_ttd_target_date = Mock(side_effect=[datetime(2025, 1, 5), None])
        generator._determine_quarter_for_date = Mock(side_effect=["2025.Q1", None])
        generator._calculate_ttd_quarter = Mock(side_effect=["2025.Q1", None])
        generator._calculate_pause = Mock(side_effect=[None, None])
        generator._calculate_ttd_pause = Mock(side_effect=[None, None])
        generator._calculate_discovery_backlog_days = Mock(side_effect=[None, None])
        generator._calculate_ready_for_dev_days = Mock(side_effect=[None, None])

        # Mock returns calculation
        generator._calculate_all_returns_batched = Mock(
            return_value={"CPO-123": (0, 0), "CPO-456": (0, 0)}
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
        # Note: _get_ttd_target_date and _determine_quarter_for_date are not used in new optimized logic

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
            "Discovery backlog (дни)",
            "Готова к разработке (дни)",
            "Возвраты с Testing",
            "Возвраты с Внешний тест",
            "Всего возвратов",
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
        # Mock new method for date range (all tasks at once)
        generator._get_ttm_tasks_for_date_range_corrected = Mock(return_value=tasks)

        # Mock quarter determination
        generator._determine_quarter_for_ttm = Mock(return_value="2025.Q1")

        # Mock data service
        generator.data_service.get_task_history = Mock(return_value=[])

        # Mock all calculation methods
        generator._calculate_ttm = Mock(side_effect=[15, 20])
        generator._calculate_tail = Mock(side_effect=[None, None])
        generator._calculate_devlt = Mock(side_effect=[None, None])
        generator._calculate_ttd = Mock(side_effect=[12, None])
        generator._get_ttd_target_date = Mock(side_effect=[datetime(2025, 1, 5), None])
        generator._determine_quarter_for_date = Mock(side_effect=["2025.Q1", None])
        generator._calculate_ttd_quarter = Mock(side_effect=["2025.Q1", None])
        generator._calculate_pause = Mock(side_effect=[None, None])
        generator._calculate_ttd_pause = Mock(side_effect=[None, None])
        generator._calculate_discovery_backlog_days = Mock(side_effect=[None, None])
        generator._calculate_ready_for_dev_days = Mock(side_effect=[None, None])

        # Mock returns calculation
        generator._calculate_all_returns_batched = Mock(
            return_value={"CPO-123": (0, 0), "CPO-456": (0, 0)}
        )
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

    def test_ttm_details_csv_has_status_duration_columns(self, test_reports_dir):
        """Test that CSV contains Discovery backlog and Готова к разработке columns."""
        import csv

        generator = TTMDetailsReportGenerator(Mock(), test_reports_dir)
        output_path = f"{test_reports_dir}/test_status_duration.csv"

        # Mock empty data to get just headers
        generator._collect_csv_rows = Mock(return_value=[])

        generator.generate_csv(output_path)

        # Read CSV and check headers
        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

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
            "Discovery backlog (дни)",  # New column after TTD Pause
            "Готова к разработке (дни)",  # New column after TTD Pause
            "Возвраты с Testing",
            "Возвраты с Внешний тест",
            "Всего возвратов",
            "Квартал TTD",
        ]
        assert headers == expected_headers

    def test_calculate_discovery_backlog_days_for_task_with_status(
        self, test_reports_dir
    ):
        """Test calculating Discovery backlog days for task with status."""
        from datetime import datetime
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock MetricsService.calculate_status_duration to return 5 days
        generator.metrics_service.calculate_status_duration = Mock(return_value=5)

        # Mock history data
        mock_history = [
            Mock(status="Discovery backlog", start_date=datetime(2025, 1, 1)),
            Mock(status="В работе", start_date=datetime(2025, 1, 6)),
        ]

        # Test calculating Discovery backlog days
        discovery_backlog_days = generator._calculate_discovery_backlog_days(
            task_id=1, history=mock_history
        )

        # Verify Discovery backlog days returns 5
        assert discovery_backlog_days == 5

        # Verify MetricsService was called with correct parameters
        generator.metrics_service.calculate_status_duration.assert_called_once()
        call_args = generator.metrics_service.calculate_status_duration.call_args
        assert call_args[0][0] == mock_history  # history
        assert call_args[0][1] == "Discovery backlog"  # status

    def test_calculate_ready_for_dev_days_for_task_with_status(self, test_reports_dir):
        """Test calculating Готова к разработке days for task with status."""
        from datetime import datetime
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock MetricsService.calculate_status_duration to return 3 days
        generator.metrics_service.calculate_status_duration = Mock(return_value=3)

        # Mock history data
        mock_history = [
            Mock(status="Готова к разработке", start_date=datetime(2025, 1, 1)),
            Mock(status="В работе", start_date=datetime(2025, 1, 4)),
        ]

        # Test calculating Готова к разработке days
        ready_for_dev_days = generator._calculate_ready_for_dev_days(
            task_id=1, history=mock_history
        )

        # Verify Готова к разработке days returns 3
        assert ready_for_dev_days == 3

        # Verify MetricsService was called with correct parameters
        generator.metrics_service.calculate_status_duration.assert_called_once()
        call_args = generator.metrics_service.calculate_status_duration.call_args
        assert call_args[0][0] == mock_history  # history
        assert call_args[0][1] == "Готова к разработке"  # status

    def test_collect_csv_rows_with_status_duration_metrics(self, test_reports_dir):
        """Test collecting CSV rows with status duration metrics."""
        from datetime import datetime
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )
        from radiator.commands.models.time_to_market_models import Quarter, TaskData

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock quarters
        quarters = [
            Quarter(
                name="Q1",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 3, 31),
            ),
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
        # Mock new method for date range (all tasks at once)
        generator._get_ttm_tasks_for_date_range_corrected = Mock(return_value=tasks)

        # Mock quarter determination
        generator._determine_quarter_for_ttm = Mock(return_value="2025.Q1")

        # Mock data service
        generator.data_service.get_task_history = Mock(return_value=[])

        # Mock all calculation methods
        generator._calculate_ttm = Mock(side_effect=[15, 20])
        generator._calculate_tail = Mock(side_effect=[None, None])
        generator._calculate_devlt = Mock(side_effect=[None, None])
        generator._calculate_ttd = Mock(side_effect=[12, None])
        generator._get_ttd_target_date = Mock(side_effect=[datetime(2025, 1, 5), None])
        generator._determine_quarter_for_date = Mock(side_effect=["2025.Q1", None])
        generator._calculate_ttd_quarter = Mock(side_effect=["2025.Q1", None])
        generator._calculate_pause = Mock(side_effect=[None, None])
        generator._calculate_ttd_pause = Mock(side_effect=[None, None])
        generator._calculate_discovery_backlog_days = Mock(side_effect=[None, None])
        generator._calculate_ready_for_dev_days = Mock(side_effect=[None, None])

        # Mock returns calculation
        generator._calculate_all_returns_batched = Mock(
            return_value={"CPO-123": (0, 0), "CPO-456": (0, 0)}
        )
        generator.data_service.get_task_history = Mock(return_value=[])  # Mock history
        generator._calculate_ttm = Mock(side_effect=[15, 20])
        generator._calculate_tail = Mock(side_effect=[5, None])
        generator._calculate_devlt = Mock(side_effect=[8, None])
        generator._calculate_ttd = Mock(side_effect=[12, None])
        generator._get_ttd_target_date = Mock(side_effect=[datetime(2025, 1, 5), None])
        generator._determine_quarter_for_date = Mock(side_effect=["2025.Q1", None])
        generator._calculate_pause = Mock(side_effect=[3, 7])  # Mock pause
        generator._calculate_ttd_pause = Mock(side_effect=[2, None])  # Mock TTD pause
        generator._calculate_discovery_backlog_days = Mock(
            side_effect=[4, None]
        )  # Mock Discovery backlog
        generator._calculate_ready_for_dev_days = Mock(
            side_effect=[6, None]
        )  # Mock Готова к разработке

        # Test collecting rows
        rows = generator._collect_csv_rows()

        # Verify status duration metrics are calculated
        assert len(rows) == 2
        row1, row2 = rows

        # Check status duration values
        assert row1["Discovery backlog (дни)"] == 4
        assert row1["Готова к разработке (дни)"] == 6
        assert row2["Discovery backlog (дни)"] == ""
        assert row2["Готова к разработке (дни)"] == ""

        # Verify status duration methods were called
        assert generator._calculate_discovery_backlog_days.call_count == 2
        assert generator._calculate_ready_for_dev_days.call_count == 2

    def test_format_task_row_with_status_duration_none(self, test_reports_dir):
        """Test formatting task row with status duration None values."""
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

        # Test with status duration None
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
            discovery_backlog_days=None,
            ready_for_dev_days=None,
        )

        assert row["Discovery backlog (дни)"] == ""
        assert row["Готова к разработке (дни)"] == ""

        # Test with status duration values
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
            discovery_backlog_days=4,
            ready_for_dev_days=6,
        )

        assert row["Discovery backlog (дни)"] == 4
        assert row["Готова к разработке (дни)"] == 6

    def test_ttm_details_csv_has_returns_columns(self, test_reports_dir):
        """Test that CSV contains returns columns in correct order."""
        import csv

        generator = TTMDetailsReportGenerator(Mock(), test_reports_dir)
        output_path = f"{test_reports_dir}/test_returns.csv"
        generator._collect_csv_rows = Mock(return_value=[])
        generator.generate_csv(output_path)
        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
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
            "Discovery backlog (дни)",
            "Готова к разработке (дни)",
            "Возвраты с Testing",  # New column after Готова к разработке (дни)
            "Возвраты с Внешний тест",  # New column after Готова к разработке (дни)
            "Всего возвратов",  # New column after Готова к разработке (дни)
            "Квартал TTD",
        ]
        assert headers == expected_headers

    def test_generator_has_testing_returns_service(self, test_reports_dir):
        """Test that TTMDetailsReportGenerator has testing_returns_service attribute."""
        generator = TTMDetailsReportGenerator(Mock(), test_reports_dir)
        assert hasattr(generator, "testing_returns_service")
        assert generator.testing_returns_service is not None

    def test_calculate_testing_returns_for_task_with_fullstack(self, test_reports_dir):
        """Test calculating testing returns for task with FULLSTACK links."""
        from unittest.mock import Mock

        generator = TTMDetailsReportGenerator(Mock(), test_reports_dir)

        # Mock the testing returns service (new batched method)
        generator.testing_returns_service.calculate_testing_returns_for_cpo_task_batched = Mock(
            return_value=(3, 2)
        )

        # Test calculating returns
        testing_returns, external_returns = generator._calculate_testing_returns(
            "CPO-123"
        )

        # Verify results
        assert testing_returns == 3
        assert external_returns == 2

        # Verify service was called correctly
        generator.testing_returns_service.calculate_testing_returns_for_cpo_task_batched.assert_called_once_with(
            "CPO-123", generator.data_service.get_task_histories_by_keys_batch
        )

    def test_collect_csv_rows_with_returns_metrics(self, test_reports_dir):
        """Test collecting CSV rows with returns metrics."""
        from datetime import datetime
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )
        from radiator.commands.models.time_to_market_models import Quarter, TaskData

        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)
        quarters = [
            Quarter(
                name="Q1",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 3, 31),
            ),
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
        generator._load_quarters = Mock(return_value=quarters)
        generator._load_done_statuses = Mock(return_value=["done"])
        # Mock new method for date range (all tasks at once)
        generator._get_ttm_tasks_for_date_range_corrected = Mock(return_value=tasks)

        # Mock quarter determination
        generator._determine_quarter_for_ttm = Mock(return_value="2025.Q1")

        # Mock data service
        generator.data_service.get_task_history = Mock(return_value=[])

        # Mock all calculation methods
        generator._calculate_ttm = Mock(side_effect=[15, 20])
        generator._calculate_tail = Mock(side_effect=[None, None])
        generator._calculate_devlt = Mock(side_effect=[None, None])
        generator._calculate_ttd = Mock(side_effect=[12, None])
        generator._get_ttd_target_date = Mock(side_effect=[datetime(2025, 1, 5), None])
        generator._determine_quarter_for_date = Mock(side_effect=["2025.Q1", None])
        generator._calculate_ttd_quarter = Mock(side_effect=["2025.Q1", None])
        generator._calculate_pause = Mock(side_effect=[None, None])
        generator._calculate_ttd_pause = Mock(side_effect=[None, None])
        generator._calculate_discovery_backlog_days = Mock(side_effect=[None, None])
        generator._calculate_ready_for_dev_days = Mock(side_effect=[None, None])

        # Mock returns calculation
        generator._calculate_all_returns_batched = Mock(
            return_value={"CPO-123": (3, 2), "CPO-456": (1, 0)}
        )
        rows = generator._collect_csv_rows()
        assert len(rows) == 2
        row1, row2 = rows
        assert row1["Возвраты с Testing"] == 3
        assert row1["Возвраты с Внешний тест"] == 2
        assert row1["Всего возвратов"] == 5  # 3 + 2
        assert row2["Возвраты с Testing"] == 1
        assert row2["Возвраты с Внешний тест"] == 0
        assert row2["Всего возвратов"] == 1  # 1 + 0
        # Note: _calculate_testing_returns is not used in new optimized logic

    def test_format_task_row_with_returns_none(self, test_reports_dir):
        """Test formatting task row with returns None values."""
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
            discovery_backlog_days=4,
            ready_for_dev_days=6,
            testing_returns=None,
            external_returns=None,
            total_returns=None,
        )
        assert row["Возвраты с Testing"] == ""
        assert row["Возвраты с Внешний тест"] == ""
        assert row["Всего возвратов"] == ""
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
            discovery_backlog_days=4,
            ready_for_dev_days=6,
            testing_returns=3,
            external_returns=2,
            total_returns=5,
        )
        assert row["Возвраты с Testing"] == 3
        assert row["Возвраты с Внешний тест"] == 2
        assert row["Всего возвратов"] == 5

    def test_batch_load_fullstack_links(self, test_reports_dir):
        """Test batch loading FULLSTACK links for multiple CPO tasks."""
        from unittest.mock import Mock

        generator = TTMDetailsReportGenerator(Mock(), test_reports_dir)

        # Mock the database query
        mock_task1 = Mock()
        mock_task1.key = "CPO-123"
        mock_task1.links = [
            {"type": {"id": "relates"}, "object": {"key": "FULLSTACK-456"}},
            {"type": {"id": "relates"}, "object": {"key": "FULLSTACK-789"}},
        ]

        mock_task2 = Mock()
        mock_task2.key = "CPO-456"
        mock_task2.links = [
            {"type": {"id": "relates"}, "object": {"key": "FULLSTACK-999"}}
        ]

        generator.testing_returns_service.db.query.return_value.filter.return_value.all.return_value = [
            (mock_task1.key, mock_task1.links),
            (mock_task2.key, mock_task2.links),
        ]

        # Test batch loading
        result = generator.testing_returns_service.batch_load_fullstack_links(
            ["CPO-123", "CPO-456"]
        )

        # Verify results
        assert result["CPO-123"] == ["FULLSTACK-456", "FULLSTACK-789"]
        assert result["CPO-456"] == ["FULLSTACK-999"]

        # Verify database was called once
        generator.testing_returns_service.db.query.assert_called_once()

    def test_calculate_testing_returns_batched(self, test_reports_dir):
        """Test batched calculation of testing returns."""
        from unittest.mock import Mock

        generator = TTMDetailsReportGenerator(Mock(), test_reports_dir)

        # Mock the service methods
        generator.testing_returns_service.get_fullstack_links = Mock(
            return_value=["FULLSTACK-123"]
        )
        generator.testing_returns_service.get_task_hierarchy = Mock(
            return_value=["FULLSTACK-123", "FULLSTACK-456"]
        )
        generator.testing_returns_service._batch_check_task_existence = Mock(
            return_value={"FULLSTACK-123", "FULLSTACK-456"}
        )

        # Mock batch histories function
        mock_batch_histories = Mock(
            return_value={
                "FULLSTACK-123": [Mock(status="Testing"), Mock(status="Done")],
                "FULLSTACK-456": [
                    Mock(status="Testing"),
                    Mock(status="Testing"),
                    Mock(status="Done"),
                ],
            }
        )

        # Mock calculate_testing_returns_for_task
        generator.testing_returns_service.calculate_testing_returns_for_task = Mock(
            side_effect=[(1, 0), (2, 0)]
        )

        # Test batched calculation
        (
            testing_returns,
            external_returns,
        ) = generator.testing_returns_service.calculate_testing_returns_for_cpo_task_batched(
            "CPO-123", mock_batch_histories
        )

        # Verify results
        assert testing_returns == 3  # 1 + 2
        assert external_returns == 0  # 0 + 0

        # Verify batch histories was called once with all task keys
        mock_batch_histories.assert_called_once_with(["FULLSTACK-123", "FULLSTACK-456"])

        # Verify individual calculations were called
        assert (
            generator.testing_returns_service.calculate_testing_returns_for_task.call_count
            == 2
        )


if __name__ == "__main__":
    pytest.main([__file__])
