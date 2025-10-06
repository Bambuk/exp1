"""Unit tests for CSV file monitor functionality."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from radiator.services.csv_file_monitor import CSVFileMonitor


class TestCSVFileMonitor:
    """Test cases for CSVFileMonitor."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def monitor(self, temp_dir):
        """Create a CSVFileMonitor instance with temporary directory."""
        with patch(
            "radiator.services.csv_file_monitor.GoogleSheetsConfig"
        ) as mock_config:
            mock_config.get_reports_dir.return_value = temp_dir
            mock_config.STATE_FILE = ".test_state.json"
            monitor = CSVFileMonitor()
            # Clear any loaded state
            monitor.known_files = set()
            monitor.processed_files = set()
            monitor.file_timestamps = {}
            return monitor

    def test_init(self, monitor):
        """Test CSVFileMonitor initialization."""
        assert monitor.reports_dir is not None
        assert str(monitor.state_file) == ".test_state.json"
        assert monitor.known_files == set()
        assert monitor.processed_files == set()
        assert monitor.file_timestamps == {}

    def test_load_state_empty(self, monitor):
        """Test loading state from non-existent file."""
        with patch("pathlib.Path.exists", return_value=False):
            monitor._load_state()
            assert monitor.known_files == set()
            assert monitor.processed_files == set()
            assert monitor.file_timestamps == {}

    def test_get_current_csv_files(self, monitor, temp_dir):
        """Test getting current CSV files from directory."""
        # Create test files
        (temp_dir / "file1.csv").touch()
        (temp_dir / "file2.csv").touch()
        (temp_dir / "file3.txt").touch()  # Non-CSV file
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "file4.csv").touch()  # File in subdirectory

        current_files = monitor.get_current_csv_files()

        # Should only include CSV files in the root directory
        assert "file1.csv" in current_files
        assert "file2.csv" in current_files
        assert "file3.txt" not in current_files
        assert "file4.csv" not in current_files

    def test_get_files_with_upload_markers(self, monitor, temp_dir):
        """Test getting files with upload markers."""
        # Create test files and markers
        (temp_dir / "file1.csv").touch()
        (temp_dir / "file2.csv").touch()
        (temp_dir / ".upload_me_file1.csv").touch()
        (temp_dir / ".upload_me_file2.csv").touch()
        (temp_dir / ".upload_me_nonexistent.csv").touch()  # Marker without file

        files_with_markers = monitor.get_files_with_upload_markers()

        assert "file1.csv" in files_with_markers
        assert "file2.csv" in files_with_markers
        assert "nonexistent.csv" not in files_with_markers

    def test_get_unprocessed_files(self, monitor, temp_dir):
        """Test getting unprocessed files."""
        # Create test files
        (temp_dir / "file1.csv").touch()
        (temp_dir / "file2.csv").touch()
        (temp_dir / "file3.csv").touch()

        # Mark some files as processed
        monitor.processed_files = {"file1.csv"}
        monitor.known_files = {"file1.csv", "file2.csv", "file3.csv"}

        unprocessed_files = monitor.get_unprocessed_files()

        assert "file1.csv" not in unprocessed_files
        assert "file2.csv" in unprocessed_files
        assert "file3.csv" in unprocessed_files

    def test_remove_upload_marker_success(self, monitor, temp_dir):
        """Test successful upload marker removal."""
        marker_file = temp_dir / ".upload_me_test.csv"
        marker_file.touch()

        result = monitor.remove_upload_marker("test.csv")

        assert result is True
        assert not marker_file.exists()

    def test_remove_upload_marker_not_found(self, monitor, temp_dir):
        """Test upload marker removal when marker doesn't exist."""
        result = monitor.remove_upload_marker("nonexistent.csv")

        assert result is False

    def test_mark_file_processed(self, monitor):
        """Test marking file as processed."""
        monitor.mark_file_processed("test.csv")

        assert "test.csv" in monitor.processed_files

    def test_cleanup_old_files(self, monitor, temp_dir):
        """Test cleaning up old files from state."""
        # Add some old files to state
        monitor.known_files = {"old_file.csv", "new_file.csv"}
        monitor.processed_files = {"old_file.csv"}
        monitor.file_timestamps = {
            "old_file.csv": 1000000000,  # Very old timestamp
            "new_file.csv": 2000000000,  # Recent timestamp
        }

        # Create actual files
        (temp_dir / "new_file.csv").touch()
        # old_file.csv doesn't exist

        monitor.cleanup_old_files()

        # old_file.csv should be removed from state
        assert "old_file.csv" not in monitor.known_files
        assert "old_file.csv" not in monitor.processed_files
        assert "old_file.csv" not in monitor.file_timestamps

        # new_file.csv should remain
        assert "new_file.csv" in monitor.known_files
        assert "new_file.csv" in monitor.file_timestamps

    def test_get_stats(self, monitor, temp_dir):
        """Test getting statistics."""
        # Set up some state
        monitor.known_files = {"file1.csv", "file2.csv", "file3.csv"}
        monitor.processed_files = {"file1.csv", "file2.csv"}

        # Create some files
        (temp_dir / "file1.csv").touch()
        (temp_dir / "file2.csv").touch()
        (temp_dir / "file3.csv").touch()
        (temp_dir / "file4.csv").touch()

        stats = monitor.get_stats()

        assert stats["known_files"] == 3
        assert stats["processed_files"] == 2
        assert stats["unprocessed_files"] == 2  # file3.csv and file4.csv
        assert stats["total_files"] == 4  # All CSV files in directory
