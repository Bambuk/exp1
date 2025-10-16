"""Tests for pause columns in task details CSV."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

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
from radiator.commands.services.data_service import DataService
from radiator.commands.services.metrics_service import MetricsService


class TestPauseColumnsInDetails:
    """Test pause columns in task details CSV."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = GenerateTimeToMarketReportCommand(group_by=GroupBy.AUTHOR)
        self.command.report = TimeToMarketReport(
            quarters=[],
            status_mapping=StatusMapping(["Discovery"], ["Done"]),
            group_by=GroupBy.AUTHOR,
            quarter_reports={},
        )
        self.command.group_by = GroupBy.AUTHOR
        self.command.status_mapping = StatusMapping(["Discovery"], ["Done"])

        # Mock services
        self.data_service = Mock(spec=DataService)
        self.metrics_service = Mock(spec=MetricsService)
        self.command.data_service = self.data_service
        self.command.metrics_service = self.metrics_service

    def test_ttd_pause_calculation_single_pause(self):
        """Test TTD pause calculation with single pause period."""
        # Task history with pause
        history = [
            StatusHistoryEntry(
                status="Создана",
                status_display="Создана",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 1),
            ),
            StatusHistoryEntry(
                status="Discovery backlog",
                status_display="Discovery backlog",
                start_date=datetime(2024, 1, 2),
                end_date=datetime(2024, 1, 2),
            ),
            StatusHistoryEntry(
                status="Приостановлено",
                status_display="Приостановлено",
                start_date=datetime(2024, 1, 5),
                end_date=datetime(2024, 1, 5),
            ),
            StatusHistoryEntry(
                status="Discovery backlog",
                status_display="Discovery backlog",
                start_date=datetime(2024, 1, 10),
                end_date=datetime(2024, 1, 10),
            ),
            StatusHistoryEntry(
                status="Готова к разработке",
                status_display="Готова к разработке",
                start_date=datetime(2024, 1, 15),
                end_date=datetime(2024, 1, 15),
            ),
        ]

        # Mock data service to return history
        self.data_service.get_task_history.return_value = history

        # Mock metrics service to return calculated values
        self.metrics_service.calculate_time_to_delivery.return_value = (
            10  # TTD without pause
        )
        self.metrics_service.calculate_pause_time_up_to_date.return_value = (
            5  # Pause time up to ready
        )

        # Create task data
        task_data = TaskData(
            id=1,
            key="CPO-123",
            group_value="test_author",
            author="test_author",
            team="test_team",
            created_at=datetime(2024, 1, 1),
            summary="Test task",
        )

        # Test pause calculation
        ttd_pause = self.command._calculate_ttd_pause(task_data)

        assert ttd_pause == 5
        self.metrics_service.calculate_pause_time_up_to_date.assert_called_once()

    def test_ttd_pause_calculation_multiple_pauses(self):
        """Test TTD pause calculation with multiple pause periods."""
        # Task history with multiple pauses
        history = [
            StatusHistoryEntry(
                status="Создана",
                status_display="Создана",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 1),
            ),
            StatusHistoryEntry(
                status="Discovery backlog",
                status_display="Discovery backlog",
                start_date=datetime(2024, 1, 2),
                end_date=datetime(2024, 1, 2),
            ),
            StatusHistoryEntry(
                status="Приостановлено",
                status_display="Приостановлено",
                start_date=datetime(2024, 1, 5),
                end_date=datetime(2024, 1, 5),
            ),
            StatusHistoryEntry(
                status="Discovery backlog",
                status_display="Discovery backlog",
                start_date=datetime(2024, 1, 10),
                end_date=datetime(2024, 1, 10),
            ),
            StatusHistoryEntry(
                status="Приостановлено",
                status_display="Приостановлено",
                start_date=datetime(2024, 1, 12),
                end_date=datetime(2024, 1, 12),
            ),
            StatusHistoryEntry(
                status="Готова к разработке",
                status_display="Готова к разработке",
                start_date=datetime(2024, 1, 15),
                end_date=datetime(2024, 1, 15),
            ),
            StatusHistoryEntry(
                status="Приостановлено",
                status_display="Приостановлено",
                start_date=datetime(2024, 1, 20),
                end_date=datetime(2024, 1, 20),
            ),
            StatusHistoryEntry(
                status="Done",
                status_display="Done",
                start_date=datetime(2024, 1, 25),
                end_date=datetime(2024, 1, 25),
            ),
        ]

        # Mock data service to return history
        self.data_service.get_task_history.return_value = history

        # Mock metrics service
        self.metrics_service.calculate_time_to_delivery.return_value = (
            10  # TTD without pause
        )
        self.metrics_service.calculate_pause_time_up_to_date.return_value = (
            8  # Pause time up to ready (5+3 days)
        )

        # Create task data
        task_data = TaskData(
            id=1,
            key="CPO-123",
            group_value="test_author",
            author="test_author",
            team="test_team",
            created_at=datetime(2024, 1, 1),
            summary="Test task",
        )

        # Test pause calculation
        ttd_pause = self.command._calculate_ttd_pause(task_data)

        assert ttd_pause == 8
        self.metrics_service.calculate_pause_time_up_to_date.assert_called_once()

    def test_ttd_pause_no_pause(self):
        """Test TTD pause calculation when no pause exists."""
        # Task history without pause
        history = [
            StatusHistoryEntry(
                status="Создана",
                status_display="Создана",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 1),
            ),
            StatusHistoryEntry(
                status="Discovery backlog",
                status_display="Discovery backlog",
                start_date=datetime(2024, 1, 2),
                end_date=datetime(2024, 1, 2),
            ),
            StatusHistoryEntry(
                status="Готова к разработке",
                status_display="Готова к разработке",
                start_date=datetime(2024, 1, 5),
                end_date=datetime(2024, 1, 5),
            ),
        ]

        # Mock data service to return history
        self.data_service.get_task_history.return_value = history

        # Mock metrics service
        self.metrics_service.calculate_time_to_delivery.return_value = 4
        self.metrics_service.calculate_pause_time_up_to_date.return_value = 0

        # Create task data
        task_data = TaskData(
            id=1,
            key="CPO-123",
            group_value="test_author",
            author="test_author",
            team="test_team",
            created_at=datetime(2024, 1, 1),
            summary="Test task",
        )

        # Test pause calculation
        ttd_pause = self.command._calculate_ttd_pause(task_data)

        assert ttd_pause == 0

    def test_ttd_pause_no_ready_status(self):
        """Test TTD pause calculation when task never reaches ready status."""
        # Task history without ready status
        history = [
            StatusHistoryEntry(
                status="Создана",
                status_display="Создана",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 1),
            ),
            StatusHistoryEntry(
                status="Discovery backlog",
                status_display="Discovery backlog",
                start_date=datetime(2024, 1, 2),
                end_date=datetime(2024, 1, 2),
            ),
            StatusHistoryEntry(
                status="Приостановлено",
                status_display="Приостановлено",
                start_date=datetime(2024, 1, 5),
                end_date=datetime(2024, 1, 5),
            ),
        ]

        # Mock data service to return history
        self.data_service.get_task_history.return_value = history

        # Mock metrics service
        self.metrics_service.calculate_time_to_delivery.return_value = None
        self.metrics_service.calculate_pause_time_up_to_date.return_value = 0

        # Create task data
        task_data = TaskData(
            id=1,
            key="CPO-123",
            group_value="test_author",
            author="test_author",
            team="test_team",
            created_at=datetime(2024, 1, 1),
            summary="Test task",
        )

        # Test pause calculation
        ttd_pause = self.command._calculate_ttd_pause(task_data)

        assert ttd_pause == 0

    def test_pause_calculation_with_empty_history(self):
        """Test pause calculation with empty history."""
        # Empty history
        history = []

        # Mock data service to return history
        self.data_service.get_task_history.return_value = history

        # Mock metrics service
        self.metrics_service.calculate_time_to_delivery.return_value = None
        self.metrics_service.calculate_time_to_market.return_value = None
        self.metrics_service.calculate_pause_time_up_to_date.return_value = 0

        # Create task data
        task_data = TaskData(
            id=1,
            key="CPO-123",
            group_value="test_author",
            author="test_author",
            team="test_team",
            created_at=datetime(2024, 1, 1),
            summary="Test task",
        )

        # Test pause calculation
        ttd_pause = self.command._calculate_ttd_pause(task_data)

        assert ttd_pause == 0

    def test_pause_calculation_with_exception(self):
        """Test pause calculation when metrics service raises exception."""
        # Task history
        history = [
            StatusHistoryEntry(
                status="Создана",
                status_display="Создана",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 1),
            ),
            StatusHistoryEntry(
                status="Готова к разработке",
                status_display="Готова к разработке",
                start_date=datetime(2024, 1, 5),
                end_date=datetime(2024, 1, 5),
            ),
        ]

        # Mock data service to return history
        self.data_service.get_task_history.return_value = history

        # Mock metrics service to raise exception
        self.metrics_service.calculate_time_to_delivery.return_value = 4
        self.metrics_service.calculate_pause_time_up_to_date.side_effect = Exception(
            "Test error"
        )

        # Create task data
        task_data = TaskData(
            id=1,
            key="CPO-123",
            group_value="test_author",
            author="test_author",
            team="test_team",
            created_at=datetime(2024, 1, 1),
            summary="Test task",
        )

        # Test pause calculation should handle exception gracefully
        ttd_pause = self.command._calculate_ttd_pause(task_data)

        assert ttd_pause == 0  # Should return 0 on error
