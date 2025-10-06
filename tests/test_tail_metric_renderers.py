"""Tests for Tail metric in renderers."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from radiator.commands.models.time_to_market_models import (
    GroupBy,
    GroupMetrics,
    Quarter,
    QuarterReport,
    ReportType,
    StatusMapping,
    TimeMetrics,
    TimeToMarketReport,
)
from radiator.commands.renderers.console_renderer import ConsoleRenderer
from radiator.commands.renderers.csv_renderer import CSVRenderer
from radiator.commands.renderers.table_renderer import TableRenderer


class TestTailMetricCSVRenderer:
    """Tests for Tail metric in CSV renderer."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock report data
        self.quarter = Quarter("Q1 2024", datetime(2024, 1, 1), datetime(2024, 3, 31))
        self.status_mapping = StatusMapping(["Discovery"], ["Done"])

        # Create mock group metrics with Tail metric
        self.group_metrics = GroupMetrics(
            group_name="TestAuthor",
            ttd_metrics=TimeMetrics([1, 2, 3], 2.0, 2.7, 3),
            ttm_metrics=TimeMetrics([4, 5, 6], 5.0, 5.7, 3),
            tail_metrics=TimeMetrics([1, 2, 3], 2.0, 2.7, 3),
            total_tasks=6,
        )

        self.quarter_report = QuarterReport(
            quarter=self.quarter, groups={"TestAuthor": self.group_metrics}
        )

        self.report = TimeToMarketReport(
            quarters=[self.quarter],
            status_mapping=self.status_mapping,
            group_by=GroupBy.AUTHOR,
            quarter_reports={"Q1 2024": self.quarter_report},
        )

        self.renderer = CSVRenderer(self.report)

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_render_ttm_with_tail_metric(self, mock_file, mock_mkdir):
        """Test CSV rendering with TTM report type including Tail metric."""
        mock_file.return_value.__enter__.return_value.write = Mock()

        result = self.renderer.render(report_type=ReportType.TTM)

        # Verify file was opened for writing
        mock_file.assert_called_once()

        # Get the written content
        written_content = "".join(
            call[0][0]
            for call in mock_file.return_value.__enter__.return_value.write.call_args_list
        )

        # Check that Tail metric columns are included
        assert "tail_mean" in written_content
        assert "tail_p85" in written_content
        assert "tail_tasks" in written_content

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_render_both_with_tail_metric(self, mock_file, mock_mkdir):
        """Test CSV rendering with BOTH report type including Tail metric."""
        mock_file.return_value.__enter__.return_value.write = Mock()

        result = self.renderer.render(report_type=ReportType.BOTH)

        # Verify file was opened for writing
        mock_file.assert_called_once()

        # Get the written content
        written_content = "".join(
            call[0][0]
            for call in mock_file.return_value.__enter__.return_value.write.call_args_list
        )

        # Check that all metric columns are included
        assert "ttd_mean" in written_content
        assert "ttm_mean" in written_content
        assert "tail_mean" in written_content

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_render_ttd_without_tail_metric(self, mock_file, mock_mkdir):
        """Test CSV rendering with TTD report type (should not include Tail metric)."""
        mock_file.return_value.__enter__.return_value.write = Mock()

        result = self.renderer.render(report_type=ReportType.TTD)

        # Verify file was opened for writing
        mock_file.assert_called_once()

        # Get the written content
        written_content = "".join(
            call[0][0]
            for call in mock_file.return_value.__enter__.return_value.write.call_args_list
        )

        # Check that Tail metric columns are NOT included
        assert "tail_mean" not in written_content
        assert "tail_p85" not in written_content
        assert "tail_tasks" not in written_content


class TestTailMetricTableRenderer:
    """Tests for Tail metric in table renderer."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock report data
        self.quarter = Quarter("Q1 2024", datetime(2024, 1, 1), datetime(2024, 3, 31))
        self.status_mapping = StatusMapping(["Discovery"], ["Done"])

        # Create mock group metrics with Tail metric
        self.group_metrics = GroupMetrics(
            group_name="TestAuthor",
            ttd_metrics=TimeMetrics([1, 2, 3], 2.0, 2.7, 3),
            ttm_metrics=TimeMetrics([4, 5, 6], 5.0, 5.7, 3),
            tail_metrics=TimeMetrics([1, 2, 3], 2.0, 2.7, 3),
            total_tasks=6,
        )

        self.quarter_report = QuarterReport(
            quarter=self.quarter, groups={"TestAuthor": self.group_metrics}
        )

        self.report = TimeToMarketReport(
            quarters=[self.quarter],
            status_mapping=self.status_mapping,
            group_by=GroupBy.AUTHOR,
            quarter_reports={"Q1 2024": self.quarter_report},
        )

        self.renderer = TableRenderer(self.report)

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.close")
    @patch("pathlib.Path.mkdir")
    def test_render_ttm_with_tail_table(self, mock_mkdir, mock_close, mock_savefig):
        """Test table rendering with TTM report type including Tail table."""
        with patch("matplotlib.pyplot.figure") as mock_fig:
            mock_ax = Mock()
            mock_table = Mock()
            mock_ax.table.return_value = mock_table
            mock_fig.return_value.add_axes.return_value = mock_ax

            # Mock table cell access
            mock_cell = Mock()
            mock_table.__getitem__ = Mock(return_value=mock_cell)

            result = self.renderer.render(report_type=ReportType.TTM)

            # Verify that add_axes was called (should create axes for TTM and Tail tables)
            assert mock_fig.return_value.add_axes.call_count >= 1

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.close")
    @patch("pathlib.Path.mkdir")
    def test_render_both_with_tail_table(self, mock_mkdir, mock_close, mock_savefig):
        """Test table rendering with BOTH report type including Tail table."""
        with patch("matplotlib.pyplot.figure") as mock_fig:
            mock_ax = Mock()
            mock_table = Mock()
            mock_ax.table.return_value = mock_table
            mock_fig.return_value.add_axes.return_value = mock_ax

            # Mock table cell access
            mock_cell = Mock()
            mock_table.__getitem__ = Mock(return_value=mock_cell)

            result = self.renderer.render(report_type=ReportType.BOTH)

            # Verify that add_axes was called multiple times (TTD and TTM+Tail tables)
            assert mock_fig.return_value.add_axes.call_count >= 2

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.close")
    @patch("pathlib.Path.mkdir")
    def test_render_ttd_without_tail_table(self, mock_mkdir, mock_close, mock_savefig):
        """Test table rendering with TTD report type (should not include Tail table)."""
        with patch("matplotlib.pyplot.figure") as mock_fig:
            mock_ax = Mock()
            mock_table = Mock()
            mock_ax.table.return_value = mock_table
            mock_fig.return_value.add_axes.return_value = mock_ax

            # Mock table cell access
            mock_cell = Mock()
            mock_table.__getitem__ = Mock(return_value=mock_cell)

            result = self.renderer.render(report_type=ReportType.TTD)

            # Verify that add_axes was called only once (TTD table only)
            assert mock_fig.return_value.add_axes.call_count == 1


class TestTailMetricConsoleRenderer:
    """Tests for Tail metric in console renderer."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock report data
        self.quarter = Quarter("Q1 2024", datetime(2024, 1, 1), datetime(2024, 3, 31))
        self.status_mapping = StatusMapping(["Discovery"], ["Done"])

        # Create mock group metrics with Tail metric
        self.group_metrics = GroupMetrics(
            group_name="TestAuthor",
            ttd_metrics=TimeMetrics([1, 2, 3], 2.0, 2.7, 3),
            ttm_metrics=TimeMetrics([4, 5, 6], 5.0, 5.7, 3),
            tail_metrics=TimeMetrics([1, 2, 3], 2.0, 2.7, 3),
            total_tasks=6,
        )

        self.quarter_report = QuarterReport(
            quarter=self.quarter, groups={"TestAuthor": self.group_metrics}
        )

        self.report = TimeToMarketReport(
            quarters=[self.quarter],
            status_mapping=self.status_mapping,
            group_by=GroupBy.AUTHOR,
            quarter_reports={"Q1 2024": self.quarter_report},
        )

        self.renderer = ConsoleRenderer(self.report)

    def test_render_ttm_with_tail_section(self, capsys):
        """Test console rendering with TTM report type including Tail section."""
        self.renderer.render(report_type=ReportType.TTM)

        captured = capsys.readouterr()
        output = captured.out

        # Check that Tail section is included
        assert "Tail (days from MP/External Test to Done)" in output
        assert "TIME TO MARKET & TAIL REPORT" in output

    def test_render_both_with_tail_section(self, capsys):
        """Test console rendering with BOTH report type including Tail section."""
        self.renderer.render(report_type=ReportType.BOTH)

        captured = capsys.readouterr()
        output = captured.out

        # Check that all sections are included
        assert "Time To Delivery" in output
        assert "Time To Market" in output
        assert "Tail (days from MP/External Test to Done)" in output
        assert "TIME TO DELIVERY, TIME TO MARKET & TAIL REPORT" in output

    def test_render_ttd_without_tail_section(self, capsys):
        """Test console rendering with TTD report type (should not include Tail section)."""
        self.renderer.render(report_type=ReportType.TTD)

        captured = capsys.readouterr()
        output = captured.out

        # Check that Tail section is NOT included
        assert "Tail (days from MP/External Test to Done)" not in output
        assert "TIME TO DELIVERY REPORT" in output


class TestTailMetricRendererIntegration:
    """Integration tests for Tail metric in all renderers."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create comprehensive mock report data
        self.quarter = Quarter("Q1 2024", datetime(2024, 1, 1), datetime(2024, 3, 31))
        self.status_mapping = StatusMapping(["Discovery"], ["Done"])

        # Create mock group metrics with all metrics including Tail
        self.group_metrics = GroupMetrics(
            group_name="TestAuthor",
            ttd_metrics=TimeMetrics([1, 2, 3], 2.0, 2.7, 3, [0, 1, 2], 1.0, 1.7),
            ttm_metrics=TimeMetrics([4, 5, 6], 5.0, 5.7, 3, [1, 0, 1], 0.7, 1.0),
            tail_metrics=TimeMetrics([1, 2, 3], 2.0, 2.7, 3, [0, 1, 0], 0.3, 0.7),
            total_tasks=6,
        )

        self.quarter_report = QuarterReport(
            quarter=self.quarter, groups={"TestAuthor": self.group_metrics}
        )

        self.report = TimeToMarketReport(
            quarters=[self.quarter],
            status_mapping=self.status_mapping,
            group_by=GroupBy.AUTHOR,
            quarter_reports={"Q1 2024": self.quarter_report},
        )

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_all_renderers_handle_tail_metric(self, mock_file, mock_mkdir):
        """Test that all renderers properly handle Tail metric data."""
        mock_file.return_value.__enter__.return_value.write = Mock()

        # Test CSV renderer
        csv_renderer = CSVRenderer(self.report)
        csv_result = csv_renderer.render(report_type=ReportType.TTM)

        # Test table renderer
        with patch("matplotlib.pyplot.savefig"), patch("matplotlib.pyplot.close"):
            with patch("matplotlib.pyplot.figure") as mock_fig:
                mock_ax = Mock()
                mock_table = Mock()
                mock_ax.table.return_value = mock_table
                mock_fig.return_value.add_axes.return_value = mock_ax

                # Mock table cell access
                mock_cell = Mock()
                mock_table.__getitem__ = Mock(return_value=mock_cell)

                table_renderer = TableRenderer(self.report)
                table_result = table_renderer.render(report_type=ReportType.TTM)

        # Test console renderer
        console_renderer = ConsoleRenderer(self.report)
        console_result = console_renderer.render(report_type=ReportType.TTM)

        # All renderers should complete without errors
        assert csv_result is not None
        assert table_result is not None
        assert console_result == ""  # Console renderer returns empty string

    def test_renderers_with_empty_tail_metrics(self):
        """Test renderers with empty Tail metrics."""
        # Create group metrics with empty Tail metrics
        empty_tail_metrics = GroupMetrics(
            group_name="TestAuthor",
            ttd_metrics=TimeMetrics([1, 2, 3], 2.0, 2.7, 3),
            ttm_metrics=TimeMetrics([4, 5, 6], 5.0, 5.7, 3),
            tail_metrics=TimeMetrics([], None, None, 0),
            total_tasks=6,
        )

        quarter_report = QuarterReport(
            quarter=self.quarter, groups={"TestAuthor": empty_tail_metrics}
        )

        report = TimeToMarketReport(
            quarters=[self.quarter],
            status_mapping=self.status_mapping,
            group_by=GroupBy.AUTHOR,
            quarter_reports={"Q1 2024": quarter_report},
        )

        # Test console renderer with empty Tail metrics
        console_renderer = ConsoleRenderer(report)
        console_result = console_renderer.render(report_type=ReportType.TTM)

        # Should complete without errors
        assert console_result == ""


class TestCSVLongFormat:
    """Tests for CSV renderer long format."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create two quarters for better testing
        self.quarter1 = Quarter("Q1 2024", datetime(2024, 1, 1), datetime(2024, 3, 31))
        self.quarter2 = Quarter("Q2 2024", datetime(2024, 4, 1), datetime(2024, 6, 30))
        self.status_mapping = StatusMapping(["Discovery"], ["Done"])

        # Create mock group metrics for Q1
        self.group_metrics_q1 = GroupMetrics(
            group_name="TestAuthor",
            ttd_metrics=TimeMetrics([1, 2, 3], 2.0, 2.7, 3),
            ttm_metrics=TimeMetrics([4, 5, 6], 5.0, 5.7, 3),
            tail_metrics=TimeMetrics([1, 2, 3], 2.0, 2.7, 3),
            total_tasks=6,
        )

        # Create mock group metrics for Q2
        self.group_metrics_q2 = GroupMetrics(
            group_name="TestAuthor",
            ttd_metrics=TimeMetrics([2, 3, 4], 3.0, 3.7, 3),
            ttm_metrics=TimeMetrics([5, 6, 7], 6.0, 6.7, 3),
            tail_metrics=TimeMetrics([2, 3, 4], 3.0, 3.7, 3),
            total_tasks=6,
        )

        self.quarter_report_q1 = QuarterReport(
            quarter=self.quarter1, groups={"TestAuthor": self.group_metrics_q1}
        )
        self.quarter_report_q2 = QuarterReport(
            quarter=self.quarter2, groups={"TestAuthor": self.group_metrics_q2}
        )

        self.report = TimeToMarketReport(
            quarters=[self.quarter1, self.quarter2],
            status_mapping=self.status_mapping,
            group_by=GroupBy.AUTHOR,
            quarter_reports={
                "Q1 2024": self.quarter_report_q1,
                "Q2 2024": self.quarter_report_q2,
            },
        )

        self.renderer = CSVRenderer(self.report)

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_render_long_format_structure(self, mock_file, mock_mkdir):
        """Test that long format creates correct structure (quarter as rows)."""
        mock_file.return_value.__enter__.return_value.write = Mock()

        result = self.renderer.render(report_type=ReportType.BOTH, csv_format="long")

        # Verify file was opened for writing
        mock_file.assert_called_once()

        # Get the written content
        written_content = "".join(
            call[0][0]
            for call in mock_file.return_value.__enter__.return_value.write.call_args_list
        )

        # Check that we have the right columns (without quarter prefix)
        assert "group_name" in written_content
        assert "quarter" in written_content
        assert "ttd_mean" in written_content
        assert "ttd_p85" in written_content
        assert "ttm_mean" in written_content
        assert "tail_mean" in written_content

        # Check that we don't have quarter-prefixed columns (which would be wide format)
        assert "Q1 2024_ttd_mean" not in written_content
        assert "Q2 2024_ttm_mean" not in written_content

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_render_long_format_ttd_only(self, mock_file, mock_mkdir):
        """Test long format with TTD report type."""
        mock_file.return_value.__enter__.return_value.write = Mock()

        result = self.renderer.render(report_type=ReportType.TTD, csv_format="long")

        # Get the written content
        written_content = "".join(
            call[0][0]
            for call in mock_file.return_value.__enter__.return_value.write.call_args_list
        )

        # Check that TTD columns are included
        assert "ttd_mean" in written_content
        assert "ttd_p85" in written_content
        assert "ttd_tasks" in written_content

        # Check that TTM and Tail columns are NOT included
        assert "ttm_mean" not in written_content
        assert "tail_mean" not in written_content

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_render_long_format_ttm_only(self, mock_file, mock_mkdir):
        """Test long format with TTM report type."""
        mock_file.return_value.__enter__.return_value.write = Mock()

        result = self.renderer.render(report_type=ReportType.TTM, csv_format="long")

        # Get the written content
        written_content = "".join(
            call[0][0]
            for call in mock_file.return_value.__enter__.return_value.write.call_args_list
        )

        # Check that TTM and Tail columns are included
        assert "ttm_mean" in written_content
        assert "ttm_p85" in written_content
        assert "tail_mean" in written_content
        assert "tail_p85" in written_content

        # Check that TTD columns are NOT included
        assert "ttd_mean" not in written_content

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_render_wide_format_default(self, mock_file, mock_mkdir):
        """Test that wide format is still the default."""
        mock_file.return_value.__enter__.return_value.write = Mock()

        # Call without csv_format parameter (should default to wide)
        result = self.renderer.render(report_type=ReportType.BOTH)

        # Get the written content
        written_content = "".join(
            call[0][0]
            for call in mock_file.return_value.__enter__.return_value.write.call_args_list
        )

        # Check that we have quarter-prefixed columns (wide format)
        assert "Q1 2024_ttd_mean" in written_content or "Q1 2024" in written_content

        # Check that we don't have separate quarter column (which would be long format)
        # In wide format, "quarter" might appear as part of column name, so we check structure
        lines = written_content.split("\n")
        if lines:
            header = lines[0]
            # Wide format should have many columns
            columns = header.split(",")
            assert len(columns) > 5  # Wide format has many columns


if __name__ == "__main__":
    pytest.main([__file__])
