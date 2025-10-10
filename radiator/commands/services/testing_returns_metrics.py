"""Additional metrics methods for testing returns functionality."""

from typing import TYPE_CHECKING, List

import numpy as np

from radiator.commands.models.time_to_market_models import GroupMetrics, TimeMetrics

if TYPE_CHECKING:
    from radiator.commands.services.metrics_service import MetricsService


def calculate_enhanced_statistics_with_testing_returns(
    metrics_service,
    times: List[int],
    pause_times: List[int],
    discovery_backlog_times: List[int],
    ready_for_dev_times: List[int],
    testing_returns: List[int],
    external_test_returns: List[int],
) -> TimeMetrics:
    """Calculate enhanced statistics with testing returns.

    Args:
        metrics_service: Instance of MetricsService
        times: List of time measurements
        pause_times: List of pause times
        discovery_backlog_times: List of discovery backlog duration times
        ready_for_dev_times: List of ready for development duration times
        testing_returns: List of testing returns counts
        external_test_returns: List of external test returns counts

    Returns:
        TimeMetrics object with all metrics including testing returns
    """
    # Calculate base statistics
    base_metrics = metrics_service.calculate_enhanced_statistics_with_status_durations(
        times, pause_times, discovery_backlog_times, ready_for_dev_times
    )

    # Calculate testing returns statistics
    testing_returns_mean = float(np.mean(testing_returns)) if testing_returns else None
    testing_returns_p85 = (
        float(np.percentile(testing_returns, 85)) if testing_returns else None
    )

    external_test_returns_mean = (
        float(np.mean(external_test_returns)) if external_test_returns else None
    )
    external_test_returns_p85 = (
        float(np.percentile(external_test_returns, 85))
        if external_test_returns
        else None
    )

    # Create new metrics with testing returns
    return TimeMetrics(
        times=base_metrics.times,
        mean=base_metrics.mean,
        p85=base_metrics.p85,
        count=base_metrics.count,
        pause_times=base_metrics.pause_times,
        pause_mean=base_metrics.pause_mean,
        pause_p85=base_metrics.pause_p85,
        discovery_backlog_times=base_metrics.discovery_backlog_times,
        discovery_backlog_mean=base_metrics.discovery_backlog_mean,
        discovery_backlog_p85=base_metrics.discovery_backlog_p85,
        ready_for_dev_times=base_metrics.ready_for_dev_times,
        ready_for_dev_mean=base_metrics.ready_for_dev_mean,
        ready_for_dev_p85=base_metrics.ready_for_dev_p85,
        testing_returns=testing_returns,
        testing_returns_mean=testing_returns_mean,
        testing_returns_p85=testing_returns_p85,
        external_test_returns=external_test_returns,
        external_test_returns_mean=external_test_returns_mean,
        external_test_returns_p85=external_test_returns_p85,
    )


def calculate_enhanced_group_metrics_with_testing_returns(
    metrics_service,
    group_name: str,
    ttd_times: List[int],
    ttd_pause_times: List[int],
    ttd_discovery_backlog_times: List[int],
    ttd_ready_for_dev_times: List[int],
    ttm_times: List[int],
    ttm_pause_times: List[int],
    ttm_discovery_backlog_times: List[int],
    ttm_ready_for_dev_times: List[int],
    tail_times: List[int],
    testing_returns: List[int],
    external_test_returns: List[int],
) -> GroupMetrics:
    """Calculate enhanced group metrics with testing returns.

    Args:
        metrics_service: Instance of MetricsService
        group_name: Name of the group
        ttd_times: List of TTD times
        ttd_pause_times: List of TTD pause times
        ttd_discovery_backlog_times: List of TTD discovery backlog duration times
        ttd_ready_for_dev_times: List of TTD ready for development duration times
        ttm_times: List of TTM times
        ttm_pause_times: List of TTM pause times
        ttm_discovery_backlog_times: List of TTM discovery backlog duration times
        ttm_ready_for_dev_times: List of TTM ready for development duration times
        tail_times: List of Tail times
        testing_returns: List of testing returns counts
        external_test_returns: List of external test returns counts

    Returns:
        GroupMetrics object with all metrics data including testing returns
    """
    ttd_metrics = metrics_service.calculate_enhanced_statistics_with_status_durations(
        ttd_times,
        ttd_pause_times,
        ttd_discovery_backlog_times,
        ttd_ready_for_dev_times,
    )
    ttm_metrics = calculate_enhanced_statistics_with_testing_returns(
        metrics_service,
        ttm_times,
        ttm_pause_times,
        ttm_discovery_backlog_times,
        ttm_ready_for_dev_times,
        testing_returns,
        external_test_returns,
    )
    tail_metrics = metrics_service.calculate_statistics(tail_times)

    return GroupMetrics(
        group_name=group_name,
        ttd_metrics=ttd_metrics,
        ttm_metrics=ttm_metrics,
        tail_metrics=tail_metrics,
        total_tasks=ttd_metrics.count + ttm_metrics.count,
    )
