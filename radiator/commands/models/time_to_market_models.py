"""Data models for Time To Market report."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ReportType(Enum):
    """Report type enumeration."""

    TTD = "ttd"
    TTM = "ttm"
    BOTH = "both"


class GroupBy(Enum):
    """Grouping type enumeration."""

    AUTHOR = "author"
    TEAM = "team"


@dataclass
class Quarter:
    """Quarter/period data model."""

    name: str
    start_date: datetime
    end_date: datetime


@dataclass
class StatusMapping:
    """Status mapping configuration."""

    discovery_statuses: List[str]
    done_statuses: List[str]

    @property
    def all_target_statuses(self) -> List[str]:
        """Get all target statuses."""
        return self.discovery_statuses + self.done_statuses


@dataclass
class TaskData:
    """Task data for analysis."""

    id: int
    key: str
    group_value: str
    author: Optional[str]
    team: Optional[str]
    created_at: datetime
    summary: Optional[str] = None


@dataclass
class StatusHistoryEntry:
    """Status history entry."""

    status: str
    status_display: str
    start_date: datetime
    end_date: Optional[datetime]


@dataclass
class TimeMetrics:
    """Time metrics for a group."""

    times: List[int]
    mean: Optional[float]
    p85: Optional[float]
    count: int
    pause_times: Optional[List[int]] = None
    pause_mean: Optional[float] = None
    pause_p85: Optional[float] = None
    # New fields for status duration metrics
    discovery_backlog_times: Optional[List[int]] = None
    discovery_backlog_mean: Optional[float] = None
    discovery_backlog_p85: Optional[float] = None
    ready_for_dev_times: Optional[List[int]] = None
    ready_for_dev_mean: Optional[float] = None
    ready_for_dev_p85: Optional[float] = None
    # New fields for testing returns metrics
    testing_returns: Optional[List[int]] = None
    testing_returns_mean: Optional[float] = None
    testing_returns_p85: Optional[float] = None
    external_test_returns: Optional[List[int]] = None
    external_test_returns_mean: Optional[float] = None
    external_test_returns_p85: Optional[float] = None

    @property
    def has_data(self) -> bool:
        """Check if metrics have data."""
        return bool(self.times)

    @property
    def has_pause_data(self) -> bool:
        """Check if pause metrics have data."""
        return bool(self.pause_times)

    @property
    def has_discovery_backlog_data(self) -> bool:
        """Check if discovery backlog duration metrics have data."""
        return bool(self.discovery_backlog_times)

    @property
    def has_ready_for_dev_data(self) -> bool:
        """Check if ready for development duration metrics have data."""
        return bool(self.ready_for_dev_times)

    @property
    def has_testing_returns_data(self) -> bool:
        """Check if testing returns metrics have data."""
        return bool(self.testing_returns)

    @property
    def has_external_test_returns_data(self) -> bool:
        """Check if external test returns metrics have data."""
        return bool(self.external_test_returns)


@dataclass
class GroupMetrics:
    """Metrics for a specific group (author/team)."""

    group_name: str
    ttd_metrics: TimeMetrics
    ttm_metrics: TimeMetrics
    tail_metrics: TimeMetrics
    total_tasks: int


@dataclass
class QuarterReport:
    """Report data for a single quarter."""

    quarter: Quarter
    groups: Dict[str, GroupMetrics]


@dataclass
class TimeToMarketReport:
    """Complete Time To Market report."""

    quarters: List[Quarter]
    status_mapping: StatusMapping
    group_by: GroupBy
    quarter_reports: Dict[str, QuarterReport]

    @property
    def all_groups(self) -> List[str]:
        """Get all unique groups across all quarters."""
        groups = set()
        for quarter_report in self.quarter_reports.values():
            groups.update(quarter_report.groups.keys())
        return sorted(groups)

    @property
    def total_tasks(self) -> int:
        """Get total number of tasks across all quarters."""
        total = 0
        for quarter_report in self.quarter_reports.values():
            for group_metrics in quarter_report.groups.values():
                total += group_metrics.total_tasks
        return total
