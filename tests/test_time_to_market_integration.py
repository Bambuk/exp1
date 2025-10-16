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

    def test_full_workflow_author_grouping(self, db_session, test_reports_dir):
        """Test complete workflow with author grouping."""
        cmd = GenerateTimeToMarketReportCommand(
            group_by=GroupBy.AUTHOR, output_dir=test_reports_dir
        )
        # Use test database instead of real database
        cmd.db = db_session

        # Mock all services to avoid real database operations
        cmd.data_service = Mock()
        cmd.data_service.get_tasks_for_period.return_value = []
        cmd.data_service.get_task_history.return_value = []

        cmd.testing_returns_service = Mock()
        cmd.testing_returns_service.calculate_testing_returns_for_cpo_task.return_value = (
            0,
            0,
        )

        try:
            # This should not raise an exception
            report = cmd.generate_report_data()
            assert report is not None
            assert report.group_by == GroupBy.AUTHOR
        finally:
            cmd.db.close()

    def test_full_workflow_team_grouping(self, db_session, test_reports_dir):
        """Test complete workflow with team grouping."""
        cmd = GenerateTimeToMarketReportCommand(
            group_by=GroupBy.TEAM, output_dir=test_reports_dir
        )
        # Use test database instead of real database
        cmd.db = db_session

        # Mock all services to avoid real database operations
        cmd.data_service = Mock()
        cmd.data_service.get_tasks_for_period.return_value = []
        cmd.data_service.get_task_history.return_value = []

        cmd.testing_returns_service = Mock()
        cmd.testing_returns_service.calculate_testing_returns_for_cpo_task.return_value = (
            0,
            0,
        )

        try:
            # This should not raise an exception
            report = cmd.generate_report_data()
            assert report is not None
            assert report.group_by == GroupBy.TEAM
        finally:
            cmd.db.close()

    def test_generate_csv_integration(self, db_session, test_reports_dir):
        """Test CSV generation integration."""
        cmd = GenerateTimeToMarketReportCommand(
            group_by=GroupBy.AUTHOR, output_dir=test_reports_dir
        )
        # Use test database instead of real database
        cmd.db = db_session

        # Mock all services to avoid real database operations
        cmd.data_service = Mock()
        cmd.data_service.get_tasks_for_period.return_value = []
        cmd.data_service.get_task_history.return_value = []

        cmd.testing_returns_service = Mock()
        cmd.testing_returns_service.calculate_testing_returns_for_cpo_task.return_value = (
            0,
            0,
        )

        try:
            # Generate report data first
            cmd.generate_report_data()

            # Generate CSV - should not raise exception
            csv_file = cmd.generate_csv(report_type=ReportType.BOTH)
            assert csv_file != ""
        finally:
            cmd.db.close()

    def test_generate_table_integration(self, db_session, test_reports_dir):
        """Test table generation integration."""
        cmd = GenerateTimeToMarketReportCommand(
            group_by=GroupBy.AUTHOR, output_dir=test_reports_dir
        )
        # Use test database instead of real database
        cmd.db = db_session

        # Mock all services to avoid real database operations
        cmd.data_service = Mock()
        cmd.data_service.get_tasks_for_period.return_value = []
        cmd.data_service.get_task_history.return_value = []

        cmd.testing_returns_service = Mock()
        cmd.testing_returns_service.calculate_testing_returns_for_cpo_task.return_value = (
            0,
            0,
        )

        try:
            # Generate report data first
            cmd.generate_report_data()

            # Generate table - should not raise exception
            table_file = cmd.generate_table(report_type=ReportType.TTD)
            # Table file might be empty if no data, but should not crash
            assert isinstance(table_file, str)
        finally:
            cmd.db.close()

    def test_print_summary_integration(self, db_session, test_reports_dir):
        """Test console summary integration."""
        cmd = GenerateTimeToMarketReportCommand(
            group_by=GroupBy.AUTHOR, output_dir=test_reports_dir
        )
        # Use test database instead of real database
        cmd.db = db_session

        # Mock all services to avoid real database operations
        cmd.data_service = Mock()
        cmd.data_service.get_tasks_for_period.return_value = []
        cmd.data_service.get_task_history.return_value = []

        cmd.testing_returns_service = Mock()
        cmd.testing_returns_service.calculate_testing_returns_for_cpo_task.return_value = (
            0,
            0,
        )

        try:
            # Generate report data first
            cmd.generate_report_data()

            # Print summary - should not raise exception
            cmd.print_summary(report_type=ReportType.BOTH)
        finally:
            cmd.db.close()

    def test_different_report_types(self, db_session, test_reports_dir):
        """Test different report types."""
        cmd = GenerateTimeToMarketReportCommand(
            group_by=GroupBy.AUTHOR, output_dir=test_reports_dir
        )
        # Use test database instead of real database
        cmd.db = db_session

        # Mock all services to avoid real database operations
        cmd.data_service = Mock()
        cmd.data_service.get_tasks_for_period.return_value = []
        cmd.data_service.get_task_history.return_value = []

        cmd.testing_returns_service = Mock()
        cmd.testing_returns_service.calculate_testing_returns_for_cpo_task.return_value = (
            0,
            0,
        )

        try:
            cmd.generate_report_data()

            # Test TTD only
            cmd.print_summary(report_type=ReportType.TTD)

            # Test TTM only
            cmd.print_summary(report_type=ReportType.TTM)

            # Test both
            cmd.print_summary(report_type=ReportType.BOTH)
        finally:
            cmd.db.close()

    def test_context_manager_cleanup(self, db_session, test_reports_dir):
        """Test that context manager properly cleans up resources."""
        cmd = GenerateTimeToMarketReportCommand(
            group_by=GroupBy.AUTHOR, output_dir=test_reports_dir
        )
        # Use test database instead of real database
        cmd.db = db_session

        # Mock all services to avoid real database operations
        cmd.data_service = Mock()
        cmd.data_service.get_tasks_for_period.return_value = []
        cmd.data_service.get_task_history.return_value = []

        cmd.testing_returns_service = Mock()
        cmd.testing_returns_service.calculate_testing_returns_for_cpo_task.return_value = (
            0,
            0,
        )

        try:
            assert cmd.db is not None
            cmd.generate_report_data()
        finally:
            cmd.db.close()

    def test_error_handling_integration(self, db_session, test_reports_dir):
        """Test error handling in integration scenarios."""
        cmd = GenerateTimeToMarketReportCommand(
            group_by=GroupBy.AUTHOR, output_dir=test_reports_dir
        )
        # Use test database instead of real database
        cmd.db = db_session

        # Mock all services to avoid real database operations
        cmd.data_service = Mock()
        cmd.data_service.get_tasks_for_period.return_value = []
        cmd.data_service.get_task_history.return_value = []

        cmd.testing_returns_service = Mock()
        cmd.testing_returns_service.calculate_testing_returns_for_cpo_task.return_value = (
            0,
            0,
        )

        try:
            # Test with invalid configuration directory
            cmd.config_dir = "/nonexistent/path"

            # Should handle gracefully
            report = cmd.generate_report_data()
            assert report is not None  # Should return empty report, not crash
        finally:
            cmd.db.close()


if __name__ == "__main__":
    pytest.main([__file__])
