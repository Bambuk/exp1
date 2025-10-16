"""Integration tests for testing returns functionality."""

from unittest.mock import MagicMock, Mock

import pytest

from radiator.commands.models.time_to_market_models import GroupMetrics, TimeMetrics
from radiator.commands.services.metrics_service import MetricsService
from radiator.commands.services.testing_returns_metrics import (
    calculate_enhanced_group_metrics_with_testing_returns,
    calculate_enhanced_statistics_with_testing_returns,
)
from radiator.commands.services.testing_returns_service import TestingReturnsService


class TestTestingReturnsIntegration:
    """Integration tests for testing returns functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.metrics_service = MetricsService()
        self.mock_db = Mock()
        self.testing_returns_service = TestingReturnsService(self.mock_db)

    def test_calculate_enhanced_statistics_with_testing_returns(self):
        """Test: calculate_enhanced_statistics_with_testing_returns works correctly."""
        # Test data
        times = [10, 20, 30]
        pause_times = [1, 2, 3]
        discovery_backlog_times = [2, 4, 6]
        ready_for_dev_times = [3, 6, 9]
        testing_returns = [0, 1, 2]
        external_test_returns = [1, 0, 1]

        # Call the function
        result = calculate_enhanced_statistics_with_testing_returns(
            self.metrics_service,
            times,
            pause_times,
            discovery_backlog_times,
            ready_for_dev_times,
            testing_returns,
            external_test_returns,
        )

        # Verify result
        assert isinstance(result, TimeMetrics)
        assert result.times == times
        assert result.mean == 20.0  # (10+20+30)/3
        assert abs(result.p85 - 27.0) < 0.1  # 85th percentile (numpy interpolation)
        assert result.count == 3

        # Verify testing returns statistics
        assert result.testing_returns == testing_returns
        assert result.testing_returns_mean == 1.0  # (0+1+2)/3
        assert (
            abs(result.testing_returns_p85 - 1.7) < 0.1
        )  # 85th percentile (numpy interpolation)

        # Verify external test returns statistics
        assert result.external_test_returns == external_test_returns
        assert abs(result.external_test_returns_mean - 0.67) < 0.01  # (1+0+1)/3 ≈ 0.67
        assert result.external_test_returns_p85 == 1.0  # 85th percentile

    def test_calculate_enhanced_statistics_with_empty_testing_returns(self):
        """Test: calculate_enhanced_statistics_with_testing_returns handles empty data."""
        # Test data with empty testing returns
        times = [10, 20, 30]
        pause_times = [1, 2, 3]
        discovery_backlog_times = [2, 4, 6]
        ready_for_dev_times = [3, 6, 9]
        testing_returns = []
        external_test_returns = []

        # Call the function
        result = calculate_enhanced_statistics_with_testing_returns(
            self.metrics_service,
            times,
            pause_times,
            discovery_backlog_times,
            ready_for_dev_times,
            testing_returns,
            external_test_returns,
        )

        # Verify result
        assert isinstance(result, TimeMetrics)
        assert result.times == times
        assert result.mean == 20.0
        assert result.count == 3

        # Verify testing returns statistics are None for empty data
        assert result.testing_returns == []
        assert result.testing_returns_mean is None
        assert result.testing_returns_p85 is None

        # Verify external test returns statistics are None for empty data
        assert result.external_test_returns == []
        assert result.external_test_returns_mean is None
        assert result.external_test_returns_p85 is None

    def test_calculate_enhanced_group_metrics_with_testing_returns(self):
        """Test: calculate_enhanced_group_metrics_with_testing_returns works correctly."""
        # Test data
        group_name = "Test Team"
        ttd_times = [5, 10, 15]
        ttd_pause_times = [1, 2, 3]
        ttd_discovery_backlog_times = [1, 2, 3]
        ttd_ready_for_dev_times = [2, 4, 6]
        ttm_times = [20, 30, 40]
        ttm_pause_times = [2, 3, 4]
        ttm_discovery_backlog_times = [3, 6, 9]
        ttm_ready_for_dev_times = [4, 8, 12]
        tail_times = [5, 10, 15]
        testing_returns = [0, 1, 2]
        external_test_returns = [1, 0, 1]

        # Call the function
        result = calculate_enhanced_group_metrics_with_testing_returns(
            self.metrics_service,
            group_name,
            ttd_times,
            ttd_pause_times,
            ttd_discovery_backlog_times,
            ttd_ready_for_dev_times,
            ttm_times,
            ttm_pause_times,
            ttm_discovery_backlog_times,
            ttm_ready_for_dev_times,
            tail_times,
            testing_returns,
            external_test_returns,
        )

        # Verify result
        assert isinstance(result, GroupMetrics)
        assert result.group_name == group_name
        assert result.total_tasks == 6  # 3 TTD + 3 TTM

        # Verify TTD metrics
        assert result.ttd_metrics.count == 3
        assert result.ttd_metrics.mean == 10.0  # (5+10+15)/3

        # Verify TTM metrics with testing returns
        assert result.ttm_metrics.count == 3
        assert result.ttm_metrics.mean == 30.0  # (20+30+40)/3
        assert result.ttm_metrics.testing_returns == testing_returns
        assert result.ttm_metrics.testing_returns_mean == 1.0
        assert result.ttm_metrics.external_test_returns == external_test_returns
        assert abs(result.ttm_metrics.external_test_returns_mean - 0.67) < 0.01

        # Verify Tail metrics
        assert result.tail_metrics.count == 3
        assert result.tail_metrics.mean == 10.0  # (5+10+15)/3

    def test_calculate_enhanced_group_metrics_with_empty_data(self):
        """Test: calculate_enhanced_group_metrics_with_testing_returns handles empty data."""
        # Test data with empty lists
        group_name = "Empty Team"
        ttd_times = []
        ttd_pause_times = []
        ttd_discovery_backlog_times = []
        ttd_ready_for_dev_times = []
        ttm_times = []
        ttm_pause_times = []
        ttm_discovery_backlog_times = []
        ttm_ready_for_dev_times = []
        tail_times = []
        testing_returns = []
        external_test_returns = []

        # Call the function
        result = calculate_enhanced_group_metrics_with_testing_returns(
            self.metrics_service,
            group_name,
            ttd_times,
            ttd_pause_times,
            ttd_discovery_backlog_times,
            ttd_ready_for_dev_times,
            ttm_times,
            ttm_pause_times,
            ttm_discovery_backlog_times,
            ttm_ready_for_dev_times,
            tail_times,
            testing_returns,
            external_test_returns,
        )

        # Verify result
        assert isinstance(result, GroupMetrics)
        assert result.group_name == group_name
        assert result.total_tasks == 0  # 0 TTD + 0 TTM

        # Verify all metrics are empty
        assert result.ttd_metrics.count == 0
        assert result.ttd_metrics.mean is None
        assert result.ttm_metrics.count == 0
        assert result.ttm_metrics.mean is None
        assert result.ttm_metrics.testing_returns_mean is None
        assert result.ttm_metrics.external_test_returns_mean is None
        assert result.tail_metrics.count == 0
        assert result.tail_metrics.mean is None

    def test_metrics_service_methods_exist(self):
        """Test: verify that MetricsService has the required methods."""
        # This test would have caught the original error
        assert hasattr(
            self.metrics_service, "calculate_enhanced_statistics_with_status_durations"
        )
        assert hasattr(self.metrics_service, "calculate_statistics")

        # These methods should NOT exist (they were the source of the error)
        assert not hasattr(self.metrics_service, "calculate_mean")
        assert not hasattr(self.metrics_service, "calculate_percentile")

    def test_numpy_functions_work_correctly(self):
        """Test: verify that numpy functions work as expected."""
        import numpy as np

        # Test data
        testing_returns = [0, 1, 2, 3, 4]
        external_test_returns = [1, 0, 1, 2, 0]

        # Test numpy functions directly
        testing_mean = float(np.mean(testing_returns))
        testing_p85 = float(np.percentile(testing_returns, 85))
        external_mean = float(np.mean(external_test_returns))
        external_p85 = float(np.percentile(external_test_returns, 85))

        # Verify results
        assert testing_mean == 2.0  # (0+1+2+3+4)/5
        assert abs(testing_p85 - 3.4) < 0.1  # 85th percentile (numpy interpolation)
        assert external_mean == 0.8  # (1+0+1+2+0)/5
        assert abs(external_p85 - 1.4) < 0.1  # 85th percentile (numpy interpolation)
