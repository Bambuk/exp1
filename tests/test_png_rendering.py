"""Tests for PNG rendering functionality."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from radiator.commands.models.time_to_market_models import (
    GroupBy,
    GroupMetrics,
    QuarterReport,
    ReportType,
    StatusMapping,
    TimeMetrics,
    TimeToMarketReport,
)
from radiator.commands.renderers.table_renderer import TableRenderer


class TestPNGRendering:
    """Tests for PNG table rendering."""

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
            quarter_reports={},
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
                        pause_p85=2.0,
                    ),
                    ttm_metrics=TimeMetrics(
                        times=[8, 10, 6],
                        mean=8.0,
                        p85=10.0,
                        count=3,
                        pause_times=[2, 1, 0],
                        pause_mean=1.0,
                        pause_p85=2.0,
                    ),
                    tail_metrics=TimeMetrics(
                        times=[2, 3, 1],
                        mean=2.0,
                        p85=3.0,
                        count=3,
                        pause_times=[0, 1, 0],
                        pause_mean=0.33,
                        pause_p85=1.0,
                    ),
                    total_tasks=3,
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
                        pause_p85=None,
                    ),
                    ttm_metrics=TimeMetrics(
                        times=[4, 6],
                        mean=5.0,
                        p85=6.0,
                        count=2,
                        pause_times=[0, 0],
                        pause_mean=0.0,
                        pause_p85=0.0,
                    ),
                    tail_metrics=TimeMetrics(
                        times=[],
                        mean=None,
                        p85=None,
                        count=0,
                        pause_times=[],
                        pause_mean=None,
                        pause_p85=None,
                    ),
                    total_tasks=2,
                ),
            },
        )

        self.report.quarter_reports = {"Q1 2024": quarter_report}

        self.renderer = TableRenderer(self.report)

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.close")
    @patch("matplotlib.pyplot.figure")
    def test_ttm_with_tail_table_rendering(self, mock_figure, mock_close, mock_savefig):
        """Test that TTM table includes both TTM and Tail columns."""
        # Mock figure and axes
        mock_ax = Mock()
        mock_fig = Mock()
        mock_fig.add_axes.return_value = mock_ax
        mock_figure.return_value = mock_fig

        # Create a mock table that supports subscripting
        class MockTable:
            def __getitem__(self, key):
                return Mock()

            def auto_set_font_size(self, value):
                pass

            def set_fontsize(self, value):
                pass

            def scale(self, x, y):
                pass

        mock_table = MockTable()
        mock_ax.table.return_value = mock_table

        # Render TTM report
        self.renderer.render(report_type=ReportType.TTM)

        # Verify that _render_ttm_with_tail_table was called
        mock_ax.axis.assert_called_with("off")

        # Verify savefig was called
        mock_savefig.assert_called_once()

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.close")
    @patch("matplotlib.pyplot.figure")
    def test_both_report_rendering(self, mock_figure, mock_close, mock_savefig):
        """Test that BOTH report includes TTD, TTM, and Tail sections."""
        # Mock figure and axes
        mock_ax1 = Mock()
        mock_ax2 = Mock()
        mock_fig = Mock()
        mock_fig.add_axes.side_effect = [mock_ax1, mock_ax2]
        mock_figure.return_value = mock_fig

        # Create a mock table that supports subscripting
        class MockTable:
            def __getitem__(self, key):
                return Mock()

            def auto_set_font_size(self, value):
                pass

            def set_fontsize(self, value):
                pass

            def scale(self, x, y):
                pass

        mock_table = MockTable()
        mock_ax1.table.return_value = mock_table
        mock_ax2.table.return_value = mock_table

        # Render BOTH report
        self.renderer.render(report_type=ReportType.BOTH)

        # Verify that both axes were created
        assert mock_fig.add_axes.call_count == 2

        # Verify that both axes had axis('off') called
        mock_ax1.axis.assert_called_with("off")
        mock_ax2.axis.assert_called_with("off")

        # Verify savefig was called
        mock_savefig.assert_called_once()

    def test_ttm_with_tail_table_data_structure(self):
        """Test that TTM with Tail table has correct data structure."""
        # Mock axes with proper table mock
        mock_ax = Mock()

        # Create a mock table that supports subscripting
        class MockTable:
            def __getitem__(self, key):
                return Mock()

            def auto_set_font_size(self, value):
                pass

            def set_fontsize(self, value):
                pass

            def scale(self, x, y):
                pass

        mock_table = MockTable()
        mock_ax.table.return_value = mock_table

        # Call the method directly
        self.renderer._render_ttm_with_tail_table(
            mock_ax, ["Q1 2024"], ["Author1", "Author2"]
        )

        # Verify table was created
        mock_ax.table.assert_called_once()

        # Get the call arguments
        call_args = mock_ax.table.call_args
        cell_text = call_args[1]["cellText"]
        col_labels = call_args[1]["colLabels"]

        # Verify we have data for both authors
        assert len(cell_text) == 2  # Two authors

        # Verify we have TTM and Tail columns (8 columns per quarter: 5 TTM + 3 Tail)
        assert len(col_labels) == 9  # 1 Group + 8 metric columns

        # Verify column headers include both TTM and Tail
        ttm_headers = [col for col in col_labels if "TTM" in col]
        tail_headers = [col for col in col_labels if "Tail" in col]

        assert (
            len(ttm_headers) == 5
        )  # TTM Avg, TTM 85%, TTM Tasks, TTM Pause Avg, TTM Pause 85%
        assert (
            len(tail_headers) == 3
        )  # Tail Avg, Tail 85%, Tail Tasks (no pause for tail)

        # Verify data structure for Author1 (has both TTM and Tail data)
        author1_row = cell_text[0]
        assert len(author1_row) == 9  # Group + 8 metric columns

        # Verify TTM data is present (first 5 metric columns)
        ttm_data = author1_row[1:6]  # Skip group name
        assert ttm_data[0] == "8.0"  # TTM Avg
        assert ttm_data[1] == "10.0"  # TTM 85%
        assert ttm_data[2] == "3"  # TTM Tasks
        assert ttm_data[3] == "1.0"  # TTM Pause Avg
        assert ttm_data[4] == "2.0"  # TTM Pause 85%

        # Verify Tail data is present (last 3 metric columns)
        tail_data = author1_row[6:9]
        assert tail_data[0] == "2.0"  # Tail Avg
        assert tail_data[1] == "3.0"  # Tail 85%
        assert tail_data[2] == "3"  # Tail Tasks

    def test_tail_metrics_calculation(self):
        """Test that tail metrics are properly calculated and displayed."""
        # Mock axes with proper table mock
        mock_ax = Mock()

        # Create a mock table that supports subscripting
        class MockTable:
            def __getitem__(self, key):
                return Mock()

            def auto_set_font_size(self, value):
                pass

            def set_fontsize(self, value):
                pass

            def scale(self, x, y):
                pass

        mock_table = MockTable()
        mock_ax.table.return_value = mock_table

        # Call the method directly
        self.renderer._render_ttm_with_tail_table(
            mock_ax, ["Q1 2024"], ["Author1", "Author2"]
        )

        # Get the call arguments
        call_args = mock_ax.table.call_args
        cell_text = call_args[1]["cellText"]

        # Author1 should have tail data
        author1_row = cell_text[0]
        tail_data = author1_row[6:11]  # Last 5 columns are Tail data

        # Verify tail metrics are not empty
        assert tail_data[0] != ""  # Tail Avg
        assert tail_data[1] != ""  # Tail 85%
        assert tail_data[2] != "0"  # Tail Tasks (should be > 0)

        # Author2 should have empty tail data (no tail metrics)
        author2_row = cell_text[1]
        tail_data_author2 = author2_row[6:9]

        # Verify tail metrics are empty for Author2
        assert tail_data_author2[0] == ""  # Tail Avg
        assert tail_data_author2[1] == ""  # Tail 85%
        assert tail_data_author2[2] == ""  # Tail Tasks

    def test_pause_metrics_not_duplicated(self):
        """Test that pause metrics are not duplicated between TTM and Tail."""
        # Mock axes with proper table mock
        mock_ax = Mock()

        # Create a mock table that supports subscripting
        class MockTable:
            def __getitem__(self, key):
                return Mock()

            def auto_set_font_size(self, value):
                pass

            def set_fontsize(self, value):
                pass

            def scale(self, x, y):
                pass

        mock_table = MockTable()
        mock_ax.table.return_value = mock_table

        # Call the method directly
        self.renderer._render_ttm_with_tail_table(
            mock_ax, ["Q1 2024"], ["Author1", "Author2"]
        )

        # Get the call arguments
        call_args = mock_ax.table.call_args
        col_labels = call_args[1]["colLabels"]

        # Count pause-related columns
        pause_columns = [col for col in col_labels if "Pause" in col]

        # Should have exactly 2 pause columns: 2 for TTM (no pause for Tail)
        assert len(pause_columns) == 2

        # Verify TTM pause columns
        ttm_pause_columns = [
            col for col in col_labels if "TTM" in col and "Pause" in col
        ]
        assert len(ttm_pause_columns) == 2  # TTM Pause Avg, TTM Pause 85% (per quarter)

        # Verify Tail pause columns (should be 0 since we removed pause from Tail)
        tail_pause_columns = [
            col for col in col_labels if "Tail" in col and "Pause" in col
        ]
        assert len(tail_pause_columns) == 0  # No pause columns for Tail

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.close")
    @patch("matplotlib.pyplot.figure")
    def test_png_file_creation(self, mock_figure, mock_close, mock_savefig):
        """Test that PNG file is created with correct parameters."""
        # Mock figure and axes
        mock_ax = Mock()
        mock_fig = Mock()
        mock_fig.add_axes.return_value = mock_ax
        mock_figure.return_value = mock_fig

        # Create a mock table that supports subscripting
        class MockTable:
            def __getitem__(self, key):
                return Mock()

            def auto_set_font_size(self, value):
                pass

            def set_fontsize(self, value):
                pass

            def scale(self, x, y):
                pass

        mock_table = MockTable()
        mock_ax.table.return_value = mock_table

        # Render report
        result = self.renderer.render(
            filepath="test_report.png", report_type=ReportType.TTM
        )

        # Verify file path is returned
        assert result == "test_report.png"

        # Verify savefig was called with correct parameters
        mock_savefig.assert_called_once()
        call_args = mock_savefig.call_args

        assert call_args[0][0] == "test_report.png"
        assert call_args[1]["dpi"] == 150
        assert call_args[1]["bbox_inches"] == "tight"
        assert call_args[1]["facecolor"] == "white"
        assert call_args[1]["pad_inches"] == 0.1
        assert call_args[1]["edgecolor"] == "none"
        assert call_args[1]["transparent"] == False


if __name__ == "__main__":
    pytest.main([__file__])
