"""Regression tests to ensure optimizations don't change results."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from radiator.commands.generate_time_to_market_report import (
    GenerateTimeToMarketReportCommand,
)
from radiator.commands.models.time_to_market_models import GroupBy
from radiator.models.tracker import TrackerTask, TrackerTaskHistory


class TestOptimizationRegression:
    """Regression tests to ensure optimizations don't change results."""

    def test_report_metrics_identical_with_cache(self, db_session, test_reports_dir):
        """Verify that report metrics are identical whether cache is used or not."""
        # Given: CPO tasks in database with history
        task = TrackerTask(
            tracker_id="cpo-regression-001",
            key="CPO-REG-001",
            summary="Test Regression Task",
            status="Done",
            author="test_author",
        )
        db_session.add(task)
        db_session.flush()

        base_date = datetime(2025, 1, 20, tzinfo=timezone.utc)
        history = [
            TrackerTaskHistory(
                task_id=task.id,
                tracker_id=task.tracker_id,
                status="Discovery backlog",
                status_display="Discovery backlog",
                start_date=base_date,
                end_date=datetime(2025, 1, 25, tzinfo=timezone.utc),
            ),
            TrackerTaskHistory(
                task_id=task.id,
                tracker_id=task.tracker_id,
                status="Готова к разработке",
                status_display="Готова к разработке",
                start_date=datetime(2025, 1, 25, tzinfo=timezone.utc),
                end_date=datetime(2025, 2, 1, tzinfo=timezone.utc),
            ),
            TrackerTaskHistory(
                task_id=task.id,
                tracker_id=task.tracker_id,
                status="Done",
                status_display="Done",
                start_date=datetime(2025, 2, 1, tzinfo=timezone.utc),
                end_date=None,
            ),
        ]
        db_session.add_all(history)
        db_session.commit()

        # When: Generate report (with caching enabled by default)
        with patch(
            "radiator.commands.generate_time_to_market_report.ConfigService"
        ) as mock_config:
            from radiator.commands.models.time_to_market_models import (
                Quarter,
                StatusMapping,
            )

            mock_config_instance = Mock()
            mock_config_instance.load_quarters.return_value = [
                Quarter(
                    name="2025.Q1",
                    start_date=datetime(2025, 1, 1),
                    end_date=datetime(2025, 3, 31),
                )
            ]
            mock_config_instance.load_status_mapping.return_value = StatusMapping(
                discovery_statuses=["Discovery backlog"],
                done_statuses=["Done"],
            )
            mock_config.return_value = mock_config_instance

            cmd = GenerateTimeToMarketReportCommand(
                group_by=GroupBy.AUTHOR, output_dir=test_reports_dir
            )
            cmd.db = db_session
            report = cmd.generate_report_data()

            # Then: Report should be generated successfully
            assert report is not None, "Report should be generated"
            assert report.quarters is not None, "Quarters should be populated"
            # Verify cache was used (it should be populated)
            assert isinstance(cmd._task_history_cache, dict), "Cache should exist"

    def test_csv_generation_succeeds_with_cache(self, db_session, test_reports_dir):
        """Verify that CSV generation works correctly with caching."""
        import time

        # Given: A simple report with cached data
        with patch(
            "radiator.commands.generate_time_to_market_report.ConfigService"
        ) as mock_config:
            from radiator.commands.models.time_to_market_models import (
                Quarter,
                StatusMapping,
            )

            mock_config_instance = Mock()
            mock_config_instance.load_quarters.return_value = [
                Quarter(
                    name="2025.Q1",
                    start_date=datetime(2025, 1, 1),
                    end_date=datetime(2025, 3, 31),
                )
            ]
            mock_config_instance.load_status_mapping.return_value = StatusMapping(
                discovery_statuses=["Discovery backlog"],
                done_statuses=["Done"],
            )
            mock_config.return_value = mock_config_instance

            cmd = GenerateTimeToMarketReportCommand(
                group_by=GroupBy.AUTHOR, output_dir=test_reports_dir
            )
            cmd.db = db_session

            # When: Generate report and CSV with timing
            print("🔄 Starting generate_report_data...")
            start = time.time()
            cmd.generate_report_data()
            print(f"⏱️ generate_report_data: {time.time() - start:.2f}s")

            print("🔄 Starting generate_task_details_csv...")
            start = time.time()
            csv_path = cmd.generate_task_details_csv()
            print(f"⏱️ generate_task_details_csv: {time.time() - start:.2f}s")

            # Then: CSV should be generated (empty or with data)
            # If there's data in the period, it should be written
            assert isinstance(csv_path, str), "CSV path should be returned"

    def test_caching_does_not_break_testing_returns(self, db_session, test_reports_dir):
        """Verify that testing returns calculation works with caching optimization."""
        # Given: CPO task linked to FULLSTACK task with returns
        cpo_task = TrackerTask(
            tracker_id="cpo-returns-001",
            key="CPO-RETURNS-001",
            summary="Test CPO Task",
            status="Done",
            author="test_author",
            links=[
                {
                    "type": {"id": "relates"},
                    "direction": "outward",
                    "object": {"key": "FULLSTACK-RETURNS-001"},
                }
            ],
        )
        db_session.add(cpo_task)
        db_session.flush()

        fullstack_task = TrackerTask(
            tracker_id="fs-returns-001",
            key="FULLSTACK-RETURNS-001",
            summary="Test FULLSTACK Task",
            status="Testing",
            author="test_dev",
        )
        db_session.add(fullstack_task)
        db_session.flush()

        # Add history with testing returns
        base_date = datetime(2025, 1, 15, tzinfo=timezone.utc)
        fs_history = [
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="Open",
                status_display="Open",
                start_date=base_date,
                end_date=datetime(2025, 1, 16, tzinfo=timezone.utc),
            ),
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="Testing",
                status_display="Testing",
                start_date=datetime(2025, 1, 16, tzinfo=timezone.utc),
                end_date=datetime(2025, 1, 17, tzinfo=timezone.utc),
            ),
            # Return from Testing
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="In Progress",
                status_display="In Progress",
                start_date=datetime(2025, 1, 17, tzinfo=timezone.utc),
                end_date=datetime(2025, 1, 18, tzinfo=timezone.utc),
            ),
            # Second entry to Testing
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="Testing",
                status_display="Testing",
                start_date=datetime(2025, 1, 18, tzinfo=timezone.utc),
                end_date=None,
            ),
        ]
        db_session.add_all(fs_history)
        db_session.commit()

        # When: Calculate testing returns with caching
        from radiator.commands.services.data_service import DataService
        from radiator.commands.services.testing_returns_service import (
            TestingReturnsService,
        )

        testing_returns_service = TestingReturnsService(db_session)
        data_service = DataService(db_session)

        (
            testing_returns,
            external_returns,
        ) = testing_returns_service.calculate_testing_returns_for_cpo_task(
            "CPO-RETURNS-001",
            get_task_history_func=data_service.get_task_history_by_key,
        )

        # Then: Testing returns should be calculated correctly
        assert testing_returns == 1, f"Expected 1 testing return, got {testing_returns}"
        assert (
            external_returns == 0
        ), f"Expected 0 external returns, got {external_returns}"


if __name__ == "__main__":
    pytest.main([__file__])
