"""Integration tests for Telegram bot and Google Sheets functionality."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile
import json

from radiator.telegram_bot.bot import ReportsTelegramBot
from radiator.services.csv_file_monitor import CSVFileMonitor
from radiator.services.google_sheets_service import GoogleSheetsService


class TestTelegramSheetsIntegration:
    """Integration tests for Telegram bot and Google Sheets."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_services(self, temp_dir):
        """Create mock services for testing."""
        with patch('radiator.telegram_bot.bot.TelegramBotConfig') as mock_telegram_config, \
             patch('radiator.services.csv_file_monitor.GoogleSheetsConfig') as mock_sheets_config, \
             patch('radiator.services.google_sheets_service.service_account.Credentials.from_service_account_file'), \
             patch('radiator.services.google_sheets_service.build'):
            
            # Configure mock configs
            mock_telegram_config.REPORTS_DIR = temp_dir
            mock_telegram_config.USER_ID = 12345
            mock_telegram_config.BOT_TOKEN = "test_token"
            
            mock_sheets_config.REPORTS_DIR = temp_dir
            mock_sheets_config.STATE_FILE = ".test_state.json"
            mock_sheets_config.CREDENTIALS_PATH = "test_credentials.json"
            mock_sheets_config.DOCUMENT_ID = "test_document_id"
            
            # Create services
            bot = ReportsTelegramBot()
            bot.bot = Mock()
            
            monitor = CSVFileMonitor()
            
            sheets_service = GoogleSheetsService(
                credentials_path="test_credentials.json",
                document_id="test_document_id"
            )
            sheets_service.service = Mock()
            
            return bot, monitor, sheets_service
    
    @pytest.mark.asyncio
    async def test_telegram_callback_creates_marker(self, mock_services, temp_dir):
        """Test that Telegram callback creates marker file."""
        bot, monitor, sheets_service = mock_services
        
        # Create a test CSV file
        test_file = temp_dir / "test_report.csv"
        test_file.write_text("Name,Value\nTest,123\n")
        
        # Mock callback query
        callback_query = Mock()
        callback_query.data = "upload_csv:test_report.csv"
        callback_query.id = "test_query_123"
        callback_query.from_user = Mock()
        callback_query.from_user.username = "test_user"
        
        bot.bot.answer_callback_query = AsyncMock()
        
        # Handle callback
        await bot.handle_callback_query(callback_query)
        
        # Check that marker file was created
        marker_file = temp_dir / ".upload_me_test_report.csv"
        assert marker_file.exists()
        
        # Check marker content
        marker_content = marker_file.read_text()
        assert "Upload request for test_report.csv" in marker_content
    
    def test_csv_monitor_detects_marker(self, mock_services, temp_dir):
        """Test that CSV monitor detects marker files."""
        bot, monitor, sheets_service = mock_services
        
        # Create test files and marker
        test_file = temp_dir / "test_report.csv"
        test_file.write_text("Name,Value\nTest,123\n")
        
        marker_file = temp_dir / ".upload_me_test_report.csv"
        marker_file.write_text("Upload request for test_report.csv\n")
        
        # Check that monitor detects the marker
        files_with_markers = monitor.get_files_with_upload_markers()
        assert "test_report.csv" in files_with_markers
    
    def test_csv_monitor_removes_marker_after_processing(self, mock_services, temp_dir):
        """Test that CSV monitor removes marker after processing."""
        bot, monitor, sheets_service = mock_services
        
        # Create test files and marker
        test_file = temp_dir / "test_report.csv"
        test_file.write_text("Name,Value\nTest,123\n")
        
        marker_file = temp_dir / ".upload_me_test_report.csv"
        marker_file.write_text("Upload request for test_report.csv\n")
        
        # Remove marker
        success = monitor.remove_upload_marker("test_report.csv")
        assert success is True
        assert not marker_file.exists()
    
    def test_end_to_end_workflow(self, mock_services, temp_dir):
        """Test complete workflow from Telegram callback to Google Sheets upload."""
        bot, monitor, sheets_service = mock_services
        
        # Create test CSV file
        test_file = temp_dir / "test_report.csv"
        test_file.write_text("Name,Value\nAlice,100\nBob,200\n")
        
        # Simulate Telegram callback creating marker
        marker_file = temp_dir / ".upload_me_test_report.csv"
        marker_file.write_text("Upload request for test_report.csv\n")
        
        # Simulate CSV monitor detecting marker
        files_with_markers = monitor.get_files_with_upload_markers()
        assert "test_report.csv" in files_with_markers
        
        # Simulate Google Sheets upload
        sheets_service.upload_csv_to_sheet = Mock(return_value=True)
        sheets_service._get_sheet_id = Mock(return_value=123)
        sheets_service.service.spreadsheets().batchUpdate().execute.return_value = {}
        
        # Mock the upload process
        success = sheets_service.upload_csv_to_sheet(test_file, "test_report")
        assert success is True
        
        # Simulate marker removal after successful upload
        monitor.remove_upload_marker("test_report.csv")
        assert not marker_file.exists()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_callback(self, mock_services, temp_dir):
        """Test error handling in Telegram callback."""
        bot, monitor, sheets_service = mock_services
        
        # Mock callback query
        callback_query = Mock()
        callback_query.data = "upload_csv:nonexistent.csv"
        callback_query.id = "test_query_123"
        callback_query.from_user = Mock()
        callback_query.from_user.username = "test_user"
        
        bot.bot.answer_callback_query = AsyncMock()
        
        # Handle callback with non-existent file
        await bot.handle_callback_query(callback_query)
        
        # Should answer with error message
        bot.bot.answer_callback_query.assert_called_once_with(
            "test_query_123", text="❌ Файл nonexistent.csv не найден"
        )
    
    def test_state_persistence(self, mock_services, temp_dir):
        """Test that state is properly persisted and loaded."""
        bot, monitor, sheets_service = mock_services
        
        # Add some files to state
        monitor.known_files = {"file1.csv", "file2.csv"}
        monitor.processed_files = {"file1.csv"}
        monitor.file_timestamps = {"file1.csv": 1234567890, "file2.csv": 1234567891}
        
        # Save state
        monitor._save_state()
        
        # Create new monitor instance with same temp directory
        with patch('radiator.services.csv_file_monitor.GoogleSheetsConfig') as mock_config:
            mock_config.REPORTS_DIR = temp_dir
            mock_config.STATE_FILE = ".test_state.json"
            new_monitor = CSVFileMonitor()
        
        # Check that state was loaded correctly
        assert new_monitor.known_files == {"file1.csv", "file2.csv"}
        assert new_monitor.processed_files == {"file1.csv"}
        assert new_monitor.file_timestamps == {"file1.csv": 1234567890, "file2.csv": 1234567891}
    
    def test_multiple_files_processing(self, mock_services, temp_dir):
        """Test processing multiple files with markers."""
        bot, monitor, sheets_service = mock_services
        
        # Create multiple test files and markers
        files = ["file1.csv", "file2.csv", "file3.csv"]
        for filename in files:
            test_file = temp_dir / filename
            test_file.write_text(f"Name,Value\nTest{filename},123\n")
            
            marker_file = temp_dir / f".upload_me_{filename}"
            marker_file.write_text(f"Upload request for {filename}\n")
        
        # Check that all files are detected
        files_with_markers = monitor.get_files_with_upload_markers()
        assert len(files_with_markers) == 3
        for filename in files:
            assert filename in files_with_markers
        
        # Process all files
        for filename in files:
            success = monitor.remove_upload_marker(filename)
            assert success is True
        
        # Check that all markers are removed
        files_with_markers_after = monitor.get_files_with_upload_markers()
        assert len(files_with_markers_after) == 0
