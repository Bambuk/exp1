"""Base renderer for Time To Market report."""

from abc import ABC, abstractmethod
from typing import Optional

from radiator.commands.models.time_to_market_models import (
    ReportType,
    TimeToMarketReport,
)


class BaseRenderer(ABC):
    """Base class for report renderers."""

    def __init__(self, report: TimeToMarketReport, output_dir: str = None):
        """
        Initialize renderer.

        Args:
            report: TimeToMarketReport object
            output_dir: Output directory for reports (optional, uses settings if not provided)
        """
        self.report = report

        # Set output directory
        if output_dir is not None:
            self.output_dir = output_dir
        else:
            # Use settings to determine output directory
            from radiator.core.config import settings

            self.output_dir = settings.REPORTS_DIR

    @abstractmethod
    def render(
        self, filepath: Optional[str] = None, report_type: ReportType = ReportType.BOTH
    ) -> str:
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
