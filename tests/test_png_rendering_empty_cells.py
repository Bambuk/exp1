"""Tests for PNG rendering with empty cells in TTM report."""

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


class TestPNGRenderingEmptyCells:
    """Tests for PNG table rendering with empty cells."""

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

        # Create mock quarter report with empty TTM metrics
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
                    # TTM metrics with None values (empty data)
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
                    # TTM metrics with some None values
                    ttm_metrics=TimeMetrics(
                        times=[4, 6],
                        mean=5.0,
                        p85=6.0,
                        count=2,
                        pause_times=[0, 0],
                        pause_mean=0.0,
                        pause_p85=0.0,
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

    def test_ttm_table_handles_empty_metrics(self):
        """Test that TTM table handles empty metrics without crashing."""
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

        # Call the method directly - this should not crash
        self.renderer._render_ttm_table(mock_ax, ["Q1 2024"], ["Author1", "Author2"])

        # Verify table was created
        mock_ax.table.assert_called_once()

        # Get the call arguments
        call_args = mock_ax.table.call_args
        cell_text = call_args[1]["cellText"]
        col_labels = call_args[1]["colLabels"]

        # Verify we have data for both authors
        assert len(cell_text) == 2  # Two authors

        # Verify we have correct number of columns (1 Group + 7 metric columns per quarter)
        assert len(col_labels) == 8  # 1 Group + 7 metric columns

        # Verify column headers include testing returns
        testing_headers = [
            col for col in col_labels if "Testing" in col or "External" in col
        ]
        assert len(testing_headers) == 2  # 2 testing returns columns (only 85%)

        # Verify data structure for Author1 (empty TTM data)
        author1_row = cell_text[0]
        assert len(author1_row) == 8  # Group + 7 metric columns

        # Verify TTM data is empty for Author1 (first 7 metric columns)
        ttm_data = author1_row[1:8]  # Skip group name
        assert ttm_data[0] == "0.0"  # TTM Avg (should be 0.0, not empty)
        assert ttm_data[1] == "0.0"  # TTM 85%
        assert ttm_data[2] == "0"  # TTM Tasks
        assert ttm_data[3] == "0.0"  # TTM Pause Avg
        assert ttm_data[4] == "0.0"  # TTM Pause 85%
        assert ttm_data[5] == "0.0"  # Testing Returns 85%
        assert ttm_data[6] == "0.0"  # External Returns 85%

        # Verify data structure for Author2 (has TTM data, no testing returns)
        author2_row = cell_text[1]
        assert len(author2_row) == 8  # Group + 7 metric columns

        # Verify TTM data is present for Author2
        ttm_data_author2 = author2_row[1:8]  # Skip group name
        assert ttm_data_author2[0] == "5.0"  # TTM Avg
        assert ttm_data_author2[1] == "6.0"  # TTM 85%
        assert ttm_data_author2[2] == "2"  # TTM Tasks
        assert ttm_data_author2[3] == "0.0"  # TTM Pause Avg
        assert ttm_data_author2[4] == "0.0"  # TTM Pause 85%
        assert ttm_data_author2[5] == "0.0"  # Testing Returns 85%
        assert ttm_data_author2[6] == "0.0"  # External Returns 85%

    def test_ttm_table_handles_missing_group_metrics(self):
        """Test that TTM table handles missing group metrics gracefully."""
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

        # Test with a group that doesn't exist in quarter report
        self.renderer._render_ttm_table(
            mock_ax, ["Q1 2024"], ["Author1", "Author2", "NonExistentAuthor"]
        )

        # Verify table was created
        mock_ax.table.assert_called_once()

        # Get the call arguments
        call_args = mock_ax.table.call_args
        cell_text = call_args[1]["cellText"]

        # Verify we have data for all three authors
        assert len(cell_text) == 3  # Three authors

        # Verify data structure for NonExistentAuthor (should have empty values)
        nonexistent_row = cell_text[2]
        assert len(nonexistent_row) == 8  # Group + 7 metric columns

        # Verify all metric columns are empty strings
        metric_data = nonexistent_row[1:8]  # Skip group name
        for value in metric_data:
            assert value == ""  # Should be empty string, not crash

    def test_ttm_table_handles_missing_quarter_report(self):
        """Test that TTM table handles missing quarter report gracefully."""
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

        # Test with a quarter that doesn't exist in quarter_reports
        self.renderer._render_ttm_table(
            mock_ax, ["Q1 2024", "Q2 2024"], ["Author1", "Author2"]
        )

        # Verify table was created
        mock_ax.table.assert_called_once()

        # Get the call arguments
        call_args = mock_ax.table.call_args
        cell_text = call_args[1]["cellText"]

        # Verify we have data for both authors
        assert len(cell_text) == 2  # Two authors

        # Verify we have correct number of columns (1 Group + 18 metric columns for 2 quarters)
        col_labels = call_args[1]["colLabels"]
        assert len(col_labels) == 15  # 1 Group + 14 metric columns (7 per quarter)

        # Verify data structure for Author1 (Q1 has data, Q2 should be empty)
        author1_row = cell_text[0]
        assert len(author1_row) == 15  # Group + 14 metric columns

        # Q1 data (first 7 metric columns) - should have data
        q1_data = author1_row[1:8]  # Skip group name
        assert q1_data[0] == "0.0"  # TTM Avg
        assert q1_data[1] == "0.0"  # TTM 85%
        assert q1_data[2] == "0"  # TTM Tasks

        # Q2 data (next 7 metric columns) - should be empty
        q2_data = author1_row[8:15]
        for value in q2_data:
            assert value == ""  # Should be empty string

    def test_ttm_table_handles_none_values_in_testing_returns(self):
        """Test that TTM table handles None values in testing returns gracefully."""
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
        self.renderer._render_ttm_table(mock_ax, ["Q1 2024"], ["Author1", "Author2"])

        # Verify table was created
        mock_ax.table.assert_called_once()

        # Get the call arguments
        call_args = mock_ax.table.call_args
        cell_text = call_args[1]["cellText"]

        # Verify no cell contains None or causes formatting errors
        for row in cell_text:
            for cell in row:
                assert cell is not None
                assert isinstance(cell, str)
                # Should not contain "None" string
                assert "None" not in cell

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.close")
    @patch("matplotlib.pyplot.figure")
    def test_full_ttm_rendering_with_empty_cells(
        self, mock_figure, mock_close, mock_savefig
    ):
        """Test full TTM rendering with empty cells doesn't crash."""
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

        # Render TTM report - should not crash
        result = self.renderer.render(report_type=ReportType.TTM)

        # Verify rendering completed
        assert result is not None

        # Verify savefig was called
        mock_savefig.assert_called_once()

    def test_ttm_table_cell_text_formatting(self):
        """Test that TTM table cell text is properly formatted."""
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
        self.renderer._render_ttm_table(mock_ax, ["Q1 2024"], ["Author1", "Author2"])

        # Get the call arguments
        call_args = mock_ax.table.call_args
        cell_text = call_args[1]["cellText"]

        # Verify all numeric values are properly formatted
        for row in cell_text:
            for cell in row:
                if cell and cell != "":
                    # If it's a numeric cell, it should be properly formatted
                    if cell.replace(".", "").replace("-", "").isdigit():
                        # Should be a valid number format
                        assert "." in cell or cell.isdigit()
                    # Should not contain "None" or other invalid values
                    assert "None" not in cell
                    assert "nan" not in cell.lower()
                    assert "inf" not in cell.lower()


if __name__ == "__main__":
    pytest.main([__file__])
