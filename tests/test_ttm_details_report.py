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

        # Check new date headers after Квартал TTD
        import csv

        with open(result_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert "Квартал TTD" in headers
            assert "Создана" in headers
            assert "Начало работы" in headers
            assert "Завершено" in headers
            # Check order: new columns should be after Квартал TTD
            ttd_index = headers.index("Квартал TTD")
            created_index = headers.index("Создана")
            start_index = headers.index("Начало работы")
            done_index = headers.index("Завершено")
            assert created_index > ttd_index
            assert start_index > ttd_index
            assert done_index > ttd_index

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

        # Mock quarter determination - will be handled by stable_done mock
        # generator._determine_quarter_for_ttm = Mock(side_effect=["Q1", "Q1", "Q2"])

        # Mock data service with valid history containing done status for quarter determination
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_history_with_done = [
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 2, 15),  # Within Q1
                end_date=None,
            )
        ]
        generator.data_service.get_task_history = Mock(
            return_value=mock_history_with_done
        )

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
        generator._get_last_discovery_backlog_exit_date = Mock(
            side_effect=[datetime(2025, 1, 10), datetime(2025, 1, 15), None]
        )
        # Mock metrics_service._find_stable_done
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_stable_done_1 = StatusHistoryEntry(
            status="Done",
            status_display="Done",
            start_date=datetime(2025, 2, 1),  # In Q1
            end_date=None,
        )
        mock_stable_done_2 = StatusHistoryEntry(
            status="Done",
            status_display="Done",
            start_date=datetime(2025, 2, 15),  # In Q1
            end_date=None,
        )
        mock_stable_done_3 = StatusHistoryEntry(
            status="Done",
            status_display="Done",
            start_date=datetime(2025, 5, 1),  # In Q2
            end_date=None,
        )
        generator.metrics_service._find_stable_done = Mock(
            side_effect=[mock_stable_done_1, mock_stable_done_2, mock_stable_done_3]
        )

        # Mock returns calculation
        generator._calculate_all_returns_batched = Mock(
            return_value={"CPO-123": (0, 0), "CPO-456": (0, 0), "CPO-789": (0, 0)}
        )

        # Mock _get_unfinished_tasks to return empty list (no unfinished tasks in this test)
        generator._get_unfinished_tasks = Mock(return_value=[])

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
                "Создана": "",
                "Начало работы": "",
                "Завершено": "",
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
                "Создана": "",
                "Начало работы": "",
                "Завершено": "",
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
                "Создана",
                "Начало работы",
                "Завершено",
                "Разработка",
                "Завершена",
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

    def test_integration_with_real_db(self, test_reports_dir, db_session):
        """Test integration with real test database."""
        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Use test database session from fixture
        db = db_session
        # Create generator with test database
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
                "Создана",
                "Начало работы",
                "Завершено",
                "Разработка",
                "Завершена",
            ]
            assert headers == expected_headers

            # If there are data rows, check format
            if len(rows) > 1:
                # Check that data rows have correct number of columns
                for i, row in enumerate(rows[1:], 1):
                    assert (
                        len(row) == 22
                    ), f"Row {i} has {len(row)} columns, expected 22"

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
                "Создана",
                "Начало работы",
                "Завершено",
                "Разработка",
                "Завершена",
            ]
            assert headers == expected_headers

            # Check first data row has Tail column
            row1 = lines[1]  # csv.reader already returns list of lists
            assert (
                len(row1) == 22
            )  # 22 columns including Пауза, Tail, DevLT, TTD, TTD Pause, Discovery backlog, Готова к разработке, returns, Квартал TTD, new date columns, and Завершена
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
                "Создана",
                "Начало работы",
                "Завершено",
                "Разработка",
                "Завершена",
            ]
            assert headers == expected_headers

            # Check first data row has DevLT column
            row1 = lines[1]  # csv.reader already returns list of lists
            assert (
                len(row1) == 22
            )  # 22 columns including Пауза, DevLT, TTD, TTD Pause, Discovery backlog, Готова к разработке, returns, Квартал TTD, new date columns, and Завершена
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

        # Test formatting with DevLT = None and new date fields = None
        created_date = datetime(2025, 1, 1)
        row = generator._format_task_row(
            task,
            ttm=15,
            quarter_name="Q1",
            tail=None,
            devlt=None,
            created_at=None,
            last_discovery_backlog_exit_date=None,
            stable_done_date=None,
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
        assert row["Создана"] == ""  # None formatted as empty string
        assert row["Начало работы"] == ""  # None formatted as empty string
        assert row["Завершено"] == ""  # None formatted as empty string

        # Test formatting with DevLT = 10 and date fields with values
        row_with_devlt = generator._format_task_row(
            task,
            ttm=15,
            quarter_name="Q1",
            tail=5,
            devlt=10,
            created_at=created_date,
            last_discovery_backlog_exit_date=datetime(2025, 1, 10),
            stable_done_date=datetime(2025, 1, 20),
        )

        # Verify DevLT is formatted correctly
        assert row_with_devlt["TTM"] == 15
        assert row_with_devlt["Tail"] == 5
        assert row_with_devlt["DevLT"] == 10  # Valid value preserved
        assert row_with_devlt["Создана"] == "2025-01-01"
        assert row_with_devlt["Начало работы"] == "2025-01-10"
        assert row_with_devlt["Завершено"] == "2025-01-20"

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

        # Mock data service with valid history containing done status for quarter determination
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_history_with_done = [
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 2, 15),  # Within Q1
                end_date=None,
            )
        ]
        generator.data_service.get_task_history = Mock(
            return_value=mock_history_with_done
        )

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

        # Mock _get_unfinished_tasks to return empty list (no unfinished tasks in this test)
        generator._get_unfinished_tasks = Mock(return_value=[])

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

    def test_integration_ttm_details_with_tail(self, test_reports_dir, db_session):
        """Test integration with real test database and Tail column generation."""
        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Use test database session from fixture
        db = db_session
        # Create generator with test database
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
                "Создана",
                "Начало работы",
                "Завершено",
                "Разработка",
                "Завершена",
            ]
            assert headers == expected_headers

            # If there are data rows, check format
            if len(rows) > 1:
                # Check that data rows have correct number of columns
                for i, row in enumerate(rows[1:], 1):
                    assert (
                        len(row) == 22
                    ), f"Row {i} has {len(row)} columns, expected 22"

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
            "Создана",
            "Начало работы",
            "Завершено",
            "Разработка",
            "Завершена",
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
        generator._load_done_statuses = Mock(return_value=["Done"])
        # Mock new method for date range (all tasks at once)
        generator._get_ttm_tasks_for_date_range_corrected = Mock(return_value=tasks)

        # Mock quarter determination
        generator._determine_quarter_for_ttm = Mock(return_value="2025.Q1")

        # Mock data service with valid history containing done status for quarter determination
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_history_with_done = [
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 2, 15),  # Within Q1
                end_date=None,
            )
        ]
        generator.data_service.get_task_history = Mock(
            return_value=mock_history_with_done
        )

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
            "Создана",
            "Начало работы",
            "Завершено",
            "Разработка",
            "Завершена",
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
        generator._load_done_statuses = Mock(return_value=["Done"])
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
        # Mock data service with valid history containing done status for quarter determination
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_history_with_done = [
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 2, 15),  # Within Q1
                end_date=None,
            )
        ]
        generator.data_service.get_task_history = Mock(
            return_value=mock_history_with_done
        )
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
            "Создана",
            "Начало работы",
            "Завершено",
            "Разработка",
            "Завершена",
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
        generator._load_done_statuses = Mock(return_value=["Done"])
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
        # Mock data service with valid history containing done status for quarter determination
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_history_with_done = [
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 2, 15),  # Within Q1
                end_date=None,
            )
        ]
        generator.data_service.get_task_history = Mock(
            return_value=mock_history_with_done
        )
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
            "Создана",
            "Начало работы",
            "Завершено",
            "Разработка",
            "Завершена",
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
        generator._load_done_statuses = Mock(return_value=["Done"])
        # Mock new method for date range (all tasks at once)
        generator._get_ttm_tasks_for_date_range_corrected = Mock(return_value=tasks)

        # Mock quarter determination
        generator._determine_quarter_for_ttm = Mock(return_value="2025.Q1")

        # Mock data service with valid history containing done status for quarter determination
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_history_with_done = [
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 2, 15),  # Within Q1
                end_date=None,
            )
        ]
        generator.data_service.get_task_history = Mock(
            return_value=mock_history_with_done
        )

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

    def test_build_fullstack_hierarchy_no_cross_contamination(self, test_reports_dir):
        """
        Verify that build_fullstack_hierarchy_batched doesn't add
        unrelated FULLSTACK tasks to CPO tasks.
        """
        from unittest.mock import Mock

        generator = TTMDetailsReportGenerator(Mock(), test_reports_dir)

        # Mock two CPO tasks with different FULLSTACK hierarchies
        # CPO-A -> FULLSTACK-1 -> FULLSTACK-2, FULLSTACK-3
        # CPO-B -> FULLSTACK-4 -> FULLSTACK-5

        # Mock batch_load_fullstack_links
        generator.testing_returns_service.batch_load_fullstack_links = Mock(
            return_value={"CPO-A": ["FULLSTACK-1"], "CPO-B": ["FULLSTACK-4"]}
        )

        # Mock get_task_hierarchy_batch to return specific hierarchies
        def mock_hierarchy_batch(parent_keys):
            result = {}
            for parent in parent_keys:
                if parent == "FULLSTACK-1":
                    result[parent] = ["FULLSTACK-2", "FULLSTACK-3"]
                elif parent == "FULLSTACK-4":
                    result[parent] = ["FULLSTACK-5"]
                else:
                    result[parent] = []
            return result

        generator.testing_returns_service.get_task_hierarchy_batch = Mock(
            side_effect=mock_hierarchy_batch
        )

        # Test the method
        result = generator.testing_returns_service.build_fullstack_hierarchy_batched(
            ["CPO-A", "CPO-B"]
        )

        # Verify results
        assert "CPO-A" in result
        assert "CPO-B" in result

        cpo_a_tasks = set(result["CPO-A"])
        cpo_b_tasks = set(result["CPO-B"])

        # Expected: CPO-A should have FULLSTACK-1, FULLSTACK-2, FULLSTACK-3
        expected_a = {"FULLSTACK-1", "FULLSTACK-2", "FULLSTACK-3"}
        assert (
            cpo_a_tasks == expected_a
        ), f"CPO-A got {cpo_a_tasks}, expected {expected_a}"

        # Expected: CPO-B should have FULLSTACK-4, FULLSTACK-5
        expected_b = {"FULLSTACK-4", "FULLSTACK-5"}
        assert (
            cpo_b_tasks == expected_b
        ), f"CPO-B got {cpo_b_tasks}, expected {expected_b}"

        # CRITICAL: No cross-contamination - no intersection
        intersection = cpo_a_tasks & cpo_b_tasks
        assert len(intersection) == 0, f"Found cross-contamination: {intersection}"

    def test_calculate_returns_respects_cpo_boundaries(self, test_reports_dir):
        """
        Verify that testing returns are calculated only for
        FULLSTACK tasks actually related to each CPO task.
        """
        from unittest.mock import Mock

        generator = TTMDetailsReportGenerator(Mock(), test_reports_dir)

        # Mock the service methods to simulate the bug
        # This test will FAIL with current buggy implementation
        # and PASS after the fix

        # Mock batch_load_fullstack_links
        generator.testing_returns_service.batch_load_fullstack_links = Mock(
            return_value={
                "CPO-5770": ["FULLSTACK-25769"],
                "CPO-4370": ["FULLSTACK-17075", "FULLSTACK-25177"],
            }
        )

        # Mock get_task_hierarchy_batch to return realistic hierarchies
        def mock_hierarchy_batch(parent_keys):
            result = {}
            for parent in parent_keys:
                if parent == "FULLSTACK-25769":
                    result[parent] = [
                        "FULLSTACK-30816",
                        "FULLSTACK-31531",
                        "FULLSTACK-31530",
                        "FULLSTACK-30815",
                        "FULLSTACK-30818",
                    ]
                elif parent == "FULLSTACK-17075":
                    result[parent] = [
                        "FULLSTACK-31360",
                        "FULLSTACK-31355",
                        "FULLSTACK-31928",
                        "FULLSTACK-22855",
                        "FULLSTACK-30608",
                        "FULLSTACK-22854",
                        "FULLSTACK-22856",
                        "FULLSTACK-22857",
                        "FULLSTACK-25112",
                    ]
                elif parent == "FULLSTACK-25177":
                    result[parent] = []  # No children
                else:
                    result[parent] = []
            return result

        generator.testing_returns_service.get_task_hierarchy_batch = Mock(
            side_effect=mock_hierarchy_batch
        )

        # Test the method
        result = generator.testing_returns_service.build_fullstack_hierarchy_batched(
            ["CPO-5770", "CPO-4370"]
        )

        # Verify results
        cpo_5770_tasks = set(result["CPO-5770"])
        cpo_4370_tasks = set(result["CPO-4370"])

        # Expected for CPO-5770: 1 direct + 5 children = 6 tasks
        expected_5770 = {
            "FULLSTACK-25769",
            "FULLSTACK-30816",
            "FULLSTACK-31531",
            "FULLSTACK-31530",
            "FULLSTACK-30815",
            "FULLSTACK-30818",
        }
        assert (
            cpo_5770_tasks == expected_5770
        ), f"CPO-5770 got {len(cpo_5770_tasks)} tasks, expected 6. Got: {cpo_5770_tasks}"

        # Expected for CPO-4370: 2 direct + 9 children = 11 tasks
        expected_4370 = {
            "FULLSTACK-17075",
            "FULLSTACK-25177",
            "FULLSTACK-31360",
            "FULLSTACK-31355",
            "FULLSTACK-31928",
            "FULLSTACK-22855",
            "FULLSTACK-30608",
            "FULLSTACK-22854",
            "FULLSTACK-22856",
            "FULLSTACK-22857",
            "FULLSTACK-25112",
        }
        assert (
            cpo_4370_tasks == expected_4370
        ), f"CPO-4370 got {len(cpo_4370_tasks)} tasks, expected 11. Got: {cpo_4370_tasks}"

        # CRITICAL: No cross-contamination
        intersection = cpo_5770_tasks & cpo_4370_tasks
        assert len(intersection) == 0, f"Found cross-contamination: {intersection}"

    def test_get_last_discovery_backlog_exit_date_with_multiple_entries(
        self, test_reports_dir
    ):
        """Test getting last Discovery backlog exit date with multiple entries."""
        from datetime import datetime
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # History with multiple Discovery backlog entries
        mock_history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 1, 5),
            ),
            StatusHistoryEntry(
                status="Discovery backlog",
                status_display="Discovery backlog",
                start_date=datetime(2025, 1, 5),
                end_date=datetime(2025, 1, 10),  # First exit
            ),
            StatusHistoryEntry(
                status="В работе",
                status_display="В работе",
                start_date=datetime(2025, 1, 10),
                end_date=datetime(2025, 1, 15),
            ),
            StatusHistoryEntry(
                status="Discovery backlog",
                status_display="Discovery backlog",
                start_date=datetime(2025, 1, 15),
                end_date=datetime(2025, 1, 20),  # Last exit - should return this
            ),
            StatusHistoryEntry(
                status="В работе",
                status_display="В работе",
                start_date=datetime(2025, 1, 20),
                end_date=None,
            ),
        ]

        result = generator._get_last_discovery_backlog_exit_date(mock_history)

        # Should return end_date of last Discovery backlog entry
        assert result == datetime(2025, 1, 20)

    def test_get_last_discovery_backlog_exit_date_no_discovery_backlog(
        self, test_reports_dir
    ):
        """Test getting last Discovery backlog exit date when no Discovery backlog exists."""
        from datetime import datetime
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # History without Discovery backlog
        mock_history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 1, 5),
            ),
            StatusHistoryEntry(
                status="В работе",
                status_display="В работе",
                start_date=datetime(2025, 1, 5),
                end_date=None,
            ),
        ]

        result = generator._get_last_discovery_backlog_exit_date(mock_history)

        # Should return None
        assert result is None

    def test_get_last_discovery_backlog_exit_date_no_end_date(self, test_reports_dir):
        """Test getting last Discovery backlog exit date when current status is Discovery backlog."""
        from datetime import datetime
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # History with Discovery backlog as current status (no end_date)
        mock_history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 1, 5),
            ),
            StatusHistoryEntry(
                status="Discovery backlog",
                status_display="Discovery backlog",
                start_date=datetime(2025, 1, 5),
                end_date=None,  # Current status
            ),
        ]

        result = generator._get_last_discovery_backlog_exit_date(mock_history)

        # Should return None (no exit yet)
        assert result is None

    def test_get_last_discovery_backlog_exit_date_empty_history(self, test_reports_dir):
        """Test getting last Discovery backlog exit date with empty history."""
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Empty history
        mock_history = []

        result = generator._get_last_discovery_backlog_exit_date(mock_history)

        # Should return None
        assert result is None

    def test_has_valid_work_status_with_valid_entry(self, test_reports_dir):
        """Test _has_valid_work_status returns True for task with valid 'МП / В работе' status."""
        from datetime import datetime, timedelta
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # History with valid "МП / В работе" entry (>= 5 minutes)
        mock_history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 1, 5),
            ),
            StatusHistoryEntry(
                status="МП / В работе",
                status_display="МП / В работе",
                start_date=datetime(2025, 1, 5),
                end_date=datetime(2025, 1, 6),  # 1 day - valid (> 5 minutes)
            ),
        ]

        generator.data_service.get_task_history = Mock(return_value=mock_history)

        result = generator._has_valid_work_status(task_id=1, history=mock_history)

        assert result is True

    def test_has_valid_work_status_without_valid_entry(self, test_reports_dir):
        """Test _has_valid_work_status returns False for task without valid 'МП / В работе' status."""
        from datetime import datetime, timedelta
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # History without "МП / В работе" status
        mock_history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 1, 5),
            ),
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 1, 5),
                end_date=None,
            ),
        ]

        generator.data_service.get_task_history = Mock(return_value=mock_history)

        result = generator._has_valid_work_status(task_id=1, history=mock_history)

        assert result is False

    def test_has_valid_work_status_with_short_entry(self, test_reports_dir):
        """Test _has_valid_work_status returns False for task with short 'МП / В работе' entry (< 5 minutes)."""
        from datetime import datetime, timedelta
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # History with short "МП / В работе" entry (< 5 minutes)
        short_start = datetime(2025, 1, 5, 12, 0, 0)
        mock_history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 1, 1),
                end_date=short_start,
            ),
            StatusHistoryEntry(
                status="МП / В работе",
                status_display="МП / В работе",
                start_date=short_start,
                end_date=short_start
                + timedelta(seconds=200),  # 200 seconds - short (< 5 minutes)
            ),
        ]

        generator.data_service.get_task_history = Mock(return_value=mock_history)

        result = generator._has_valid_work_status(task_id=1, history=mock_history)

        assert result is False

    def test_has_valid_work_status_with_open_entry(self, test_reports_dir):
        """Test _has_valid_work_status returns False for task with open 'МП / В работе' entry (no end_date)."""
        from datetime import datetime
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db)

        # History with open "МП / В работе" entry (no end_date)
        mock_history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 1, 5),
            ),
            StatusHistoryEntry(
                status="МП / В работе",
                status_display="МП / В работе",
                start_date=datetime(2025, 1, 5),
                end_date=None,  # Open interval - not valid
            ),
        ]

        generator.data_service.get_task_history = Mock(return_value=mock_history)

        result = generator._has_valid_work_status(task_id=1, history=mock_history)

        assert result is False

    def test_ttm_details_csv_has_development_column(self, test_reports_dir):
        """Test that CSV contains 'Разработка' column at the end."""
        import csv

        generator = TTMDetailsReportGenerator(Mock(), test_reports_dir)
        output_path = f"{test_reports_dir}/test_development.csv"

        # Mock empty data to get just headers
        generator._collect_csv_rows = Mock(return_value=[])

        generator.generate_csv(output_path)

        # Read CSV and check headers
        with open(output_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

        # Check that "Разработка" is in headers and "Завершена" is the last column
        assert "Разработка" in headers
        assert headers[-1] == "Завершена"

    def test_format_task_row_with_development_flag(self, test_reports_dir):
        """Test formatting task row with development flag."""
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

        # Test with has_development=True
        row = generator._format_task_row(
            task,
            ttm=15,
            quarter_name="Q1",
            has_development=True,
        )

        assert row["Разработка"] == 1

        # Test with has_development=False
        row = generator._format_task_row(
            task,
            ttm=15,
            quarter_name="Q1",
            has_development=False,
        )

        assert row["Разработка"] == 0

    def test_collect_csv_rows_with_development_flag(self, test_reports_dir):
        """Test collecting CSV rows with development flag (1/0)."""
        from datetime import datetime, timedelta
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )
        from radiator.commands.models.time_to_market_models import (
            Quarter,
            StatusHistoryEntry,
            TaskData,
        )

        mock_db = Mock()
        generator = TTMDetailsReportGenerator(db=mock_db, config_dir=test_reports_dir)

        # Mock quarters
        mock_quarters = [
            Quarter(
                name="Q1",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 3, 31),
            )
        ]
        generator._load_quarters = Mock(return_value=mock_quarters)
        generator._load_done_statuses = Mock(return_value=["Done"])

        # Mock tasks
        mock_tasks = [
            TaskData(
                id=1,
                key="CPO-123",
                group_value="Author1",
                author="Author1",
                team=None,
                created_at=datetime(2025, 1, 1),
                summary="Task with development",
            ),
            TaskData(
                id=2,
                key="CPO-456",
                group_value="Author2",
                author="Author2",
                team=None,
                created_at=datetime(2025, 1, 1),
                summary="Task without development",
            ),
        ]
        generator._get_ttm_tasks_for_date_range_corrected = Mock(
            return_value=mock_tasks
        )

        # Mock history for task 1: with valid "МП / В работе" (>= 5 minutes)
        work_start = datetime(2025, 2, 1, 12, 0, 0)
        mock_history_with_work = [
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 2, 15),  # Within Q1
                end_date=None,
            ),
            StatusHistoryEntry(
                status="МП / В работе",
                status_display="МП / В работе",
                start_date=work_start,
                end_date=work_start + timedelta(days=1),  # 1 day - valid (> 5 minutes)
            ),
        ]

        # Mock history for task 2: without valid "МП / В работе"
        mock_history_without_work = [
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 2, 15),  # Within Q1
                end_date=None,
            ),
        ]

        # Mock get_task_history to return different histories for different tasks
        def get_history_side_effect(task_id):
            if task_id == 1:
                return mock_history_with_work
            elif task_id == 2:
                return mock_history_without_work
            return []

        generator.data_service.get_task_history = Mock(
            side_effect=get_history_side_effect
        )

        # Mock all calculation methods
        generator._calculate_ttm = Mock(side_effect=[15, 20])
        generator._calculate_tail = Mock(side_effect=[5, 3])
        generator._calculate_devlt = Mock(side_effect=[8, None])
        generator._calculate_ttd = Mock(side_effect=[None, None])
        generator._calculate_ttd_quarter = Mock(side_effect=[None, None])
        generator._calculate_pause = Mock(side_effect=[None, None])
        generator._calculate_ttd_pause = Mock(side_effect=[None, None])
        generator._calculate_discovery_backlog_days = Mock(side_effect=[None, None])
        generator._calculate_ready_for_dev_days = Mock(side_effect=[None, None])
        generator._get_last_discovery_backlog_exit_date = Mock(side_effect=[None, None])

        # Mock returns calculation
        generator._calculate_all_returns_batched = Mock(
            return_value={"CPO-123": (0, 0), "CPO-456": (0, 0)}
        )

        # Test collecting CSV rows
        rows = generator._collect_csv_rows()

        # Verify rows were collected
        assert len(rows) == 2

        # Check first row: task with valid "МП / В работе" should have "Разработка" = 1
        row1 = rows[0]
        assert row1["Ключ задачи"] == "CPO-123"
        assert row1["Разработка"] == 1

        # Check second row: task without valid "МП / В работе" should have "Разработка" = 0
        row2 = rows[1]
        assert row2["Ключ задачи"] == "CPO-456"
        assert row2["Разработка"] == 0

    def test_unfinished_tasks_included_in_report(self, test_reports_dir):
        """Test that unfinished tasks (with 'Готова к разработке' but no stable_done) are included in report."""
        from datetime import datetime
        from unittest.mock import Mock

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
        ]
        generator._load_quarters = Mock(return_value=mock_quarters)

        # Mock done statuses
        mock_done_statuses = ["Done", "Закрыт"]
        generator._load_done_statuses = Mock(return_value=mock_done_statuses)

        # Mock finished tasks (with stable_done)
        from radiator.commands.models.time_to_market_models import TaskData

        mock_finished_task = TaskData(
            id=1,
            key="CPO-FINISHED",
            group_value="Author1",
            author="Author1",
            team=None,
            created_at=datetime(2025, 1, 1),
            summary="Finished Task",
        )

        # Mock unfinished task (with 'Готова к разработке' but no stable_done)
        mock_unfinished_task = TaskData(
            id=2,
            key="CPO-UNFINISHED",
            group_value="Author2",
            author="Author2",
            team=None,
            created_at=datetime(2025, 1, 1),
            summary="Unfinished Task",
        )

        # Mock _get_ttm_tasks_for_date_range_corrected to return finished task
        generator._get_ttm_tasks_for_date_range_corrected = Mock(
            return_value=[mock_finished_task]
        )

        # Mock _get_unfinished_tasks to return unfinished task
        generator._get_unfinished_tasks = Mock(return_value=[mock_unfinished_task])

        # Mock history for finished task (with stable_done)
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        mock_finished_history = [
            StatusHistoryEntry(
                status="Готова к разработке",
                status_display="Готова к разработке",
                start_date=datetime(2025, 1, 10),
                end_date=datetime(2025, 1, 15),
            ),
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 2, 1),
                end_date=None,
            ),
        ]

        # Mock history for unfinished task (with 'Готова к разработке' but no done)
        mock_unfinished_history = [
            StatusHistoryEntry(
                status="Готова к разработке",
                status_display="Готова к разработке",
                start_date=datetime(2025, 1, 10),
                end_date=None,  # Still in this status
            ),
        ]

        # get_task_history вызывается для разных задач, используем функцию для возврата правильной истории
        def get_history_side_effect(task_id):
            if task_id == 1:  # Finished task
                return mock_finished_history
            elif task_id == 2:  # Unfinished task
                return mock_unfinished_history
            return []

        generator.data_service.get_task_history = Mock(
            side_effect=get_history_side_effect
        )

        # Mock stable_done: finished task has it, unfinished doesn't
        mock_stable_done_finished = StatusHistoryEntry(
            status="Done",
            status_display="Done",
            start_date=datetime(2025, 2, 1),
            end_date=None,
        )

        # _find_stable_done вызывается для разных задач, используем функцию
        def find_stable_done_side_effect(history, done_statuses):
            # Проверяем наличие Done статуса в истории
            if any(entry.status == "Done" for entry in history):
                return mock_stable_done_finished
            return None

        generator.metrics_service._find_stable_done = Mock(
            side_effect=find_stable_done_side_effect
        )

        # Mock all calculation methods - используем функции для поддержки повторных вызовов
        def calculate_ttm_side_effect(task_id, done_statuses, history=None):
            # Определяем по истории, какая задача
            if history and any(entry.status == "Done" for entry in history):
                return 15  # Finished task
            return None  # Unfinished task - будет использован _calculate_ttm_unfinished

        generator._calculate_ttm = Mock(side_effect=calculate_ttm_side_effect)

        # Mock _calculate_ttm_unfinished for unfinished tasks
        generator._calculate_ttm_unfinished = Mock(return_value=20)
        generator._calculate_tail = Mock(return_value=None)
        generator._calculate_devlt = Mock(return_value=None)
        generator._calculate_ttd = Mock(return_value=5)
        generator._calculate_ttd_quarter = Mock(return_value=None)
        generator._calculate_pause = Mock(return_value=None)
        generator._calculate_ttd_pause = Mock(return_value=None)
        generator._calculate_discovery_backlog_days = Mock(return_value=None)
        generator._calculate_ready_for_dev_days = Mock(return_value=None)
        generator._get_last_discovery_backlog_exit_date = Mock(
            return_value=datetime(2025, 1, 5)
        )
        generator._has_valid_work_status = Mock(return_value=False)

        # Mock returns calculation
        generator._calculate_all_returns_batched = Mock(
            return_value={"CPO-FINISHED": (0, 0), "CPO-UNFINISHED": (0, 0)}
        )

        # Test collecting CSV rows
        rows = generator._collect_csv_rows()

        # Verify both tasks are in the report
        assert len(rows) == 2

        # Find finished and unfinished tasks
        finished_row = next(r for r in rows if r["Ключ задачи"] == "CPO-FINISHED")
        unfinished_row = next(r for r in rows if r["Ключ задачи"] == "CPO-UNFINISHED")

        # Check finished task
        assert finished_row["Завершена"] == 1
        assert finished_row["Квартал"] == "Q1"  # Has quarter based on stable_done

        # Check unfinished task
        assert unfinished_row["Завершена"] == 0
        assert unfinished_row["Квартал"] == ""  # Empty quarter
        assert unfinished_row["TTM"] == 20  # TTM calculated to today

        # Test CSV generation
        output_path = f"{test_reports_dir}/ttm_details_with_unfinished.csv"
        result_path = generator.generate_csv(output_path)

        # Verify file was created
        assert Path(result_path).exists()

        # Verify CSV has "Завершена" column
        import csv

        with open(result_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            assert "Завершена" in headers

            # Read rows
            rows_list = list(reader)
            assert len(rows_list) == 2

            # Find tasks
            finished_csv = next(
                r for r in rows_list if r["Ключ задачи"] == "CPO-FINISHED"
            )
            unfinished_csv = next(
                r for r in rows_list if r["Ключ задачи"] == "CPO-UNFINISHED"
            )

            # Verify values
            assert finished_csv["Завершена"] == "1"
            assert unfinished_csv["Завершена"] == "0"
            assert unfinished_csv["Квартал"] == ""

    def test_get_unfinished_tasks_returns_tasks_without_stable_done(
        self, test_reports_dir
    ):
        """Test that _get_unfinished_tasks returns tasks that transitioned to 'Готова к разработке' but don't have stable_done."""
        from datetime import datetime
        from unittest.mock import Mock

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
        ]
        generator._load_quarters = Mock(return_value=mock_quarters)

        # Mock done statuses
        mock_done_statuses = ["Done", "Закрыт"]
        generator._load_done_statuses = Mock(return_value=mock_done_statuses)

        # Mock tasks that transitioned to "Готова к разработке"
        from radiator.commands.models.time_to_market_models import TaskData

        unfinished_task = TaskData(
            id=1,
            key="CPO-UNFINISHED",
            group_value="Author1",
            author="Author1",
            team=None,
            created_at=datetime(2025, 1, 1),
            summary="Unfinished Task",
        )

        finished_task = TaskData(
            id=2,
            key="CPO-FINISHED",
            group_value="Author2",
            author="Author2",
            team=None,
            created_at=datetime(2025, 1, 1),
            summary="Finished Task",
        )

        # Mock get_tasks_for_period to return both tasks
        from radiator.commands.models.time_to_market_models import GroupBy

        generator.data_service.get_tasks_for_period = Mock(
            return_value=[unfinished_task, finished_task]
        )
        generator.config_service.load_status_mapping = Mock()

        # Mock histories
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        unfinished_history = [
            StatusHistoryEntry(
                status="Готова к разработке",
                status_display="Готова к разработке",
                start_date=datetime(2025, 1, 10),
                end_date=None,
            ),
        ]

        finished_history = [
            StatusHistoryEntry(
                status="Готова к разработке",
                status_display="Готова к разработке",
                start_date=datetime(2025, 1, 10),
                end_date=datetime(2025, 1, 15),
            ),
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 2, 1),
                end_date=None,
            ),
        ]

        def get_history_side_effect(task_id):
            if task_id == 1:
                return unfinished_history
            elif task_id == 2:
                return finished_history
            return []

        generator.data_service.get_task_history = Mock(
            side_effect=get_history_side_effect
        )

        # Mock stable_done: unfinished task doesn't have it, finished task has it
        mock_stable_done_finished = StatusHistoryEntry(
            status="Done",
            status_display="Done",
            start_date=datetime(2025, 2, 1),
            end_date=None,
        )

        def find_stable_done_side_effect(history, done_statuses):
            if any(entry.status == "Done" for entry in history):
                return mock_stable_done_finished
            return None

        generator.metrics_service._find_stable_done = Mock(
            side_effect=find_stable_done_side_effect
        )

        # Test _get_unfinished_tasks
        result = generator._get_unfinished_tasks()

        # Verify only unfinished task is returned
        assert len(result) == 1
        assert result[0].key == "CPO-UNFINISHED"

    def test_get_unfinished_tasks_excludes_tasks_without_ready_status(
        self, test_reports_dir
    ):
        """Test that _get_unfinished_tasks excludes tasks that never transitioned to 'Готова к разработке'."""
        from datetime import datetime
        from unittest.mock import Mock

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
        ]
        generator._load_quarters = Mock(return_value=mock_quarters)

        # Mock done statuses
        mock_done_statuses = ["Done", "Закрыт"]
        generator._load_done_statuses = Mock(return_value=mock_done_statuses)

        # Mock get_tasks_for_period to return empty list (no tasks with "Готова к разработке")
        generator.data_service.get_tasks_for_period = Mock(return_value=[])
        generator.config_service.load_status_mapping = Mock()

        # Test _get_unfinished_tasks
        result = generator._get_unfinished_tasks()

        # Verify empty list is returned
        assert len(result) == 0

    def test_unfinished_tasks_returns_calculation(self, test_reports_dir):
        """Test that returns are correctly calculated for unfinished tasks."""
        from datetime import datetime
        from unittest.mock import Mock

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
        ]
        generator._load_quarters = Mock(return_value=mock_quarters)

        # Mock done statuses
        mock_done_statuses = ["Done", "Закрыт"]
        generator._load_done_statuses = Mock(return_value=mock_done_statuses)

        # Mock unfinished task with FULLSTACK links
        from radiator.commands.models.time_to_market_models import TaskData

        unfinished_task = TaskData(
            id=1,
            key="CPO-UNFINISHED",
            group_value="Author1",
            author="Author1",
            team=None,
            created_at=datetime(2025, 1, 1),
            summary="Unfinished Task",
        )

        generator._get_ttm_tasks_for_date_range_corrected = Mock(return_value=[])
        generator._get_unfinished_tasks = Mock(return_value=[unfinished_task])

        # Mock history
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        unfinished_history = [
            StatusHistoryEntry(
                status="Готова к разработке",
                status_display="Готова к разработке",
                start_date=datetime(2025, 1, 10),
                end_date=None,
            ),
        ]

        generator.data_service.get_task_history = Mock(return_value=unfinished_history)
        generator.metrics_service._find_stable_done = Mock(return_value=None)

        # Mock all calculation methods
        generator._calculate_ttm_unfinished = Mock(return_value=20)
        generator._calculate_tail = Mock(return_value=None)
        generator._calculate_devlt = Mock(return_value=None)
        generator._calculate_ttd = Mock(return_value=10)
        generator._calculate_ttd_quarter = Mock(return_value=None)
        generator._calculate_pause = Mock(return_value=None)
        generator._calculate_ttd_pause = Mock(return_value=None)
        generator._calculate_discovery_backlog_days = Mock(return_value=None)
        generator._calculate_ready_for_dev_days = Mock(return_value=None)
        generator._get_last_discovery_backlog_exit_date = Mock(return_value=None)
        generator._has_valid_work_status = Mock(return_value=False)

        # Mock returns calculation - незавершенная задача имеет возвраты
        generator._calculate_all_returns_batched = Mock(
            return_value={
                "CPO-UNFINISHED": (5, 3)
            }  # testing_returns=5, external_returns=3
        )

        # Test collecting CSV rows
        rows = generator._collect_csv_rows()

        # Verify unfinished task is in the report
        assert len(rows) == 1
        unfinished_row = rows[0]

        # Verify returns are correctly included
        assert unfinished_row["Ключ задачи"] == "CPO-UNFINISHED"
        assert unfinished_row["Возвраты с Testing"] == 5
        assert unfinished_row["Возвраты с Внешний тест"] == 3
        assert unfinished_row["Всего возвратов"] == 8

        # Verify _calculate_all_returns_batched was called with unfinished task key
        generator._calculate_all_returns_batched.assert_called_once()
        call_args = generator._calculate_all_returns_batched.call_args
        assert "CPO-UNFINISHED" in call_args[0][0]

    def test_collect_csv_rows_includes_unfinished_tasks_with_all_metrics(
        self, test_reports_dir
    ):
        """Test that unfinished tasks are included in CSV rows with all metrics calculated."""
        from datetime import datetime
        from unittest.mock import Mock

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
        ]
        generator._load_quarters = Mock(return_value=mock_quarters)

        # Mock done statuses
        mock_done_statuses = ["Done", "Закрыт"]
        generator._load_done_statuses = Mock(return_value=mock_done_statuses)

        # Mock finished task
        from radiator.commands.models.time_to_market_models import TaskData

        finished_task = TaskData(
            id=1,
            key="CPO-FINISHED",
            group_value="Author1",
            author="Author1",
            team=None,
            created_at=datetime(2025, 1, 1),
            summary="Finished Task",
        )

        # Mock unfinished task
        unfinished_task = TaskData(
            id=2,
            key="CPO-UNFINISHED",
            group_value="Author2",
            author="Author2",
            team=None,
            created_at=datetime(2025, 1, 1),
            summary="Unfinished Task",
        )

        # Mock tasks
        generator._get_ttm_tasks_for_date_range_corrected = Mock(
            return_value=[finished_task]
        )
        generator._get_unfinished_tasks = Mock(return_value=[unfinished_task])

        # Mock histories
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        finished_history = [
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 2, 1),
                end_date=None,
            ),
        ]

        unfinished_history = [
            StatusHistoryEntry(
                status="Готова к разработке",
                status_display="Готова к разработке",
                start_date=datetime(2025, 1, 10),
                end_date=None,
            ),
        ]

        def get_history_side_effect(task_id):
            if task_id == 1:
                return finished_history
            elif task_id == 2:
                return unfinished_history
            return []

        generator.data_service.get_task_history = Mock(
            side_effect=get_history_side_effect
        )

        # Mock stable_done
        mock_stable_done = StatusHistoryEntry(
            status="Done",
            status_display="Done",
            start_date=datetime(2025, 2, 1),
            end_date=None,
        )

        def find_stable_done_side_effect(history, done_statuses):
            if any(entry.status == "Done" for entry in history):
                return mock_stable_done
            return None

        generator.metrics_service._find_stable_done = Mock(
            side_effect=find_stable_done_side_effect
        )

        # Mock all calculation methods
        generator._calculate_ttm = Mock(return_value=15)
        generator._calculate_ttm_unfinished = Mock(return_value=20)
        generator._calculate_tail = Mock(return_value=5)
        generator._calculate_devlt = Mock(return_value=8)
        generator._calculate_ttd = Mock(return_value=10)
        generator._calculate_ttd_quarter = Mock(return_value="Q1")
        generator._calculate_pause = Mock(return_value=2)
        generator._calculate_ttd_pause = Mock(return_value=1)
        generator._calculate_discovery_backlog_days = Mock(return_value=3)
        generator._calculate_ready_for_dev_days = Mock(return_value=4)
        generator._get_last_discovery_backlog_exit_date = Mock(
            return_value=datetime(2025, 1, 5)
        )
        generator._has_valid_work_status = Mock(return_value=True)

        # Mock returns calculation
        generator._calculate_all_returns_batched = Mock(
            return_value={"CPO-FINISHED": (1, 2), "CPO-UNFINISHED": (3, 4)}
        )

        # Test collecting CSV rows
        rows = generator._collect_csv_rows()

        # Verify both tasks are in the report
        assert len(rows) == 2

        # Find tasks
        finished_row = next(r for r in rows if r["Ключ задачи"] == "CPO-FINISHED")
        unfinished_row = next(r for r in rows if r["Ключ задачи"] == "CPO-UNFINISHED")

        # Check finished task
        assert finished_row["Завершена"] == 1
        assert finished_row["Квартал"] == "Q1"
        assert finished_row["TTM"] == 15
        assert finished_row["Tail"] == 5
        assert finished_row["DevLT"] == 8
        assert finished_row["TTD"] == 10
        assert finished_row["Возвраты с Testing"] == 1
        assert finished_row["Возвраты с Внешний тест"] == 2
        assert finished_row["Всего возвратов"] == 3

        # Check unfinished task - all metrics should be calculated
        assert unfinished_row["Завершена"] == 0
        assert unfinished_row["Квартал"] == ""  # Empty quarter
        assert unfinished_row["TTM"] == 20  # Calculated using _calculate_ttm_unfinished
        assert unfinished_row["Tail"] == 5
        assert unfinished_row["DevLT"] == 8
        assert unfinished_row["TTD"] == 10
        assert unfinished_row["Пауза"] == 2
        assert unfinished_row["TTD Pause"] == 1
        assert unfinished_row["Discovery backlog (дни)"] == 3
        assert unfinished_row["Готова к разработке (дни)"] == 4
        assert unfinished_row["Возвраты с Testing"] == 3
        assert unfinished_row["Возвраты с Внешний тест"] == 4
        assert unfinished_row["Всего возвратов"] == 7
        assert unfinished_row["Разработка"] == 1

        # Verify _calculate_ttm_unfinished was called for unfinished task
        generator._calculate_ttm_unfinished.assert_called_once()

    def test_calculate_ttm_unfinished_without_pauses(self, test_reports_dir):
        """Test calculating TTM for unfinished task without pauses."""
        from datetime import datetime
        from unittest.mock import Mock, patch

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock done statuses
        mock_done_statuses = ["Done", "Закрыт"]
        generator._load_done_statuses = Mock(return_value=mock_done_statuses)

        # Mock history for unfinished task
        # Task created 10 days ago, still in progress
        from datetime import timedelta

        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        created_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        created_date = created_date - timedelta(days=10)

        mock_history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=created_date,
                end_date=created_date.replace(day=created_date.day + 1),
            ),
            StatusHistoryEntry(
                status="Готова к разработке",
                status_display="Готова к разработке",
                start_date=created_date.replace(day=created_date.day + 5),
                end_date=None,  # Still in this status
            ),
        ]

        generator.data_service.get_task_history = Mock(return_value=mock_history)

        # Mock metrics_service methods
        generator.metrics_service.ttm_strategy.calculate_start_date = Mock(
            return_value=created_date
        )
        generator.metrics_service.calculate_pause_time_up_to_date = Mock(return_value=0)

        # Test _calculate_ttm_unfinished
        from datetime import timezone

        with patch(
            "radiator.commands.generate_ttm_details_report.datetime"
        ) as mock_datetime:
            current_date = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            # Mock datetime.now to return timezone-aware datetime
            def mock_now(tz=None):
                return current_date

            mock_datetime.now = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = generator._calculate_ttm_unfinished(
                mock_history, mock_done_statuses
            )

        # Verify TTM is approximately 10 days (current_date - created_date)
        assert result is not None
        assert result >= 9  # Allow for small time differences
        assert result <= 11

    def test_calculate_ttm_unfinished_with_pauses(self, test_reports_dir):
        """Test calculating TTM for unfinished task with pauses."""
        from datetime import datetime, timedelta
        from unittest.mock import Mock, patch

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock done statuses
        mock_done_statuses = ["Done", "Закрыт"]
        generator._load_done_statuses = Mock(return_value=mock_done_statuses)

        # Mock history for unfinished task with pause
        from radiator.commands.models.time_to_market_models import StatusHistoryEntry

        created_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        created_date = created_date - timedelta(days=15)

        mock_history = [
            StatusHistoryEntry(
                status="Открыт",
                status_display="Открыт",
                start_date=created_date,
                end_date=created_date + timedelta(days=2),
            ),
            StatusHistoryEntry(
                status="Приостановлено",
                status_display="Приостановлено",
                start_date=created_date + timedelta(days=3),
                end_date=created_date + timedelta(days=6),
            ),
            StatusHistoryEntry(
                status="Готова к разработке",
                status_display="Готова к разработке",
                start_date=created_date + timedelta(days=7),
                end_date=None,  # Still in this status
            ),
        ]

        generator.data_service.get_task_history = Mock(return_value=mock_history)

        # Mock metrics_service methods
        generator.metrics_service.ttm_strategy.calculate_start_date = Mock(
            return_value=created_date
        )
        # 3 days of pause (from day 3 to day 6)
        generator.metrics_service.calculate_pause_time_up_to_date = Mock(return_value=3)

        # Test _calculate_ttm_unfinished
        from datetime import timezone

        current_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        # Create a mock datetime module that preserves datetime class but mocks now()
        import datetime as dt_module

        original_datetime = dt_module.datetime
        mock_datetime_class = type(
            "datetime",
            (original_datetime,),
            {
                "now": lambda tz=None: current_date,
                "__new__": original_datetime.__new__,
                "__init__": original_datetime.__init__,
            },
        )
        # Copy all attributes from original datetime
        for attr in dir(original_datetime):
            if not attr.startswith("_") and attr != "now":
                try:
                    setattr(mock_datetime_class, attr, getattr(original_datetime, attr))
                except (TypeError, AttributeError):
                    pass

        with patch(
            "radiator.commands.generate_ttm_details_report.datetime",
            mock_datetime_class,
        ):
            result = generator._calculate_ttm_unfinished(
                mock_history, mock_done_statuses
            )

        # Verify TTM = (current_date - created_date) - pause_time
        # Should be approximately 15 - 3 = 12 days
        assert result is not None
        assert result >= 11  # Allow for small time differences
        assert result <= 13

    def test_calculate_ttm_unfinished_empty_history(self, test_reports_dir):
        """Test calculating TTM for unfinished task with empty history returns None."""
        from unittest.mock import Mock

        from radiator.commands.generate_ttm_details_report import (
            TTMDetailsReportGenerator,
        )

        # Mock database session
        mock_db = Mock()

        # Create generator
        generator = TTMDetailsReportGenerator(db=mock_db)

        # Mock done statuses
        mock_done_statuses = ["Done", "Закрыт"]
        generator._load_done_statuses = Mock(return_value=mock_done_statuses)

        # Test _calculate_ttm_unfinished with empty history
        result = generator._calculate_ttm_unfinished([], mock_done_statuses)

        # Verify None is returned
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__])
