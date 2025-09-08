"""Base renderer for Time To Market report."""

from abc import ABC, abstractmethod
from typing import Optional
from radiator.commands.models.time_to_market_models import TimeToMarketReport, ReportType


class BaseRenderer(ABC):
    """Base class for report renderers."""
    
    def __init__(self, report: TimeToMarketReport):
        """
        Initialize renderer.
        
        Args:
            report: TimeToMarketReport object
        """
        self.report = report
    
    @abstractmethod
    def render(self, filepath: Optional[str] = None, report_type: ReportType = ReportType.BOTH) -> str:
        """
        Render report to file.
        
        Args:
            filepath: Output file path (optional)
            report_type: Type of report to render
            
        Returns:
            Path to generated file
        """
        pass
    
    def _get_quarters(self) -> list:
        """Get sorted list of quarter names."""
        return sorted(self.report.quarter_reports.keys())
    
    def _get_all_groups(self) -> list:
        """Get sorted list of all groups."""
        return self.report.all_groups
