"""Unit tests for Telegram file monitor marker skipping."""

import pytest

from radiator.telegram_bot.file_monitor import FileMonitor


class TestFileMonitorMarkerSkipping:
    """Test cases for marker file skipping in FileMonitor."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for testing."""
        return tmp_path

    @pytest.fixture
    def file_monitor(self, temp_dir):
        """Create a FileMonitor instance with temporary directory."""
        monitor = FileMonitor(reports_dir=temp_dir)
        return monitor

    def test_skip_upload_me_markers(self, file_monitor, temp_dir):
        """Test that .upload_me_ marker files are skipped."""
        # Create a regular CSV file
        regular_file = temp_dir / "test_report.csv"
        regular_file.write_text("col1,col2\nval1,val2")

        # Create a .upload_me_ marker file
        marker_file = temp_dir / ".upload_me_test_report.csv"
        marker_file.write_text("marker content")

        # Get current files
        current_files = file_monitor.get_current_files()

        # Only the regular CSV should be found, not the marker
        assert "test_report.csv" in current_files
        assert ".upload_me_test_report.csv" not in current_files
        assert len(current_files) == 1

    def test_skip_upload_with_pivots_markers(self, file_monitor, temp_dir):
        """Test that .upload_with_pivots_ marker files are skipped."""
        # Create a regular CSV file
        regular_file = temp_dir / "details_report.csv"
        regular_file.write_text("col1,col2\nval1,val2")

        # Create a .upload_with_pivots_ marker file
        marker_file = temp_dir / ".upload_with_pivots_details_report.csv"
        marker_file.write_text("pivot marker content")

        # Get current files
        current_files = file_monitor.get_current_files()

        # Only the regular CSV should be found, not the marker
        assert "details_report.csv" in current_files
        assert ".upload_with_pivots_details_report.csv" not in current_files
        assert len(current_files) == 1

    def test_skip_both_marker_types(self, file_monitor, temp_dir):
        """Test that both marker types are skipped."""
        # Create regular CSV files
        file1 = temp_dir / "report1.csv"
        file1.write_text("data1")
        file2 = temp_dir / "report2.csv"
        file2.write_text("data2")

        # Create both types of markers
        marker1 = temp_dir / ".upload_me_report1.csv"
        marker1.write_text("marker1")
        marker2 = temp_dir / ".upload_with_pivots_report2.csv"
        marker2.write_text("marker2")

        # Get current files
        current_files = file_monitor.get_current_files()

        # Only regular CSV files should be found
        assert "report1.csv" in current_files
        assert "report2.csv" in current_files
        assert ".upload_me_report1.csv" not in current_files
        assert ".upload_with_pivots_report2.csv" not in current_files
        assert len(current_files) == 2

    def test_detect_new_files_without_markers(self, file_monitor, temp_dir):
        """Test that new file detection excludes markers."""
        # Create initial file
        file1 = temp_dir / "old_report.csv"
        file1.write_text("old data")

        # First scan
        new_files1 = file_monitor.get_new_files()
        assert "old_report.csv" in new_files1

        # Create new CSV and markers
        file2 = temp_dir / "new_report.csv"
        file2.write_text("new data")
        marker1 = temp_dir / ".upload_me_new_report.csv"
        marker1.write_text("marker")
        marker2 = temp_dir / ".upload_with_pivots_new_report.csv"
        marker2.write_text("pivot marker")

        # Second scan
        new_files2 = file_monitor.get_new_files()

        # Only the new CSV should be detected, not markers
        assert "new_report.csv" in new_files2
        assert ".upload_me_new_report.csv" not in new_files2
        assert ".upload_with_pivots_new_report.csv" not in new_files2
        assert len(new_files2) == 1

    def test_png_files_not_affected(self, file_monitor, temp_dir):
        """Test that PNG files are still detected normally."""
        # Create PNG file
        png_file = temp_dir / "chart.png"
        png_file.write_bytes(b"fake png data")

        # Create CSV with marker
        csv_file = temp_dir / "report.csv"
        csv_file.write_text("csv data")
        marker = temp_dir / ".upload_with_pivots_report.csv"
        marker.write_text("marker")

        # Get current files
        current_files = file_monitor.get_current_files()

        # Both CSV and PNG should be found, but not marker
        assert "chart.png" in current_files
        assert "report.csv" in current_files
        assert ".upload_with_pivots_report.csv" not in current_files
        assert len(current_files) == 2
