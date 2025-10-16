"""Test cleanup of upload marker files from state."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from radiator.telegram_bot.file_monitor import FileMonitor


class TestFileMonitorCleanupMarkers:
    """Test cases for cleaning up upload marker files from state."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def temp_state_file(self, temp_dir):
        """Create a temporary state file with upload marker files."""
        state_file = temp_dir / ".telegram_bot_state.json"

        # Create state with some regular files and upload marker files
        state_data = {
            "known_files": [
                "report1.csv",
                "report2.csv",
                "image.png",
                ".upload_me_report1.csv",  # Upload marker
                ".upload_me_report2.csv",  # Upload marker
                ".upload_me_image.png",  # Upload marker
                "document.pdf",
            ],
            "file_timestamps": {
                "report1.csv": 1234567890.0,
                "report2.csv": 1234567891.0,
                "image.png": 1234567892.0,
                ".upload_me_report1.csv": 1234567893.0,
                ".upload_me_report2.csv": 1234567894.0,
                ".upload_me_image.png": 1234567895.0,
                "document.pdf": 1234567896.0,
            },
            "last_updated": "2024-01-01T00:00:00",
        }

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

        return state_file

    def test_cleanup_upload_markers_from_state(self, temp_dir, temp_state_file):
        """Test that upload marker files are removed from state."""
        with patch(
            "radiator.telegram_bot.file_monitor.TelegramBotConfig"
        ) as mock_config:
            mock_config.get_reports_dir.return_value = temp_dir
            mock_config.MONITORED_EXTENSIONS = {".csv", ".png", ".jpg", ".jpeg", ".pdf"}

            # Create FileMonitor with custom state file
            monitor = FileMonitor()
            monitor.state_file = temp_state_file
            monitor._load_state()

            # Check initial state
            assert len(monitor.known_files) == 7
            assert ".upload_me_report1.csv" in monitor.known_files
            assert ".upload_me_report2.csv" in monitor.known_files
            assert ".upload_me_image.png" in monitor.known_files

            # Clean up upload markers
            monitor.cleanup_upload_markers_from_state()

            # Check that upload markers are removed
            assert len(monitor.known_files) == 4
            assert "report1.csv" in monitor.known_files
            assert "report2.csv" in monitor.known_files
            assert "image.png" in monitor.known_files
            assert "document.pdf" in monitor.known_files

            # Check that upload markers are removed
            assert ".upload_me_report1.csv" not in monitor.known_files
            assert ".upload_me_report2.csv" not in monitor.known_files
            assert ".upload_me_image.png" not in monitor.known_files

    def test_cleanup_during_initialization(self, temp_dir, temp_state_file):
        """Test that cleanup happens during FileMonitor initialization."""
        with patch(
            "radiator.telegram_bot.file_monitor.TelegramBotConfig"
        ) as mock_config:
            mock_config.get_reports_dir.return_value = temp_dir
            mock_config.MONITORED_EXTENSIONS = {".csv", ".png", ".jpg", ".jpeg", ".pdf"}

            # Create FileMonitor with custom state file
            monitor = FileMonitor()
            monitor.state_file = temp_state_file
            monitor._load_state()
            monitor.cleanup_upload_markers_from_state()

            # Check that upload markers are not in known_files
            for filename in monitor.known_files:
                assert not filename.startswith(
                    ".upload_me_"
                ), f"Upload marker found: {filename}"

    def test_cleanup_with_no_upload_markers(self, temp_dir):
        """Test cleanup when there are no upload marker files."""
        state_file = temp_dir / ".telegram_bot_state.json"

        # Create state without upload marker files
        state_data = {
            "known_files": [
                "report1.csv",
                "report2.csv",
                "image.png",
                "document.pdf",
            ],
            "file_timestamps": {
                "report1.csv": 1234567890.0,
                "report2.csv": 1234567891.0,
                "image.png": 1234567892.0,
                "document.pdf": 1234567896.0,
            },
            "last_updated": "2024-01-01T00:00:00",
        }

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

        with patch(
            "radiator.telegram_bot.file_monitor.TelegramBotConfig"
        ) as mock_config:
            mock_config.get_reports_dir.return_value = temp_dir
            mock_config.MONITORED_EXTENSIONS = {".csv", ".png", ".jpg", ".jpeg", ".pdf"}

            monitor = FileMonitor()
            monitor.state_file = state_file
            monitor._load_state()

            original_count = len(monitor.known_files)
            monitor.cleanup_upload_markers_from_state()

            # Should not change anything
            assert len(monitor.known_files) == original_count
            assert "report1.csv" in monitor.known_files
            assert "report2.csv" in monitor.known_files
            assert "image.png" in monitor.known_files
            assert "document.pdf" in monitor.known_files

    def test_cleanup_saves_state(self, temp_dir, temp_state_file):
        """Test that cleanup saves the updated state."""
        with patch(
            "radiator.telegram_bot.file_monitor.TelegramBotConfig"
        ) as mock_config:
            mock_config.get_reports_dir.return_value = temp_dir
            mock_config.MONITORED_EXTENSIONS = {".csv", ".png", ".jpg", ".jpeg", ".pdf"}

            monitor = FileMonitor()
            monitor.state_file = temp_state_file
            monitor._load_state()

            # Clean up upload markers
            monitor.cleanup_upload_markers_from_state()

            # Reload state and check
            monitor2 = FileMonitor()
            monitor2.state_file = temp_state_file
            monitor2._load_state()

            # Should not have upload markers
            for filename in monitor2.known_files:
                assert not filename.startswith(
                    ".upload_me_"
                ), f"Upload marker found: {filename}"

    def test_cleanup_with_mixed_files(self, temp_dir):
        """Test cleanup with various file types including upload markers."""
        state_file = temp_dir / ".telegram_bot_state.json"

        # Create state with mixed files
        state_data = {
            "known_files": [
                "report1.csv",
                "report2.csv",
                "image1.png",
                "image2.jpg",
                "document.pdf",
                ".upload_me_report1.csv",
                ".upload_me_image1.png",
                ".upload_me_document.pdf",
                ".hidden_file.csv",  # Not an upload marker, should be kept
                ".gitignore",  # Not an upload marker, should be kept
            ],
            "file_timestamps": {
                "report1.csv": 1234567890.0,
                "report2.csv": 1234567891.0,
                "image1.png": 1234567892.0,
                "image2.jpg": 1234567893.0,
                "document.pdf": 1234567894.0,
                ".upload_me_report1.csv": 1234567895.0,
                ".upload_me_image1.png": 1234567896.0,
                ".upload_me_document.pdf": 1234567897.0,
                ".hidden_file.csv": 1234567898.0,
                ".gitignore": 1234567899.0,
            },
            "last_updated": "2024-01-01T00:00:00",
        }

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

        with patch(
            "radiator.telegram_bot.file_monitor.TelegramBotConfig"
        ) as mock_config:
            mock_config.get_reports_dir.return_value = temp_dir
            mock_config.MONITORED_EXTENSIONS = {".csv", ".png", ".jpg", ".jpeg", ".pdf"}

            monitor = FileMonitor()
            monitor.state_file = state_file
            monitor._load_state()
            monitor.cleanup_upload_markers_from_state()

            # Should keep regular files and hidden files, but remove upload markers
            assert len(monitor.known_files) == 7
            assert "report1.csv" in monitor.known_files
            assert "report2.csv" in monitor.known_files
            assert "image1.png" in monitor.known_files
            assert "image2.jpg" in monitor.known_files
            assert "document.pdf" in monitor.known_files
            assert ".hidden_file.csv" in monitor.known_files
            assert ".gitignore" in monitor.known_files

            # Should remove upload markers
            assert ".upload_me_report1.csv" not in monitor.known_files
            assert ".upload_me_image1.png" not in monitor.known_files
            assert ".upload_me_document.pdf" not in monitor.known_files
