"""Test that file monitor excludes upload marker files."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from radiator.telegram_bot.file_monitor import FileMonitor


class TestFileMonitorUploadMarkers:
    """Test cases for file monitor excluding upload marker files."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def monitor(self, temp_dir):
        """Create a FileMonitor instance with temporary directory."""
        with patch(
            "radiator.telegram_bot.file_monitor.TelegramBotConfig"
        ) as mock_config:
            mock_config.get_reports_dir.return_value = temp_dir
            mock_config.MONITORED_EXTENSIONS = {".csv", ".png", ".jpg", ".jpeg", ".pdf"}
            monitor = FileMonitor()
            return monitor

    def test_get_current_files_excludes_upload_markers(self, monitor, temp_dir):
        """Test that get_current_files excludes upload marker files."""
        # Create test files
        (temp_dir / "report1.csv").touch()
        (temp_dir / "report2.csv").touch()
        (temp_dir / "image.png").touch()

        # Create upload marker files
        (temp_dir / ".upload_me_report1.csv").touch()
        (temp_dir / ".upload_me_report2.csv").touch()
        (temp_dir / ".upload_me_image.png").touch()

        # Create other hidden files
        (temp_dir / ".hidden_file.csv").touch()
        (temp_dir / ".gitignore").touch()

        current_files = monitor.get_current_files()

        # Should only include regular files, not upload markers
        assert "report1.csv" in current_files
        assert "report2.csv" in current_files
        assert "image.png" in current_files

        # Should exclude upload marker files
        assert ".upload_me_report1.csv" not in current_files
        assert ".upload_me_report2.csv" not in current_files
        assert ".upload_me_image.png" not in current_files

        # Should exclude other hidden files (but .hidden_file.csv has .csv extension so it's included)
        assert ".gitignore" not in current_files

    def test_get_new_files_excludes_upload_markers(self, monitor, temp_dir):
        """Test that get_new_files excludes upload marker files."""
        # Create test files
        (temp_dir / "report1.csv").touch()
        (temp_dir / "report2.csv").touch()

        # Create upload marker files
        (temp_dir / ".upload_me_report1.csv").touch()
        (temp_dir / ".upload_me_report2.csv").touch()

        new_files = monitor.get_new_files()

        # Should only include regular files, not upload markers
        assert "report1.csv" in new_files
        assert "report2.csv" in new_files

        # Should exclude upload marker files
        assert ".upload_me_report1.csv" not in new_files
        assert ".upload_me_report2.csv" not in new_files

    def test_get_file_path_works_with_upload_markers(self, monitor, temp_dir):
        """Test that get_file_path works correctly with upload markers."""
        # Create test file
        (temp_dir / "report1.csv").touch()

        # Create upload marker file
        (temp_dir / ".upload_me_report1.csv").touch()

        # Should find regular file
        file_path = monitor.get_file_path("report1.csv")
        assert file_path is not None
        assert file_path.name == "report1.csv"

        # Should also find upload marker file if requested directly
        marker_path = monitor.get_file_path(".upload_me_report1.csv")
        assert marker_path is not None
        assert marker_path.name == ".upload_me_report1.csv"

    def test_get_file_info_works_with_upload_markers(self, monitor, temp_dir):
        """Test that get_file_info works correctly with upload markers."""
        # Create test file
        (temp_dir / "report1.csv").write_text("Name,Value\nTest,123\n")

        # Create upload marker file
        (temp_dir / ".upload_me_report1.csv").write_text("Upload request\n")

        # Should get info for regular file
        file_info = monitor.get_file_info("report1.csv")
        assert file_info is not None
        assert file_info["name"] == "report1.csv"
        assert file_info["size"] > 0

        # Should also get info for upload marker file if requested directly
        marker_info = monitor.get_file_info(".upload_me_report1.csv")
        assert marker_info is not None
        assert marker_info["name"] == ".upload_me_report1.csv"
        assert marker_info["size"] > 0

    def test_upload_marker_files_are_ignored_in_monitoring(self, monitor, temp_dir):
        """Test that upload marker files are completely ignored in monitoring."""
        # Create test files
        (temp_dir / "report1.csv").touch()
        (temp_dir / "report2.csv").touch()

        # Create upload marker files
        (temp_dir / ".upload_me_report1.csv").touch()
        (temp_dir / ".upload_me_report2.csv").touch()

        # Get current files
        current_files = monitor.get_current_files()

        # Get new files
        new_files = monitor.get_new_files()

        # Upload marker files should not appear anywhere
        all_files = set(current_files.keys()) | new_files

        for file_name in all_files:
            assert not file_name.startswith(
                ".upload_me_"
            ), f"Upload marker file found: {file_name}"

    def test_mixed_file_types_with_upload_markers(self, monitor, temp_dir):
        """Test with mixed file types including upload markers."""
        # Create various file types
        files_to_create = [
            "report1.csv",
            "report2.csv",
            "image1.png",
            "image2.jpg",
            "document.pdf",
            "data.xlsx",  # Not monitored
            "text.txt",  # Not monitored
        ]

        for filename in files_to_create:
            (temp_dir / filename).touch()

        # Create upload markers for some files
        upload_markers = [
            ".upload_me_report1.csv",
            ".upload_me_image1.png",
            ".upload_me_document.pdf",
        ]

        for marker in upload_markers:
            (temp_dir / marker).touch()

        current_files = monitor.get_current_files()

        # Should include all monitored file types
        assert "report1.csv" in current_files
        assert "report2.csv" in current_files
        assert "image1.png" in current_files
        assert "image2.jpg" in current_files
        assert "document.pdf" in current_files

        # Should exclude non-monitored files
        assert "data.xlsx" not in current_files
        assert "text.txt" not in current_files

        # Should exclude all upload marker files
        for marker in upload_markers:
            assert marker not in current_files
