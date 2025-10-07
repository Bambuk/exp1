"""Tests for pivot markers functionality in CSV file monitor."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from radiator.services.csv_file_monitor import CSVFileMonitor


class TestCSVFileMonitorPivotMarkers:
    """Test cases for pivot markers functionality in CSVFileMonitor."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def monitor(self, temp_dir):
        """Create a CSVFileMonitor instance with temp directory."""
        return CSVFileMonitor(reports_dir=temp_dir)

    def test_get_files_with_pivot_markers_empty(self, monitor):
        """Test getting files with pivot markers when none exist."""
        files = monitor.get_files_with_pivot_markers()
        assert files == []

    def test_get_files_with_pivot_markers_single_file(self, monitor, temp_dir):
        """Test getting files with pivot markers with one file."""
        # Create test CSV file
        csv_file = temp_dir / "test_file.csv"
        csv_file.write_text("test,data\n1,2")

        # Create pivot marker
        marker_file = temp_dir / ".upload_with_pivots_test_file.csv"
        marker_file.write_text("Upload with pivots request")

        files = monitor.get_files_with_pivot_markers()
        assert files == ["test_file.csv"]

    def test_get_files_with_pivot_markers_multiple_files(self, monitor, temp_dir):
        """Test getting files with pivot markers with multiple files."""
        # Create test CSV files
        csv_file1 = temp_dir / "test_file1.csv"
        csv_file1.write_text("test,data\n1,2")

        csv_file2 = temp_dir / "test_file2.csv"
        csv_file2.write_text("test,data\n3,4")

        # Create pivot markers
        marker_file1 = temp_dir / ".upload_with_pivots_test_file1.csv"
        marker_file1.write_text("Upload with pivots request 1")

        marker_file2 = temp_dir / ".upload_with_pivots_test_file2.csv"
        marker_file2.write_text("Upload with pivots request 2")

        files = monitor.get_files_with_pivot_markers()
        assert set(files) == {"test_file1.csv", "test_file2.csv"}

    def test_get_files_with_pivot_markers_missing_csv(self, monitor, temp_dir):
        """Test getting files with pivot markers when CSV file is missing."""
        # Create only pivot marker (no CSV file)
        marker_file = temp_dir / ".upload_with_pivots_missing_file.csv"
        marker_file.write_text("Upload with pivots request")

        files = monitor.get_files_with_pivot_markers()
        assert files == []

    def test_get_files_with_pivot_markers_non_csv(self, monitor, temp_dir):
        """Test getting files with pivot markers with non-CSV files."""
        # Create test non-CSV file
        txt_file = temp_dir / "test_file.txt"
        txt_file.write_text("test data")

        # Create pivot marker
        marker_file = temp_dir / ".upload_with_pivots_test_file.txt"
        marker_file.write_text("Upload with pivots request")

        files = monitor.get_files_with_pivot_markers()
        assert files == []

    def test_remove_pivot_upload_marker_success(self, monitor, temp_dir):
        """Test successful removal of pivot upload marker."""
        # Create test CSV file
        csv_file = temp_dir / "test_file.csv"
        csv_file.write_text("test,data\n1,2")

        # Create pivot marker
        marker_file = temp_dir / ".upload_with_pivots_test_file.csv"
        marker_file.write_text("Upload with pivots request")

        # Verify marker exists
        assert marker_file.exists()

        # Remove marker
        result = monitor.remove_pivot_upload_marker("test_file.csv")

        assert result is True
        assert not marker_file.exists()

    def test_remove_pivot_upload_marker_not_exists(self, monitor, temp_dir):
        """Test removal of pivot upload marker when it doesn't exist."""
        # Create test CSV file
        csv_file = temp_dir / "test_file.csv"
        csv_file.write_text("test,data\n1,2")

        # Try to remove non-existent marker
        result = monitor.remove_pivot_upload_marker("test_file.csv")

        assert result is False

    def test_remove_pivot_upload_marker_error(self, monitor, temp_dir):
        """Test removal of pivot upload marker when error occurs."""
        # Create test CSV file
        csv_file = temp_dir / "test_file.csv"
        csv_file.write_text("test,data\n1,2")

        # Create pivot marker
        marker_file = temp_dir / ".upload_with_pivots_test_file.csv"
        marker_file.write_text("Upload with pivots request")

        # Mock unlink to raise exception
        with patch.object(Path, "unlink", side_effect=Exception("Permission denied")):
            result = monitor.remove_pivot_upload_marker("test_file.csv")

            assert result is False

    def test_mixed_markers(self, monitor, temp_dir):
        """Test handling of both regular and pivot markers."""
        # Create test CSV file
        csv_file = temp_dir / "test_file.csv"
        csv_file.write_text("test,data\n1,2")

        # Create both types of markers
        regular_marker = temp_dir / ".upload_me_test_file.csv"
        regular_marker.write_text("Regular upload request")

        pivot_marker = temp_dir / ".upload_with_pivots_test_file.csv"
        pivot_marker.write_text("Pivot upload request")

        # Test getting regular markers
        regular_files = monitor.get_files_with_upload_markers()
        assert regular_files == ["test_file.csv"]

        # Test getting pivot markers
        pivot_files = monitor.get_files_with_pivot_markers()
        assert pivot_files == ["test_file.csv"]

        # Remove regular marker
        monitor.remove_upload_marker("test_file.csv")
        assert not regular_marker.exists()
        assert pivot_marker.exists()

        # Remove pivot marker
        monitor.remove_pivot_upload_marker("test_file.csv")
        assert not pivot_marker.exists()
