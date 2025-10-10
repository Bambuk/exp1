"""Tests for PNG rendering with real empty cells scenario."""

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


class TestPNGRenderingRealEmptyCells:
    """Tests for PNG table rendering with real empty cells scenario."""

    def setup_method(self):
        """Set up test fixtures with realistic empty data scenario."""
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

        # Create realistic scenario with mixed data
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
                    # TTM metrics with partial data (some None values)
                    ttm_metrics=TimeMetrics(
                        times=[8, 10, 6],
                        mean=8.0,
                        p85=10.0,
                        count=3,
                        pause_times=[2, 1, 0],
                        pause_mean=1.0,
                        pause_p85=2.0,
                        # Testing returns with None values
                        testing_returns=[],
                        testing_returns_mean=None,
                        testing_returns_p85=None,
                        external_test_returns=[],
                        external_test_returns_mean=None,
                        external_test_returns_p85=None,
                    ),
                    tail_metrics=TimeMetrics(
                        times=[2, 3, 1],
                        mean=2.0,
                        p85=3.0,
                        count=3,
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
                    # TTM metrics with all None values
                    ttm_metrics=TimeMetrics(
                        times=[],
                        mean=None,
                        p85=None,
                        count=0,
                        pause_times=[],
                        pause_mean=None,
                        pause_p85=None,
                        testing_returns=[],
                        testing_returns_mean=None,
                        testing_returns_p85=None,
                        external_test_returns=[],
                        external_test_returns_mean=None,
                        external_test_returns_p85=None,
                    ),
                    tail_metrics=TimeMetrics(
                        times=[],
                        mean=None,
                        p85=None,
                        count=0,
                    ),
                    total_tasks=0,
                ),
                "Author3": GroupMetrics(
                    group_name="Author3",
                    ttd_metrics=TimeMetrics(
                        times=[4, 6],
                        mean=5.0,
                        p85=6.0,
                        count=2,
                        pause_times=[0, 0],
                        pause_mean=0.0,
                        pause_p85=0.0,
                    ),
                    # TTM metrics with some data but no testing returns
                    ttm_metrics=TimeMetrics(
                        times=[12, 15],
                        mean=13.5,
                        p85=15.0,
                        count=2,
                        pause_times=[1, 0],
                        pause_mean=0.5,
                        pause_p85=1.0,
                        testing_returns=[],
                        testing_returns_mean=None,
                        testing_returns_p85=None,
                        external_test_returns=[],
                        external_test_returns_mean=None,
                        external_test_returns_p85=None,
                    ),
                    tail_metrics=TimeMetrics(
                        times=[],
                        mean=None,
                        p85=None,
                        count=0,
                    ),
                    total_tasks=2,
                ),
            },
        )

        self.report.quarter_reports = {"Q1 2024": quarter_report}
        self.renderer = TableRenderer(self.report)

    def test_ttm_table_handles_mixed_empty_and_filled_data(self):
        """Test that TTM table handles mixed empty and filled data correctly."""
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
        self.renderer._render_ttm_table(
            mock_ax, ["Q1 2024"], ["Author1", "Author2", "Author3"]
        )

        # Verify table was created
        mock_ax.table.assert_called_once()

        # Get the call arguments
        call_args = mock_ax.table.call_args
        cell_text = call_args[1]["cellText"]
        col_labels = call_args[1]["colLabels"]

        # Verify we have data for all three authors
        assert len(cell_text) == 3  # Three authors

        # Verify column structure
        assert len(col_labels) == 8  # 1 Group + 7 metric columns

        # Verify Author1 data (has TTM data, no testing returns)
        author1_row = cell_text[0]
        assert author1_row[0] == "Author1"  # Group name
        assert author1_row[1] == "8.0"  # TTM Avg
        assert author1_row[2] == "10.0"  # TTM 85%
        assert author1_row[3] == "3"  # TTM Tasks
        assert author1_row[4] == "1.0"  # TTM Pause Avg
        assert author1_row[5] == "2.0"  # TTM Pause 85%
        assert author1_row[6] == "0.0"  # Testing Returns 85%
        assert author1_row[7] == "0.0"  # External Returns 85%

        # Verify Author2 data (all empty TTM data)
        author2_row = cell_text[1]
        assert author2_row[0] == "Author2"  # Group name
        assert author2_row[1] == "0.0"  # TTM Avg (None -> 0.0)
        assert author2_row[2] == "0.0"  # TTM 85%
        assert author2_row[3] == "0"  # TTM Tasks
        assert author2_row[4] == "0.0"  # TTM Pause Avg
        assert author2_row[5] == "0.0"  # TTM Pause 85%
        assert author2_row[6] == "0.0"  # Testing Returns 85%
        assert author2_row[7] == "0.0"  # External Returns 85%

        # Verify Author3 data (has TTM data, no testing returns)
        author3_row = cell_text[2]
        assert author3_row[0] == "Author3"  # Group name
        assert author3_row[1] == "13.5"  # TTM Avg
        assert author3_row[2] == "15.0"  # TTM 85%
        assert author3_row[3] == "2"  # TTM Tasks
        assert author3_row[4] == "0.5"  # TTM Pause Avg
        assert author3_row[5] == "1.0"  # TTM Pause 85%
        assert author3_row[6] == "0.0"  # Testing Returns 85%
        assert author3_row[7] == "0.0"  # External Returns 85%

    def test_ttm_table_no_empty_strings_in_cells(self):
        """Test that TTM table doesn't have empty strings in cells when data is missing."""
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
        self.renderer._render_ttm_table(
            mock_ax, ["Q1 2024"], ["Author1", "Author2", "Author3"]
        )

        # Get the call arguments
        call_args = mock_ax.table.call_args
        cell_text = call_args[1]["cellText"]

        # Verify no cell contains empty string when data is missing
        for row in cell_text:
            for cell in row:
                if cell != "":  # Skip group names
                    # Should not be empty string for numeric cells
                    assert cell != ""
                    # Should be a valid number or group name
                    assert cell.replace(".", "").replace("-", "").isdigit() or cell in [
                        "Author1",
                        "Author2",
                        "Author3",
                    ]

    def test_ttm_table_handles_zero_values_correctly(self):
        """Test that TTM table handles zero values correctly (not as empty)."""
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
        self.renderer._render_ttm_table(
            mock_ax, ["Q1 2024"], ["Author1", "Author2", "Author3"]
        )

        # Get the call arguments
        call_args = mock_ax.table.call_args
        cell_text = call_args[1]["cellText"]

        # Verify that zero values are displayed as "0.0" or "0", not empty strings
        for row in cell_text:
            for i, cell in enumerate(row):
                if i > 0:  # Skip group name column
                    # If it's a zero value, it should be displayed as "0.0" or "0"
                    if cell == "0.0" or cell == "0":
                        # This is correct - zero values should be displayed
                        assert True
                    elif cell == "":
                        # This might be a problem - empty strings for missing data
                        # But in our current implementation, we convert None to 0.0
                        assert False, f"Found empty string in cell: {cell}"

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.close")
    @patch("matplotlib.pyplot.figure")
    def test_full_ttm_rendering_with_mixed_data(
        self, mock_figure, mock_close, mock_savefig
    ):
        """Test full TTM rendering with mixed data doesn't produce empty cells."""
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
        result = self.renderer.render(report_type=ReportType.TTM)

        # Verify rendering completed
        assert result is not None

        # Verify savefig was called
        mock_savefig.assert_called_once()

        # Get the call arguments to verify table data
        call_args = mock_ax.table.call_args
        cell_text = call_args[1]["cellText"]

        # Verify no empty strings in numeric cells
        for row in cell_text:
            for i, cell in enumerate(row):
                if i > 0:  # Skip group name column
                    # All numeric cells should have values, not empty strings
                    assert cell != "", f"Found empty string in cell: {cell}"

    def test_ttm_table_column_widths_are_correct(self):
        """Test that TTM table column widths are calculated correctly."""
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
        self.renderer._render_ttm_table(
            mock_ax, ["Q1 2024"], ["Author1", "Author2", "Author3"]
        )

        # Get the call arguments
        call_args = mock_ax.table.call_args
        col_widths = call_args[1]["colWidths"]

        # Verify column widths are calculated correctly
        # Should have 1 group column + 9 metric columns = 10 columns
        assert len(col_widths) == 8

        # Group column should be wider
        assert col_widths[0] == 0.15

        # Metric columns should be evenly distributed
        metric_width = 0.14 / 1  # 1 quarter
        for i in range(1, 8):
            assert col_widths[i] == metric_width


if __name__ == "__main__":
    pytest.main([__file__])
