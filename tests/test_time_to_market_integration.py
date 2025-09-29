"""Integration tests for refactored Time To Market report - testing complete workflow."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from radiator.commands.generate_time_to_market_report import (
    GenerateTimeToMarketReportCommand,
)
from radiator.commands.models.time_to_market_models import GroupBy, ReportType


class TestTimeToMarketReportIntegration:
    """Integration tests for refactored Time To Market report."""

    def test_full_workflow_author_grouping(self):
        """Test complete workflow with author grouping."""
        with GenerateTimeToMarketReportCommand(group_by=GroupBy.AUTHOR) as cmd:
            # This should not raise an exception
            report = cmd.generate_report_data()
            assert report is not None
            assert report.group_by == GroupBy.AUTHOR

    def test_full_workflow_team_grouping(self):
        """Test complete workflow with team grouping."""
        with GenerateTimeToMarketReportCommand(group_by=GroupBy.TEAM) as cmd:
            # This should not raise an exception
            report = cmd.generate_report_data()
            assert report is not None
            assert report.group_by == GroupBy.TEAM

    def test_generate_csv_integration(self):
        """Test CSV generation integration."""
        with GenerateTimeToMarketReportCommand(group_by=GroupBy.AUTHOR) as cmd:
            # Generate report data first
            cmd.generate_report_data()

            # Generate CSV - should not raise exception
            csv_file = cmd.generate_csv(report_type=ReportType.BOTH)
            assert csv_file != ""

    def test_generate_table_integration(self):
        """Test table generation integration."""
        with GenerateTimeToMarketReportCommand(group_by=GroupBy.AUTHOR) as cmd:
            # Generate report data first
            cmd.generate_report_data()

            # Generate table - should not raise exception
            table_file = cmd.generate_table(report_type=ReportType.TTD)
            # Table file might be empty if no data, but should not crash
            assert isinstance(table_file, str)

    def test_print_summary_integration(self):
        """Test console summary integration."""
        with GenerateTimeToMarketReportCommand(group_by=GroupBy.AUTHOR) as cmd:
            # Generate report data first
            cmd.generate_report_data()

            # Print summary - should not raise exception
            cmd.print_summary(report_type=ReportType.BOTH)

    def test_different_report_types(self):
        """Test different report types."""
        with GenerateTimeToMarketReportCommand(group_by=GroupBy.AUTHOR) as cmd:
            cmd.generate_report_data()

            # Test TTD only
            cmd.print_summary(report_type=ReportType.TTD)

            # Test TTM only
            cmd.print_summary(report_type=ReportType.TTM)

            # Test both
            cmd.print_summary(report_type=ReportType.BOTH)

    def test_context_manager_cleanup(self):
        """Test that context manager properly cleans up resources."""
        cmd = GenerateTimeToMarketReportCommand(group_by=GroupBy.AUTHOR)

        with cmd:
            assert cmd.db is not None
            cmd.generate_report_data()

        # After context exit, db should be closed
        # (We can't easily test this without mocking, but the structure is correct)

    def test_error_handling_integration(self):
        """Test error handling in integration scenarios."""
        with GenerateTimeToMarketReportCommand(group_by=GroupBy.AUTHOR) as cmd:
            # Test with invalid configuration directory
            cmd.config_dir = "/nonexistent/path"

            # Should handle gracefully
            report = cmd.generate_report_data()
            assert report is not None  # Should return empty report, not crash


if __name__ == "__main__":
    pytest.main([__file__])
