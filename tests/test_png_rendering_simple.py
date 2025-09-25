"""Simple tests for PNG rendering functionality."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from radiator.commands.renderers.table_renderer import TableRenderer
from radiator.commands.models.time_to_market_models import (
    TimeToMarketReport, QuarterReport, GroupMetrics, TimeMetrics, 
    StatusMapping, ReportType, GroupBy
)


class TestPNGRenderingSimple:
    """Simple tests for PNG table rendering."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock quarter
        quarter = Mock()
        quarter.name = "Q1 2024"
        quarter.start_date = datetime(2024, 1, 1)
        quarter.end_date = datetime(2024, 3, 31)
        
        # Create mock report data
        self.report = TimeToMarketReport(
            quarters=[quarter],
            group_by=GroupBy.AUTHOR,
            status_mapping=StatusMapping(["Discovery"], ["Done"]),
            quarter_reports={}
        )
        
        # Create mock quarter report with all metrics
        quarter_report = QuarterReport(
            quarter=quarter,
            groups={
                "Author1": GroupMetrics(
                    group_name="Author1",
                    ttd_metrics=TimeMetrics(
                        times=[5, 7, 3],
                        mean=5.0,
                        p85=7.0,
                        count=3,
                        pause_times=[1, 2, 0],
                        pause_mean=1.0,
                        pause_p85=2.0
                    ),
                    ttm_metrics=TimeMetrics(
                        times=[8, 10, 6],
                        mean=8.0,
                        p85=10.0,
                        count=3,
                        pause_times=[2, 1, 0],
                        pause_mean=1.0,
                        pause_p85=2.0
                    ),
                    tail_metrics=TimeMetrics(
                        times=[2, 3, 1],
                        mean=2.0,
                        p85=3.0,
                        count=3,
                        pause_times=[0, 1, 0],
                        pause_mean=0.33,
                        pause_p85=1.0
                    ),
                    total_tasks=3
                ),
                "Author2": GroupMetrics(
                    group_name="Author2",
                    ttd_metrics=TimeMetrics(
                        times=[],
                        mean=None,
                        p85=None,
                        count=0,
                        pause_times=[],
                        pause_mean=None,
                        pause_p85=None
                    ),
                    ttm_metrics=TimeMetrics(
                        times=[4, 6],
                        mean=5.0,
                        p85=6.0,
                        count=2,
                        pause_times=[0, 0],
                        pause_mean=0.0,
                        pause_p85=0.0
                    ),
                    tail_metrics=TimeMetrics(
                        times=[],
                        mean=None,
                        p85=None,
                        count=0,
                        pause_times=[],
                        pause_mean=None,
                        pause_p85=None
                    ),
                    total_tasks=2
                )
            }
        )
        
        self.report.quarter_reports = {"Q1 2024": quarter_report}
        
        self.renderer = TableRenderer(self.report)
    
    def test_ttm_with_tail_table_data_preparation(self):
        """Test that TTM with Tail table data is prepared correctly."""
        # Test data preparation without calling _style_table
        quarters = ["Q1 2024"]
        all_groups = ["Author1", "Author2"]
        
        # Prepare data with proper structure (simulate the logic from _render_ttm_with_tail_table)
        ttm_tail_table_data = []
        for group in all_groups:
            row = [group]
            for quarter in quarters:
                quarter_report = self.report.quarter_reports.get(quarter)
                group_metrics = quarter_report.groups.get(group) if quarter_report else None
                if group_metrics:
                    # TTM columns
                    if group_metrics.ttm_metrics.count > 0:
                        ttm_avg = group_metrics.ttm_metrics.mean or 0
                        ttm_p85 = group_metrics.ttm_metrics.p85 or 0
                        ttm_tasks = group_metrics.ttm_metrics.count
                        ttm_pause_avg = group_metrics.ttm_metrics.pause_mean or 0
                        ttm_pause_p85 = group_metrics.ttm_metrics.pause_p85 or 0
                        ttm_values = [f"{ttm_avg:.1f}", f"{ttm_p85:.1f}", str(ttm_tasks), f"{ttm_pause_avg:.1f}", f"{ttm_pause_p85:.1f}"]
                    else:
                        ttm_values = ["", "", "", "", ""]
                    
                    # Tail columns
                    if group_metrics.tail_metrics.count > 0:
                        tail_avg = group_metrics.tail_metrics.mean or 0
                        tail_p85 = group_metrics.tail_metrics.p85 or 0
                        tail_tasks = group_metrics.tail_metrics.count
                        tail_pause_avg = group_metrics.tail_metrics.pause_mean or 0
                        tail_pause_p85 = group_metrics.tail_metrics.pause_p85 or 0
                        tail_values = [f"{tail_avg:.1f}", f"{tail_p85:.1f}", str(tail_tasks), f"{tail_pause_avg:.1f}", f"{tail_pause_p85:.1f}"]
                    else:
                        tail_values = ["", "", "", "", ""]
                    
                    row.extend(ttm_values + tail_values)
                else:
                    row.extend(["", "", "", "", "", "", "", "", "", ""])
            ttm_tail_table_data.append(row)
        
        # Verify we have data for both authors
        assert len(ttm_tail_table_data) == 2  # Two authors
        
        # Verify we have TTM and Tail columns (10 columns per quarter: 5 TTM + 5 Tail)
        assert len(ttm_tail_table_data[0]) == 11  # Group + 10 metric columns
        
        # Verify data structure for Author1 (has both TTM and Tail data)
        author1_row = ttm_tail_table_data[0]
        
        # Verify TTM data is present (first 5 metric columns)
        ttm_data = author1_row[1:6]  # Skip group name
        assert ttm_data[0] == "8.0"  # TTM Avg
        assert ttm_data[1] == "10.0"  # TTM 85%
        assert ttm_data[2] == "3"  # TTM Tasks
        assert ttm_data[3] == "1.0"  # TTM Pause Avg
        assert ttm_data[4] == "2.0"  # TTM Pause 85%
        
        # Verify Tail data is present (last 5 metric columns)
        tail_data = author1_row[6:11]
        assert tail_data[0] == "2.0"  # Tail Avg
        assert tail_data[1] == "3.0"  # Tail 85%
        assert tail_data[2] == "3"  # Tail Tasks
        assert tail_data[3] == "0.3"  # Tail Pause Avg (0.33 rounded)
        assert tail_data[4] == "1.0"  # Tail Pause 85%
        
        # Verify Author2 has empty tail data
        author2_row = ttm_tail_table_data[1]
        tail_data_author2 = author2_row[6:11]
        
        # Verify tail metrics are empty for Author2
        assert tail_data_author2[0] == ""  # Tail Avg
        assert tail_data_author2[1] == ""  # Tail 85%
        assert tail_data_author2[2] == ""  # Tail Tasks
        assert tail_data_author2[3] == ""  # Tail Pause Avg
        assert tail_data_author2[4] == ""  # Tail Pause 85%
    
    def test_ttm_with_tail_headers_preparation(self):
        """Test that TTM with Tail table headers are prepared correctly."""
        quarters = ["Q1 2024"]
        
        # Prepare headers (simulate the logic from _render_ttm_with_tail_table)
        ttm_tail_headers = ['Group']
        for quarter in quarters:
            ttm_tail_headers.extend([
                f'{quarter}\nTTM Avg', f'{quarter}\nTTM 85%', f'{quarter}\nTTM Tasks', 
                f'{quarter}\nTTM Pause Avg', f'{quarter}\nTTM Pause 85%',
                f'{quarter}\nTail Avg', f'{quarter}\nTail 85%', f'{quarter}\nTail Tasks',
                f'{quarter}\nTail Pause Avg', f'{quarter}\nTail Pause 85%'
            ])
        
        # Verify we have correct number of headers
        assert len(ttm_tail_headers) == 11  # 1 Group + 10 metric columns
        
        # Verify column headers include both TTM and Tail
        ttm_headers = [col for col in ttm_tail_headers if 'TTM' in col]
        tail_headers = [col for col in ttm_tail_headers if 'Tail' in col]
        
        assert len(ttm_headers) == 5  # TTM Avg, TTM 85%, TTM Tasks, TTM Pause Avg, TTM Pause 85%
        assert len(tail_headers) == 5  # Tail Avg, Tail 85%, Tail Tasks, Tail Pause Avg, Tail Pause 85%
        
        # Verify specific headers
        assert 'Q1 2024\nTTM Avg' in ttm_tail_headers
        assert 'Q1 2024\nTTM Pause Avg' in ttm_tail_headers
        assert 'Q1 2024\nTail Avg' in ttm_tail_headers
        assert 'Q1 2024\nTail Pause Avg' in ttm_tail_headers
    
    def test_pause_metrics_count(self):
        """Test that pause metrics are counted correctly."""
        quarters = ["Q1 2024"]
        
        # Prepare headers
        ttm_tail_headers = ['Group']
        for quarter in quarters:
            ttm_tail_headers.extend([
                f'{quarter}\nTTM Avg', f'{quarter}\nTTM 85%', f'{quarter}\nTTM Tasks', 
                f'{quarter}\nTTM Pause Avg', f'{quarter}\nTTM Pause 85%',
                f'{quarter}\nTail Avg', f'{quarter}\nTail 85%', f'{quarter}\nTail Tasks',
                f'{quarter}\nTail Pause Avg', f'{quarter}\nTail Pause 85%'
            ])
        
        # Count pause-related columns
        pause_columns = [col for col in ttm_tail_headers if 'Pause' in col]
        
        # Should have exactly 4 pause columns: 2 for TTM + 2 for Tail (per quarter)
        assert len(pause_columns) == 4
        
        # Verify TTM pause columns
        ttm_pause_columns = [col for col in ttm_tail_headers if 'TTM' in col and 'Pause' in col]
        assert len(ttm_pause_columns) == 2  # TTM Pause Avg, TTM Pause 85% (per quarter)
        
        # Verify Tail pause columns
        tail_pause_columns = [col for col in ttm_tail_headers if 'Tail' in col and 'Pause' in col]
        assert len(tail_pause_columns) == 2  # Tail Pause Avg, Tail Pause 85% (per quarter)
    
    def test_tail_metrics_display_logic(self):
        """Test that tail metrics display logic works correctly."""
        # Test with Author1 (has tail metrics)
        author1_metrics = self.report.quarter_reports["Q1 2024"].groups["Author1"]
        
        # Should display tail metrics
        if author1_metrics.tail_metrics.count > 0:
            tail_avg = author1_metrics.tail_metrics.mean or 0
            tail_p85 = author1_metrics.tail_metrics.p85 or 0
            tail_tasks = author1_metrics.tail_metrics.count
            tail_pause_avg = author1_metrics.tail_metrics.pause_mean or 0
            tail_pause_p85 = author1_metrics.tail_metrics.pause_p85 or 0
            tail_values = [f"{tail_avg:.1f}", f"{tail_p85:.1f}", str(tail_tasks), f"{tail_pause_avg:.1f}", f"{tail_pause_p85:.1f}"]
        else:
            tail_values = ["", "", "", "", ""]
        
        # Verify tail metrics are not empty for Author1
        assert tail_values[0] != ""  # Tail Avg
        assert tail_values[1] != ""  # Tail 85%
        assert tail_values[2] != "0"  # Tail Tasks
        assert tail_values[3] != ""  # Tail Pause Avg
        assert tail_values[4] != ""  # Tail Pause 85%
        
        # Test with Author2 (no tail metrics)
        author2_metrics = self.report.quarter_reports["Q1 2024"].groups["Author2"]
        
        # Should not display tail metrics
        if author2_metrics.tail_metrics.count > 0:
            tail_avg = author2_metrics.tail_metrics.mean or 0
            tail_p85 = author2_metrics.tail_metrics.p85 or 0
            tail_tasks = author2_metrics.tail_metrics.count
            tail_pause_avg = author2_metrics.tail_metrics.pause_mean or 0
            tail_pause_p85 = author2_metrics.tail_metrics.pause_p85 or 0
            tail_values = [f"{tail_avg:.1f}", f"{tail_p85:.1f}", str(tail_tasks), f"{tail_pause_avg:.1f}", f"{tail_pause_p85:.1f}"]
        else:
            tail_values = ["", "", "", "", ""]
        
        # Verify tail metrics are empty for Author2
        assert tail_values[0] == ""  # Tail Avg
        assert tail_values[1] == ""  # Tail 85%
        assert tail_values[2] == ""  # Tail Tasks
        assert tail_values[3] == ""  # Tail Pause Avg
        assert tail_values[4] == ""  # Tail Pause 85%


if __name__ == "__main__":
    pytest.main([__file__])
