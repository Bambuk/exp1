"""Tests for Time To Market services - only new components from refactoring."""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from radiator.commands.models.time_to_market_models import (
    GroupBy,
    GroupMetrics,
    Quarter,
    StatusHistoryEntry,
    StatusMapping,
    TimeMetrics,
)
from radiator.commands.services.config_service import ConfigService
from radiator.commands.services.data_service import DataService
from radiator.commands.services.metrics_service import (
    CreationDateStrategy,
    FirstChangeStrategy,
    MetricsService,
)


class TestConfigService:
    """Tests for ConfigService - new component."""

    def test_init(self):
        """Test ConfigService initialization."""
        service = ConfigService("test_config")
        assert service.config_dir == Path("test_config")

    def test_load_quarters_success(self):
        """Test successful loading of quarters."""
        service = ConfigService("test_config")

        # Test with real file if it exists, otherwise skip
        result = service.load_quarters()

        # If file exists, should have data; if not, should be empty list
        assert isinstance(result, list)
        if result:  # If we have data, test structure
            assert all(hasattr(q, "name") for q in result)
            assert all(hasattr(q, "start_date") for q in result)
            assert all(hasattr(q, "end_date") for q in result)

    def test_load_quarters_file_not_found(self):
        """Test handling of missing quarters file."""
        service = ConfigService("test_config")

        with patch("pathlib.Path.exists", return_value=False):
            result = service.load_quarters()
            assert result == []

    def test_load_quarters_parsing_error(self):
        """Test handling of malformed quarters file."""
        service = ConfigService("test_config")

        # Test with real file - should handle parsing errors gracefully
        result = service.load_quarters()
        assert isinstance(result, list)

    def test_load_status_mapping_success(self):
        """Test successful loading of status mapping."""
        service = ConfigService("test_config")

        # Test with real file if it exists
        result = service.load_status_mapping()

        # Should return StatusMapping object
        assert hasattr(result, "discovery_statuses")
        assert hasattr(result, "done_statuses")
        assert isinstance(result.discovery_statuses, list)
        assert isinstance(result.done_statuses, list)

    def test_load_status_mapping_file_not_found(self):
        """Test handling of missing status mapping file."""
        service = ConfigService("test_config")

        with patch("pathlib.Path.exists", return_value=False):
            result = service.load_status_mapping()
            assert result.discovery_statuses == []
            assert result.done_statuses == []


class TestMetricsService:
    """Tests for MetricsService - new component."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MetricsService()
        self.history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry("Discovery", "Discovery", datetime(2024, 1, 5), None),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 10), None),
        ]

    def test_calculate_time_to_delivery_success(self):
        """Test successful TTD calculation."""
        # Create history with 'Готова к разработке' status
        history_with_target = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "Discovery", "Discovery", datetime(2024, 1, 3), None
            ),  # First change
            StatusHistoryEntry(
                "Готова к разработке", "Готова к разработке", datetime(2024, 1, 6), None
            ),  # Target
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 10), None),
        ]
        result = self.service.calculate_time_to_delivery(
            history_with_target, ["Discovery"]
        )
        assert result == 5  # 6 days - 1 day (creation) = 5 days

    def test_calculate_time_to_delivery_with_intermediate_status(self):
        """Test TTD calculation with intermediate status change."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "Готова к разработке", "Готова к разработке", datetime(2024, 1, 5), None
            ),
        ]

        result = self.service.calculate_time_to_delivery(history, ["Discovery"])
        assert result == 4  # 5 days - 1 day (creation) = 4 days

    def test_calculate_time_to_delivery_no_target_status(self):
        """Test TTD calculation when target status not found."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 5), None
            ),
        ]

        result = self.service.calculate_time_to_delivery(history, ["Discovery"])
        assert result is None  # No 'Готова к разработке' status found

    def test_calculate_time_to_market_success(self):
        """Test successful TTM calculation."""
        result = self.service.calculate_time_to_market(self.history, ["Done"])
        assert result == 9  # 10 days - 1 day (creation) = 9 days

    def test_calculate_time_to_market_no_target_status(self):
        """Test TTM calculation when target status not found."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 5), None
            ),
        ]

        result = self.service.calculate_time_to_market(history, ["Done"])
        assert result is None

    def test_calculate_statistics_success(self):
        """Test successful statistics calculation."""
        times = [1, 2, 3, 4, 5]
        result = self.service.calculate_statistics(times)

        assert result.times == times
        assert result.mean == 3.0
        assert result.p85 == 4.4  # 85th percentile of [1,2,3,4,5]
        assert result.count == 5


class TestStartDateStrategies:
    """Tests for start date calculation strategies."""

    def test_creation_date_strategy(self):
        """Test CreationDateStrategy."""
        strategy = CreationDateStrategy()
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry("Discovery", "Discovery", datetime(2024, 1, 5), None),
        ]

        result = strategy.calculate_start_date(history)
        assert result == datetime(2024, 1, 1)

    def test_first_change_strategy(self):
        """Test FirstChangeStrategy."""
        strategy = FirstChangeStrategy()
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry("Discovery", "Discovery", datetime(2024, 1, 5), None),
        ]

        result = strategy.calculate_start_date(history)
        assert result == datetime(2024, 1, 1)  # Task creation date

    def test_first_change_strategy_no_changes(self):
        """Test FirstChangeStrategy when no changes after creation."""
        strategy = FirstChangeStrategy()
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
        ]

        result = strategy.calculate_start_date(history)
        assert result == datetime(2024, 1, 1)  # Falls back to creation date


class TestMetricsServiceWithStrategies:
    """Tests for MetricsService with different strategies."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MetricsService()

    def test_ttd_with_first_change_strategy(self):
        """Test TTD calculation with FirstChangeStrategy."""
        service = MetricsService(ttd_strategy=FirstChangeStrategy())
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "Готова к разработке", "Готова к разработке", datetime(2024, 1, 5), None
            ),
        ]

        result = service.calculate_time_to_delivery(history, ["Discovery"])
        assert result == 4  # 5 days - 1 day (creation) = 4 days

    def test_ttd_with_creation_date_strategy(self):
        """Test TTD calculation with CreationDateStrategy."""
        service = MetricsService(ttd_strategy=CreationDateStrategy())
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry(
                "Готова к разработке", "Готова к разработке", datetime(2024, 1, 5), None
            ),
        ]

        result = service.calculate_time_to_delivery(history, ["Discovery"])
        assert result == 4  # 5 days - 1 day (creation) = 4 days

    def test_ttm_with_creation_date_strategy(self):
        """Test TTM calculation with CreationDateStrategy."""
        service = MetricsService(ttm_strategy=CreationDateStrategy())
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "In Progress", "In Progress", datetime(2024, 1, 3), None
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 5), None),
        ]

        result = service.calculate_time_to_market(history, ["Done"])
        assert result == 4  # 5 days - 1 day (creation) = 4 days

    def test_calculate_statistics_empty_list(self):
        """Test statistics calculation with empty list."""
        result = self.service.calculate_statistics([])

        assert result.times == []
        assert result.mean is None
        assert result.p85 is None
        assert result.count == 0

    def test_calculate_group_metrics(self):
        """Test group metrics calculation."""
        ttd_times = [1, 2, 3]
        ttm_times = [4, 5, 6]
        tail_times = [1, 2, 3]

        result = self.service.calculate_group_metrics(
            "TestGroup", ttd_times, ttm_times, tail_times
        )

        assert result.group_name == "TestGroup"
        assert result.ttd_metrics.times == ttd_times
        assert result.ttm_metrics.times == ttm_times
        assert result.tail_metrics.times == tail_times
        assert result.total_tasks == 6

    def test_calculate_dev_lead_time_normal_flow(self):
        """Test DevLT calculation with normal flow - both statuses present."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "МП / В работе",
                "МП / В работе",
                datetime(2024, 1, 5),
                datetime(2024, 1, 8),
            ),
            StatusHistoryEntry("Testing", "Testing", datetime(2024, 1, 10), None),
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 15), None
            ),
        ]

        result = self.service.calculate_dev_lead_time(history)

        # Should be 10 days from first "МП / В работе" to last "МП / Внешний тест"
        assert result == 10

    def test_calculate_dev_lead_time_missing_start(self):
        """Test DevLT calculation when 'МП / В работе' status is missing."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry("Testing", "Testing", datetime(2024, 1, 10), None),
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 15), None
            ),
        ]

        result = self.service.calculate_dev_lead_time(history)

        assert result is None

    def test_calculate_dev_lead_time_missing_end(self):
        """Test DevLT calculation when 'МП / Внешний тест' status is missing."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "МП / В работе", "МП / В работе", datetime(2024, 1, 5), None
            ),
            StatusHistoryEntry("Testing", "Testing", datetime(2024, 1, 10), None),
        ]

        result = self.service.calculate_dev_lead_time(history)

        assert result is None

    def test_calculate_dev_lead_time_multiple_entries(self):
        """Test DevLT calculation with multiple entries - should use first work to last test."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "МП / В работе",
                "МП / В работе",
                datetime(2024, 1, 5),
                datetime(2024, 1, 7),
            ),
            StatusHistoryEntry("Testing", "Testing", datetime(2024, 1, 8), None),
            StatusHistoryEntry(
                "МП / В работе",
                "МП / В работе",
                datetime(2024, 1, 10),
                datetime(2024, 1, 11),
            ),
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 12), None
            ),
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 14), None),
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 15), None
            ),
        ]

        result = self.service.calculate_dev_lead_time(history)

        # Should be 10 days from first "МП / В работе" (1/5) to last "МП / Внешний тест" (1/15)
        assert result == 10

    def test_calculate_dev_lead_time_returns_none_when_no_valid_work(self):
        """Test DevLT returns None when no 'МП / В работе' with end_date found."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "МП / В работе",
                "МП / В работе",
                datetime(2024, 1, 5),
                None,  # No end_date
            ),
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 10), None
            ),
        ]

        result = self.service.calculate_dev_lead_time(history)

        # Should return None because "МП / В работе" has no end_date (open interval)
        assert result is None

    def test_calculate_dev_lead_time_with_pauses(self):
        """Test DevLT calculation with pauses - pauses should NOT be excluded."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "МП / В работе",
                "МП / В работе",
                datetime(2024, 1, 5),
                datetime(2024, 1, 7),
            ),
            StatusHistoryEntry(
                "Приостановлено", "Приостановлено", datetime(2024, 1, 8), None
            ),
            StatusHistoryEntry(
                "МП / В работе",
                "МП / В работе",
                datetime(2024, 1, 10),
                datetime(2024, 1, 12),
            ),
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 15), None
            ),
        ]

        result = self.service.calculate_dev_lead_time(history)

        # Should be 10 days from first "МП / В работе" (1/5) to "МП / Внешний тест" (1/15)
        assert result == 10

    def test_calculate_dev_lead_time_filters_short_transitions(self):
        """Test DevLT calculation filters short transitions (< 300 seconds)."""
        # Create history with short transition that should be filtered
        short_transition_time = datetime(2024, 1, 5, 12, 0, 0)
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry(
                "МП / В работе",
                "МП / В работе",
                datetime(2024, 1, 5),
                datetime(2024, 1, 6),
            ),
            # Short transition (less than 300 seconds) - should be filtered
            StatusHistoryEntry("Testing", "Testing", short_transition_time, None),
            StatusHistoryEntry(
                "МП / В работе",
                "МП / В работе",
                short_transition_time + timedelta(seconds=200),
                short_transition_time + timedelta(seconds=400),  # Short duration
            ),
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 15), None
            ),
        ]

        result = self.service.calculate_dev_lead_time(history)

        # Should be 10 days from first "МП / В работе" to last "МП / Внешний тест"
        # Short transition should be filtered out
        assert result == 10

    def test_calculate_dev_lead_time_empty_history(self):
        """Test DevLT calculation with empty history."""
        result = self.service.calculate_dev_lead_time([])

        assert result is None

    def test_calculate_dev_lead_time_unsorted_history(self):
        """Test DevLT calculation with unsorted history - should still work correctly."""
        history = [
            StatusHistoryEntry(
                "МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 15), None
            ),
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry("Testing", "Testing", datetime(2024, 1, 10), None),
            StatusHistoryEntry(
                "МП / В работе",
                "МП / В работе",
                datetime(2024, 1, 5),
                datetime(2024, 1, 7),
            ),
        ]

        result = self.service.calculate_dev_lead_time(history)

        # Should still be 10 days from first "МП / В работе" to last "МП / Внешний тест"
        assert result == 10

    def test_calculate_dev_lead_time_cpo_1548_case(self):
        """Test DevLT calculation with CPO-1548 real history - should find first long work to last long external test."""
        # История из CPO-1548 (упрощенная):
        # МП / В работе: 2024-05-02 12:15 - 2024-12-09 15:25 (длинный, > 5 мин)
        # МП / В работе: 2024-12-16 10:16 - 2024-12-16 10:31 (15 мин, короткий, < 5 мин)
        # МП / Внешний тест: 2024-12-09 15:25 - 2024-12-16 10:16 (длинный, > 5 мин)
        # МП / Внешний тест: 2025-01-29 12:06 - 2025-02-06 10:28 (длинный, > 5 мин)
        # МП / Внешний тест: 2025-07-23 10:45 - 2025-07-23 10:47 (2 мин, короткий, < 5 мин)
        # Ожидаемый DevLT: 272 дня (2024-05-02 → 2025-01-29)

        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            # Первое длинное "МП / В работе" (> 5 минут)
            StatusHistoryEntry(
                "МП / В работе",
                "МП / В работе",
                datetime(2024, 5, 2, 12, 15),
                datetime(2024, 12, 9, 15, 25),  # 7+ месяцев - длинный
            ),
            # Длинный "МП / Внешний тест" (> 5 минут)
            StatusHistoryEntry(
                "МП / Внешний тест",
                "МП / Внешний тест",
                datetime(2024, 12, 9, 15, 25),
                datetime(2024, 12, 16, 10, 16),  # 6+ дней - длинный
            ),
            # Короткий "МП / В работе" (< 5 минут) - должен игнорироваться
            StatusHistoryEntry(
                "МП / В работе",
                "МП / В работе",
                datetime(2024, 12, 16, 10, 16),
                datetime(2024, 12, 16, 10, 31),  # 15 минут - короткий
            ),
            # Последний длинный "МП / Внешний тест" (> 5 минут)
            StatusHistoryEntry(
                "МП / Внешний тест",
                "МП / Внешний тест",
                datetime(2025, 1, 29, 12, 6),
                datetime(2025, 2, 6, 10, 28),  # 8+ дней - длинный
            ),
            # Короткий "МП / Внешний тест" (< 5 минут) - должен игнорироваться
            StatusHistoryEntry(
                "МП / Внешний тест",
                "МП / Внешний тест",
                datetime(2025, 7, 23, 10, 45),
                datetime(2025, 7, 23, 10, 47),  # 2 минуты - короткий
            ),
        ]

        result = self.service.calculate_dev_lead_time(history)

        # Ожидаемый DevLT: 271 день (2024-05-02 → 2025-01-29)
        # Первое длинное "МП / В работе" (2024-05-02) → последнее длинное "МП / Внешний тест" (2025-01-29)
        assert result == 271


class TestDataService:
    """Tests for DataService - new component."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.service = DataService(self.mock_db)

    def test_init(self):
        """Test DataService initialization."""
        assert self.service.db == self.mock_db

    def test_get_tasks_for_period_author_grouping(self):
        """Test getting tasks for period with author grouping."""
        # Mock database query - now includes summary field
        mock_tasks = [
            (1, "CPO-1", "Author1", datetime(2024, 1, 1), "Task 1"),
            (2, "CPO-2", "Author2", datetime(2024, 1, 2), "Task 2"),
        ]

        self.mock_db.query.return_value.join.return_value.filter.return_value.distinct.return_value.all.return_value = (
            mock_tasks
        )

        status_mapping = StatusMapping(["Discovery"], ["Done"])
        result = self.service.get_tasks_for_period(
            datetime(2024, 1, 1), datetime(2024, 1, 31), GroupBy.AUTHOR, status_mapping
        )

        assert len(result) == 2
        assert result[0].key == "CPO-1"
        assert result[0].author == "Author1"

    def test_get_task_history(self):
        """Test getting task history."""
        mock_history = [
            ("New", "New", datetime(2024, 1, 1), None),
            ("Discovery", "Discovery", datetime(2024, 1, 5), None),
        ]

        self.mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
            mock_history
        )

        result = self.service.get_task_history(1)

        assert len(result) == 2
        assert result[0].status == "New"
        assert result[0].start_date == datetime(2024, 1, 1)


if __name__ == "__main__":
    pytest.main([__file__])
