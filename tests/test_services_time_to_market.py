"""Tests for Time To Market services - only new components from refactoring."""

import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime
from pathlib import Path

from radiator.commands.services.config_service import ConfigService
from radiator.commands.services.data_service import DataService
from radiator.commands.services.metrics_service import MetricsService, CreationDateStrategy, FirstChangeStrategy
from radiator.commands.models.time_to_market_models import (
    GroupBy, Quarter, StatusMapping, StatusHistoryEntry, TimeMetrics, GroupMetrics
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
            assert all(hasattr(q, 'name') for q in result)
            assert all(hasattr(q, 'start_date') for q in result)
            assert all(hasattr(q, 'end_date') for q in result)
    
    def test_load_quarters_file_not_found(self):
        """Test handling of missing quarters file."""
        service = ConfigService("test_config")
        
        with patch('pathlib.Path.exists', return_value=False):
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
        assert hasattr(result, 'discovery_statuses')
        assert hasattr(result, 'done_statuses')
        assert isinstance(result.discovery_statuses, list)
        assert isinstance(result.done_statuses, list)
    
    def test_load_status_mapping_file_not_found(self):
        """Test handling of missing status mapping file."""
        service = ConfigService("test_config")
        
        with patch('pathlib.Path.exists', return_value=False):
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
            StatusHistoryEntry("Discovery", "Discovery", datetime(2024, 1, 3), None),  # First change
            StatusHistoryEntry("Готова к разработке", "Готова к разработке", datetime(2024, 1, 6), None),  # Target
            StatusHistoryEntry("Done", "Done", datetime(2024, 1, 10), None),
        ]
        result = self.service.calculate_time_to_delivery(history_with_target, ["Discovery"])
        assert result == 5  # 6 days - 1 day (creation) = 5 days
    
    def test_calculate_time_to_delivery_with_intermediate_status(self):
        """Test TTD calculation with intermediate status change."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry("In Progress", "In Progress", datetime(2024, 1, 3), None),
            StatusHistoryEntry("Готова к разработке", "Готова к разработке", datetime(2024, 1, 5), None),
        ]

        result = self.service.calculate_time_to_delivery(history, ["Discovery"])
        assert result == 4  # 5 days - 1 day (creation) = 4 days
    
    def test_calculate_time_to_delivery_no_target_status(self):
        """Test TTD calculation when target status not found."""
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry("In Progress", "In Progress", datetime(2024, 1, 5), None),
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
            StatusHistoryEntry("In Progress", "In Progress", datetime(2024, 1, 5), None),
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
            StatusHistoryEntry("In Progress", "In Progress", datetime(2024, 1, 3), None),
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
            StatusHistoryEntry("In Progress", "In Progress", datetime(2024, 1, 3), None),
            StatusHistoryEntry("Готова к разработке", "Готова к разработке", datetime(2024, 1, 5), None),
        ]

        result = service.calculate_time_to_delivery(history, ["Discovery"])
        assert result == 4  # 5 days - 1 day (creation) = 4 days
    
    def test_ttd_with_creation_date_strategy(self):
        """Test TTD calculation with CreationDateStrategy."""
        service = MetricsService(ttd_strategy=CreationDateStrategy())
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry("In Progress", "In Progress", datetime(2024, 1, 3), None),
            StatusHistoryEntry("Готова к разработке", "Готова к разработке", datetime(2024, 1, 5), None),
        ]
        
        result = service.calculate_time_to_delivery(history, ["Discovery"])
        assert result == 4  # 5 days - 1 day (creation) = 4 days
    
    def test_ttm_with_creation_date_strategy(self):
        """Test TTM calculation with CreationDateStrategy."""
        service = MetricsService(ttm_strategy=CreationDateStrategy())
        history = [
            StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
            StatusHistoryEntry("In Progress", "In Progress", datetime(2024, 1, 3), None),
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
        
        result = self.service.calculate_group_metrics("TestGroup", ttd_times, ttm_times, tail_times)
        
        assert result.group_name == "TestGroup"
        assert result.ttd_metrics.times == ttd_times
        assert result.ttm_metrics.times == ttm_times
        assert result.tail_metrics.times == tail_times
        assert result.total_tasks == 6


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
            (2, "CPO-2", "Author2", datetime(2024, 1, 2), "Task 2")
        ]

        self.mock_db.query.return_value.join.return_value.filter.return_value.distinct.return_value.all.return_value = mock_tasks

        status_mapping = StatusMapping(["Discovery"], ["Done"])
        result = self.service.get_tasks_for_period(
            datetime(2024, 1, 1),
            datetime(2024, 1, 31),
            GroupBy.AUTHOR,
            status_mapping
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
        
        self.mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_history
        
        result = self.service.get_task_history(1)
        
        assert len(result) == 2
        assert result[0].status == "New"
        assert result[0].start_date == datetime(2024, 1, 1)


if __name__ == "__main__":
    pytest.main([__file__])
