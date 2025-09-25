"""Debug tests for task details CSV generation."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from pathlib import Path
import csv
import tempfile
import os

from radiator.commands.generate_time_to_market_report import GenerateTimeToMarketReportCommand
from radiator.commands.models.time_to_market_models import (
    TimeToMarketReport, QuarterReport, GroupMetrics, TimeMetrics, 
    StatusMapping, ReportType, GroupBy, TaskData
)


class TestTaskDetailsCSVDebug:
    """Debug tests for task details CSV generation."""
    
    def test_generate_task_details_csv_debug(self):
        """Debug test for CSV generation."""
        # Create mock quarter
        quarter = Mock()
        quarter.name = "Q1 2024"
        quarter.start_date = datetime(2024, 1, 1)
        quarter.end_date = datetime(2024, 3, 31)
        
        # Create mock report data
        report = TimeToMarketReport(
            quarters=[quarter],
            group_by=GroupBy.AUTHOR,
            status_mapping=StatusMapping(["Discovery"], ["Done"]),
            quarter_reports={}
        )
        
        # Create mock quarter report
        quarter_report = QuarterReport(
            quarter=quarter,
            groups={
                "Author1": GroupMetrics(
                    group_name="Author1",
                    ttd_metrics=TimeMetrics(times=[5, 7, 3], mean=5.0, p85=7.0, count=3, pause_times=[1, 2, 0], pause_mean=1.0, pause_p85=2.0),
                    ttm_metrics=TimeMetrics(times=[8, 10, 6], mean=8.0, p85=10.0, count=3, pause_times=[2, 1, 0], pause_mean=1.0, pause_p85=2.0),
                    tail_metrics=TimeMetrics(times=[2, 3, 1], mean=2.0, p85=3.0, count=3, pause_times=[0, 1, 0], pause_mean=0.33, pause_p85=1.0),
                    total_tasks=3
                )
            }
        )
        
        report.quarter_reports = {"Q1 2024": quarter_report}
        
        # Create mock command
        command = GenerateTimeToMarketReportCommand(group_by=GroupBy.AUTHOR)
        command.report = report
        command.group_by = GroupBy.AUTHOR
        command.status_mapping = StatusMapping(["Discovery"], ["Done"])
        
        # Mock data service
        command.data_service = Mock()
        command.data_service.get_tasks_for_period.return_value = [
            TaskData(
                id=1,
                key="CPO-1001",
                group_value="Author1",
                author="Author1",
                team=None,
                created_at=datetime(2024, 1, 15),
                summary="Test Task 1"
            )
        ]
        
        # Mock metrics service
        command.metrics_service = Mock()
        command.metrics_service.calculate_time_to_delivery.return_value = 5
        command.metrics_service.calculate_time_to_market.return_value = 8
        command.metrics_service.calculate_tail_metric.return_value = 2
        
        # Mock task history
        command.data_service.get_task_history.return_value = []
        
        # Debug: Check if report is set
        print(f"Report is set: {command.report is not None}")
        print(f"Report quarters: {len(command.report.quarters) if command.report else 0}")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Generate CSV
            result = command.generate_task_details_csv(temp_path)
            
            print(f"Result: {result}")
            print(f"File exists: {os.path.exists(temp_path)}")
            
            if os.path.exists(temp_path):
                with open(temp_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"File content: {content}")
            
            # For now, just verify the method doesn't crash
            assert result is not None
            
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__])
