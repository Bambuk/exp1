"""Integration test for pause time functionality in Time To Market report."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from radiator.commands.generate_time_to_market_report import GenerateTimeToMarketReportCommand
from radiator.commands.models.time_to_market_models import (
    GroupBy, Quarter, StatusMapping, StatusHistoryEntry, TaskData
)


class TestPauseTimeIntegration:
    """Integration tests for pause time functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        
        # Mock quarters
        self.quarters = [
            Quarter("Q1 2024", datetime(2024, 1, 1), datetime(2024, 3, 31))
        ]
        
        # Mock status mapping
        self.status_mapping = StatusMapping(
            discovery_statuses=["Discovery"],
            done_statuses=["Done"]
        )
        
        # Mock tasks with pause time
        self.mock_tasks = [
            TaskData(
                id=1,
                key="CPO-1",
                group_value="Author1",
                author="Author1",
                team=None,
                created_at=datetime(2024, 1, 1)
            ),
            TaskData(
                id=2,
                key="CPO-2", 
                group_value="Author2",
                author="Author2",
                team=None,
                created_at=datetime(2024, 1, 1)
            )
        ]
        
        # Mock task histories with pause time and MP/External Test for Tail metric
        self.mock_histories = {
            1: [
                StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
                StatusHistoryEntry("In Progress", "In Progress", datetime(2024, 1, 3), None),
                StatusHistoryEntry("Приостановлено", "Приостановлено", datetime(2024, 1, 5), None),
                StatusHistoryEntry("In Progress", "In Progress", datetime(2024, 1, 8), None),
                StatusHistoryEntry("Готова к разработке", "Готова к разработке", datetime(2024, 1, 10), None),
                StatusHistoryEntry("МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 11), None),
                StatusHistoryEntry("Done", "Done", datetime(2024, 1, 12), None),
            ],
            2: [
                StatusHistoryEntry("New", "New", datetime(2024, 1, 1), None),
                StatusHistoryEntry("In Progress", "In Progress", datetime(2024, 1, 2), None),
                StatusHistoryEntry("МП / Внешний тест", "МП / Внешний тест", datetime(2024, 1, 4), None),
                StatusHistoryEntry("Done", "Done", datetime(2024, 1, 5), None),
            ]
        }
    
    def test_full_report_generation_with_pause_time(self):
        """Test full report generation including pause time calculation."""
        # Create command with mocked config
        with GenerateTimeToMarketReportCommand(group_by=GroupBy.AUTHOR) as cmd:
            # Mock the database session
            cmd.db = self.mock_db
            
            # Mock the config service
            cmd.config_service = Mock()
            cmd.config_service.load_quarters.return_value = self.quarters
            cmd.config_service.load_status_mapping.return_value = self.status_mapping
            
            # Mock the data service
            cmd.data_service = Mock()
            cmd.data_service.get_tasks_for_period.return_value = self.mock_tasks
            cmd.data_service.get_task_history.side_effect = lambda task_id: self.mock_histories.get(task_id, [])
            
            # Generate report
            report = cmd.generate_report_data()
            
            # Verify report structure
            assert report is not None
            assert len(report.quarters) == 1
            assert "Q1 2024" in report.quarter_reports
            
            quarter_report = report.quarter_reports["Q1 2024"]
            assert "Author1" in quarter_report.groups
            assert "Author2" in quarter_report.groups
            
            # Check Author1 metrics (has pause time)
            author1_metrics = quarter_report.groups["Author1"]
            assert author1_metrics.ttd_metrics.count == 1
            assert author1_metrics.ttm_metrics.count == 1
            assert author1_metrics.tail_metrics.count == 1
            
            # TTD should exclude pause time: 10-3=7 days total, minus 3 days pause = 4 days
            assert author1_metrics.ttd_metrics.times[0] == 4
            # TTM should exclude pause time: 12-3=9 days total, minus 3 days pause = 6 days  
            assert author1_metrics.ttm_metrics.times[0] == 6
            # Tail should be: 12-11=1 day (no pause time in this period)
            assert author1_metrics.tail_metrics.times[0] == 1
            
            # Check pause time metrics
            assert author1_metrics.ttd_metrics.pause_times[0] == 3
            assert author1_metrics.ttm_metrics.pause_times[0] == 3
            assert author1_metrics.tail_metrics.pause_times[0] == 0
            assert author1_metrics.ttd_metrics.pause_mean == 3.0
            assert author1_metrics.ttd_metrics.pause_p85 == 3.0
            assert author1_metrics.ttm_metrics.pause_mean == 3.0
            assert author1_metrics.ttm_metrics.pause_p85 == 3.0
            assert author1_metrics.tail_metrics.pause_mean == 0.0
            assert author1_metrics.tail_metrics.pause_p85 == 0.0
            
            # Check Author2 metrics (no pause time)
            author2_metrics = quarter_report.groups["Author2"]
            assert author2_metrics.ttd_metrics.count == 0  # No TTD for Author2
            assert author2_metrics.ttm_metrics.count == 1
            assert author2_metrics.tail_metrics.count == 1
            
            # TTM should be normal: 5-2=3 days, no pause time
            assert author2_metrics.ttm_metrics.times[0] == 3
            # Tail should be: 5-4=1 day, no pause time
            assert author2_metrics.tail_metrics.times[0] == 1
            assert author2_metrics.ttm_metrics.pause_times[0] == 0
            assert author2_metrics.tail_metrics.pause_times[0] == 0
            assert author2_metrics.ttm_metrics.pause_mean == 0.0
            assert author2_metrics.ttm_metrics.pause_p85 == 0.0
            assert author2_metrics.tail_metrics.pause_mean == 0.0
            assert author2_metrics.tail_metrics.pause_p85 == 0.0
    
    def test_csv_rendering_with_pause_time(self):
        """Test CSV rendering includes pause time columns."""
        # Create command and generate report
        with GenerateTimeToMarketReportCommand(group_by=GroupBy.AUTHOR) as cmd:
            cmd.db = self.mock_db
            
            # Mock the config service
            cmd.config_service = Mock()
            cmd.config_service.load_quarters.return_value = self.quarters
            cmd.config_service.load_status_mapping.return_value = self.status_mapping
            
            # Mock the data service
            cmd.data_service = Mock()
            cmd.data_service.get_tasks_for_period.return_value = self.mock_tasks
            cmd.data_service.get_task_history.side_effect = lambda task_id: self.mock_histories.get(task_id, [])
            
            cmd.generate_report_data()
            
            # Generate CSV
            csv_file = cmd.generate_csv()
            
            # Read and verify CSV content
            with open(csv_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check that pause time columns are present
            assert 'Q1 2024_ttd_pause_mean' in content
            assert 'Q1 2024_ttd_pause_p85' in content
            assert 'Q1 2024_ttm_pause_mean' in content
            assert 'Q1 2024_ttm_pause_p85' in content
            assert 'Q1 2024_tail_pause_mean' in content
            assert 'Q1 2024_tail_pause_p85' in content
            
            # Check that data is present
            assert 'Author1' in content
            assert 'Author2' in content
    
    def test_console_rendering_with_pause_time(self, capsys):
        """Test console rendering includes pause time information."""
        # Create command and generate report
        with GenerateTimeToMarketReportCommand(group_by=GroupBy.AUTHOR) as cmd:
            cmd.db = self.mock_db
            
            # Mock the config service
            cmd.config_service = Mock()
            cmd.config_service.load_quarters.return_value = self.quarters
            cmd.config_service.load_status_mapping.return_value = self.status_mapping
            
            # Mock the data service
            cmd.data_service = Mock()
            cmd.data_service.get_tasks_for_period.return_value = self.mock_tasks
            cmd.data_service.get_task_history.side_effect = lambda task_id: self.mock_histories.get(task_id, [])
            
            cmd.generate_report_data()
            
            # Print summary
            cmd.print_summary()
            
            # Capture output
            captured = capsys.readouterr()
            output = captured.out
            
            # Check that pause time information is displayed
            assert 'Excluding Pause Time' in output
            assert 'Pause Avg' in output
            assert 'Pause 85%' in output
            assert 'Tail (days from MP/External Test to Done)' in output
            assert 'Author1' in output
            assert 'Author2' in output


if __name__ == "__main__":
    pytest.main([__file__])
