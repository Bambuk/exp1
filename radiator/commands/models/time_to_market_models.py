"""Data models for Time To Market report."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


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
    
    @property
    def has_data(self) -> bool:
        """Check if metrics have data."""
        return bool(self.times)
    
    @property
    def has_pause_data(self) -> bool:
        """Check if pause metrics have data."""
        return bool(self.pause_times)


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
