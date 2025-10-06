"""Tests for task details CSV generation."""

import csv
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from radiator.commands.generate_time_to_market_report import (
    GenerateTimeToMarketReportCommand,
)
from radiator.commands.models.time_to_market_models import (
    GroupBy,
    GroupMetrics,
    QuarterReport,
    ReportType,
    StatusMapping,
    TaskData,
    TimeMetrics,
    TimeToMarketReport,
)


class TestTaskDetailsCSV:
    """Tests for task details CSV generation."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock quarter
        quarter = Mock()
        quarter.name = "Q1 2024"
        quarter.start_date = datetime(2024, 1, 1)
        quarter.end_date = datetime(2024, 3, 31)

        # Create mock report data
        self.report = TimeToMarketReport(
            quarters=[quarter],
            group_by=GroupBy.AUTHOR,
            status_mapping=StatusMapping(["Discovery"], ["Done"]),
            quarter_reports={},
        )

        # Create mock quarter report
        quarter_report = QuarterReport(
            quarter=quarter,
            groups={
                "Author1": GroupMetrics(
                    group_name="Author1",
                    ttd_metrics=TimeMetrics(
                        times=[5, 7, 3],
                        mean=5.0,
                        p85=7.0,
                        count=3,
                        pause_times=[1, 2, 0],
                        pause_mean=1.0,
                        pause_p85=2.0,
                    ),
                    ttm_metrics=TimeMetrics(
                        times=[8, 10, 6],
                        mean=8.0,
                        p85=10.0,
                        count=3,
                        pause_times=[2, 1, 0],
                        pause_mean=1.0,
                        pause_p85=2.0,
                    ),
                    tail_metrics=TimeMetrics(
                        times=[2, 3, 1],
                        mean=2.0,
                        p85=3.0,
                        count=3,
                        pause_times=[0, 1, 0],
                        pause_mean=0.33,
                        pause_p85=1.0,
                    ),
                    total_tasks=3,
                )
            },
        )

        self.report.quarter_reports = {"Q1 2024": quarter_report}

        # Create mock command
        self.command = GenerateTimeToMarketReportCommand(group_by=GroupBy.AUTHOR)
        self.command.report = self.report
        self.command.group_by = GroupBy.AUTHOR
        self.command.status_mapping = StatusMapping(["Discovery"], ["Done"])

        # Mock the report property
        self.command.report = self.report

        # Mock data service
        self.command.data_service = Mock()
        # Mock tasks for both TTD and TTM calls
        mock_tasks = [
            TaskData(
                id=1,
                key="CPO-1001",
                group_value="Author1",
                author="Author1",
                team=None,
                created_at=datetime(2024, 1, 15),
                summary="Test Task 1",
            ),
            TaskData(
                id=2,
                key="CPO-1002",
                group_value="Author1",
                author="Author1",
                team=None,
                created_at=datetime(2024, 2, 10),
                summary="Test Task 2",
            ),
        ]
        # Mock tasks for both TTD and TTM calls
        self.command.data_service.get_tasks_for_period.side_effect = [
            mock_tasks,
            mock_tasks,
        ]

        # Mock metrics service
        self.command.metrics_service = Mock()
        self.command.metrics_service.calculate_time_to_delivery.return_value = 5
        self.command.metrics_service.calculate_time_to_market.return_value = 8
        self.command.metrics_service.calculate_tail_metric.return_value = 2
        self.command.metrics_service.calculate_pause_time.return_value = 1

        # Mock task history
        self.command.data_service.get_task_history.return_value = [
            Mock(status="New", start_date=datetime(2024, 1, 1), end_date=None),
            Mock(status="Done", start_date=datetime(2024, 1, 5), end_date=None),
        ]

    def test_generate_task_details_csv_basic(self):
        """Test basic CSV generation functionality."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as temp_file:
            temp_path = temp_file.name

        try:
            # Generate CSV
            result = self.command.generate_task_details_csv(temp_path)

            # Verify file was created
            assert result == temp_path
            assert os.path.exists(temp_path)

            # Read and verify content
            with open(temp_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                # Verify headers
                expected_headers = [
                    "Автор",
                    "Команда",
                    "Ключ задачи",
                    "Название",
                    "TTD",
                    "TTM",
                    "Tail",
                    "Пауза",
                    "Квартал",
                ]
                assert reader.fieldnames == expected_headers

                # Verify we have data
                assert len(rows) > 0

                # Verify first row structure
                first_row = rows[0]
                assert "Автор" in first_row
                assert "Команда" in first_row
                assert "Ключ задачи" in first_row
                assert "Название" in first_row
                assert "TTD" in first_row
                assert "TTM" in first_row
                assert "Tail" in first_row
                assert "Пауза" in first_row
                assert "Квартал" in first_row

        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_generate_task_details_csv_data_content(self):
        """Test that CSV contains correct data."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as temp_file:
            temp_path = temp_file.name

        try:
            # Generate CSV
            self.command.generate_task_details_csv(temp_path)

            # Read and verify content
            with open(temp_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                # Verify we have the expected number of rows
                assert len(rows) == 2  # Two tasks

                # Verify first task data
                first_row = rows[0]
                assert first_row["Автор"] == "Author1"
                assert first_row["Ключ задачи"] == "CPO-1001"
                assert first_row["Название"] == "Test Task 1"
                assert first_row["TTD"] == "5"
                assert first_row["TTM"] == "8"
                assert first_row["Tail"] == "2"
                assert first_row["Пауза"] == "1"
                assert first_row["Квартал"] == "Q1 2024"

                # Verify second task data
                second_row = rows[1]
                assert second_row["Автор"] == "Author1"
                assert second_row["Ключ задачи"] == "CPO-1002"
                assert second_row["Название"] == "Test Task 2"
                assert second_row["TTD"] == "5"
                assert second_row["TTM"] == "8"
                assert second_row["Tail"] == "2"
                assert second_row["Пауза"] == "1"
                assert second_row["Квартал"] == "Q1 2024"

        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_generate_task_details_csv_empty_metrics(self):
        """Test CSV generation with empty metrics."""
        # Mock metrics service to return None for some metrics
        self.command.metrics_service.calculate_time_to_delivery.return_value = None
        self.command.metrics_service.calculate_time_to_market.return_value = 8
        self.command.metrics_service.calculate_tail_metric.return_value = None

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as temp_file:
            temp_path = temp_file.name

        try:
            # Generate CSV
            self.command.generate_task_details_csv(temp_path)

            # Read and verify content
            with open(temp_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                # Verify first task data with None metrics
                first_row = rows[0]
                assert first_row["TTD"] == ""  # None should be empty string
                assert first_row["TTM"] == "8"
                assert first_row["Tail"] == ""  # None should be empty string
                assert first_row["Пауза"] == "1"  # Pause time should be calculated

        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_generate_task_details_csv_no_report_data(self):
        """Test CSV generation when no report data is available."""
        command = GenerateTimeToMarketReportCommand(group_by=GroupBy.AUTHOR)
        command.report = None

        result = command.generate_task_details_csv()

        # Should return empty string when no report data
        assert result == ""

    def test_generate_task_details_csv_default_filename(self):
        """Test CSV generation with default filename."""
        # Mock datetime to get predictable filename
        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 15, 12, 30, 45)
            mock_datetime.strftime = datetime.strftime

            result = self.command.generate_task_details_csv()

            # Should generate filename with timestamp
            assert "task_details_" in result
            assert "20240115_123045" in result
            assert result.endswith(".csv")

    def test_generate_task_details_csv_multiple_quarters(self):
        """Test CSV generation with multiple quarters."""
        # Add second quarter
        quarter2 = Mock()
        quarter2.name = "Q2 2024"
        quarter2.start_date = datetime(2024, 4, 1)
        quarter2.end_date = datetime(2024, 6, 30)
        self.report.quarters.append(quarter2)

        quarter_report2 = QuarterReport(
            quarter=quarter2,
            groups={
                "Author1": GroupMetrics(
                    group_name="Author1",
                    ttd_metrics=TimeMetrics(
                        times=[],
                        mean=None,
                        p85=None,
                        count=0,
                        pause_times=[],
                        pause_mean=None,
                        pause_p85=None,
                    ),
                    ttm_metrics=TimeMetrics(
                        times=[6, 8],
                        mean=7.0,
                        p85=8.0,
                        count=2,
                        pause_times=[0, 0],
                        pause_mean=0.0,
                        pause_p85=0.0,
                    ),
                    tail_metrics=TimeMetrics(
                        times=[1, 2],
                        mean=1.5,
                        p85=2.0,
                        count=2,
                        pause_times=[0, 0],
                        pause_mean=0.0,
                        pause_p85=0.0,
                    ),
                    total_tasks=2,
                )
            },
        )

        self.report.quarter_reports["Q2 2024"] = quarter_report2

        # Mock data service to return different tasks for Q2
        # For TTD tasks
        self.command.data_service.get_tasks_for_period.side_effect = [
            # Q1 TTD tasks
            [
                TaskData(
                    id=1,
                    key="CPO-1001",
                    group_value="Author1",
                    author="Author1",
                    team=None,
                    created_at=datetime(2024, 1, 15),
                    summary="Q1 Task 1",
                )
            ],
            # Q1 TTM tasks
            [
                TaskData(
                    id=1,
                    key="CPO-1001",
                    group_value="Author1",
                    author="Author1",
                    team=None,
                    created_at=datetime(2024, 1, 15),
                    summary="Q1 Task 1",
                )
            ],
            # Q2 TTD tasks
            [
                TaskData(
                    id=3,
                    key="CPO-1003",
                    group_value="Author1",
                    author="Author1",
                    team=None,
                    created_at=datetime(2024, 4, 20),
                    summary="Q2 Task 1",
                )
            ],
            # Q2 TTM tasks
            [
                TaskData(
                    id=3,
                    key="CPO-1003",
                    group_value="Author1",
                    author="Author1",
                    team=None,
                    created_at=datetime(2024, 4, 20),
                    summary="Q2 Task 1",
                )
            ],
        ]

        # Mock task history for both tasks
        self.command.data_service.get_task_history.return_value = [
            Mock(status="New", start_date=datetime(2024, 1, 1), end_date=None),
            Mock(status="Done", start_date=datetime(2024, 1, 5), end_date=None),
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as temp_file:
            temp_path = temp_file.name

        try:
            # Generate CSV
            result = self.command.generate_task_details_csv(temp_path)

            # Verify file was created
            assert result == temp_path
            assert os.path.exists(temp_path)

            # Read and verify content
            with open(temp_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                # Should have tasks from both quarters
                assert len(rows) == 2

                # Verify quarters are different
                quarters = set(row["Квартал"] for row in rows)
                assert "Q1 2024" in quarters
                assert "Q2 2024" in quarters

        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_generate_task_details_csv_error_handling(self):
        """Test CSV generation error handling."""
        # Mock data service to raise exception
        self.command.data_service.get_tasks_for_period.side_effect = Exception(
            "Database error"
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False
        ) as temp_file:
            temp_path = temp_file.name

        try:
            # Should handle error gracefully
            result = self.command.generate_task_details_csv(temp_path)

            # Should return empty string on error
            assert result == ""

        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__])
