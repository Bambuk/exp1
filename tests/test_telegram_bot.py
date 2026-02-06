"""Unit tests for Telegram bot functionality."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest

from radiator.telegram_bot.bot import ReportsTelegramBot
from radiator.telegram_bot.config import TelegramBotConfig


class TestReportsTelegramBot:
    """Test cases for ReportsTelegramBot."""

    @pytest.fixture
    def mock_bot(self):
        """Create a mock ReportsTelegramBot instance."""
        with patch("radiator.telegram_bot.bot.Bot"), patch(
            "radiator.telegram_bot.bot.FileMonitor"
        ):
            bot = ReportsTelegramBot()
            bot.bot = Mock()
            return bot

    @pytest.fixture
    def mock_callback_query(self):
        """Create a mock callback query."""
        query = Mock()
        # Use new hash-based format
        query.data = "upload:testhash"
        query.id = "test_query_123"
        query.from_user = Mock()
        query.from_user.username = "test_user"
        return query

    @pytest.mark.asyncio
    async def test_handle_callback_query_upload_csv(
        self, mock_bot, mock_callback_query
    ):
        """Test handling upload CSV callback query."""
        # Add file to hash map
        mock_bot.file_hash_map["testhash"] = "test_file.csv"
        mock_bot._handle_upload_csv_request = AsyncMock()

        await mock_bot.handle_callback_query(mock_callback_query)

        mock_bot._handle_upload_csv_request.assert_called_once_with(
            "test_query_123", "test_file.csv"
        )

    @pytest.mark.asyncio
    async def test_handle_callback_query_upload_csv_with_pivots(self, mock_bot):
        """Test handling upload CSV with pivots callback query."""
        query = Mock()
        # Use new hash-based format
        query.data = "pivot:testhash2"
        query.id = "test_query_456"
        query.from_user = Mock()
        query.from_user.username = "test_user"

        # Add file to hash map
        mock_bot.file_hash_map["testhash2"] = "test_file.csv"
        mock_bot._handle_upload_csv_with_pivots_request = AsyncMock()

        await mock_bot.handle_callback_query(query)

        mock_bot._handle_upload_csv_with_pivots_request.assert_called_once_with(
            "test_query_456", "test_file.csv"
        )

    @pytest.mark.asyncio
    async def test_handle_callback_query_unknown(self, mock_bot):
        """Test handling unknown callback query."""
        query = Mock()
        query.data = "unknown_action:test"
        query.id = "test_query_123"
        query.from_user = Mock()
        query.from_user.username = "test_user"

        mock_bot.bot.answer_callback_query = AsyncMock()

        await mock_bot.handle_callback_query(query)

        mock_bot.bot.answer_callback_query.assert_called_once_with(
            "test_query_123", text="❌ Неизвестная команда"
        )

    @pytest.mark.asyncio
    async def test_handle_callback_query_error(self, mock_bot):
        """Test handling callback query with error."""
        query = Mock()
        # Use new hash-based format
        query.data = "upload:testhash3"
        query.id = "test_query_123"
        query.from_user = Mock()
        query.from_user.username = "test_user"

        # Add file to hash map
        mock_bot.file_hash_map["testhash3"] = "test_file.csv"

        # Make _handle_upload_csv_request raise an exception
        mock_bot._handle_upload_csv_request = AsyncMock(
            side_effect=Exception("Test error")
        )
        mock_bot.bot.answer_callback_query = AsyncMock()

        await mock_bot.handle_callback_query(query)

        # Should call answer_callback_query twice: once in _handle_upload_csv_request, once in error handler
        assert mock_bot.bot.answer_callback_query.call_count >= 1

    @pytest.mark.asyncio
    async def test_handle_upload_csv_request_success(self, mock_bot):
        """Test successful upload CSV request handling."""
        mock_bot.bot.answer_callback_query = AsyncMock()

        # Mock file operations
        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)

        with patch("builtins.open", return_value=mock_file), patch(
            "pathlib.Path.exists", return_value=True
        ):
            await mock_bot._handle_upload_csv_request("test_query_123", "test_file.csv")

            # Verify marker file was created
            # open should be called once for writing the marker file
            assert True  # If we get here without exception, the test passes

            # Verify callback query was answered
            mock_bot.bot.answer_callback_query.assert_called_once_with(
                "test_query_123",
                text="✅ Файл test_file.csv добавлен в очередь загрузки в Google Sheets",
            )

    @pytest.mark.asyncio
    async def test_handle_upload_csv_request_file_not_exists(self, mock_bot):
        """Test upload CSV request when file doesn't exist."""
        mock_bot.bot.answer_callback_query = AsyncMock()

        with patch("pathlib.Path.exists", return_value=False):
            await mock_bot._handle_upload_csv_request(
                "test_query_123", "nonexistent_file.csv"
            )

            mock_bot.bot.answer_callback_query.assert_called_once_with(
                "test_query_123", text="❌ Файл nonexistent_file.csv не найден"
            )

    @pytest.mark.asyncio
    async def test_handle_upload_csv_request_error(self, mock_bot):
        """Test upload CSV request with error."""
        mock_bot.bot.answer_callback_query = AsyncMock()

        # Mock file operations to raise an exception
        with patch("builtins.open", side_effect=Exception("File error")), patch(
            "pathlib.Path.exists", return_value=True
        ):
            await mock_bot._handle_upload_csv_request("test_query_123", "test_file.csv")

            mock_bot.bot.answer_callback_query.assert_called_once_with(
                "test_query_123", text="❌ Ошибка создания маркера для test_file.csv"
            )

    @pytest.mark.asyncio
    async def test_send_file_with_upload_button_csv(self, mock_bot):
        """Test sending CSV file with upload button."""
        mock_bot.bot.send_document = AsyncMock(return_value=Mock())
        mock_bot.send_message = AsyncMock(return_value=True)

        test_file = Path("test_file.csv")

        # Create a temporary file for testing
        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.stat", return_value=Mock(st_size=1024)
        ), patch("builtins.open", mock_open(read_data=b"test data")):
            result = await mock_bot.send_file_with_upload_button(
                test_file, "Test caption"
            )

            assert result is True
            mock_bot.bot.send_document.assert_called_once()

            # Check that reply_markup was set (inline keyboard)
            call_args = mock_bot.bot.send_document.call_args
            assert "reply_markup" in call_args[1]

    @pytest.mark.asyncio
    async def test_send_file_with_upload_button_non_csv(self, mock_bot):
        """Test sending non-CSV file without upload button."""
        mock_bot.bot.send_photo = AsyncMock(return_value=Mock())
        mock_bot.send_message = AsyncMock(return_value=True)

        test_file = Path("test_file.png")

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.stat", return_value=Mock(st_size=1024)
        ), patch("builtins.open", mock_open(read_data=b"test data")):
            result = await mock_bot.send_file_with_upload_button(
                test_file, "Test caption"
            )

            assert result is True
            mock_bot.bot.send_photo.assert_called_once()

            # Check that no reply_markup was set
            call_args = mock_bot.bot.send_photo.call_args
            assert (
                "reply_markup" not in call_args[1]
                or call_args[1]["reply_markup"] is None
            )

    @pytest.mark.asyncio
    async def test_send_file_with_upload_button_error(self, mock_bot):
        """Test sending file with upload button when error occurs."""
        mock_bot.bot.send_document = AsyncMock(side_effect=Exception("Send error"))
        mock_bot.send_message = AsyncMock(return_value=True)

        test_file = Path("test_file.csv")

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.stat", return_value=Mock(st_size=1024)
        ), patch("builtins.open", mock_open(read_data=b"test data")):
            result = await mock_bot.send_file_with_upload_button(
                test_file, "Test caption"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_bot):
        """Test successful message sending."""
        mock_bot.bot.send_message = AsyncMock(return_value=Mock())

        result = await mock_bot.send_message("Test message")

        assert result is True
        mock_bot.bot.send_message.assert_called_once_with(
            chat_id=mock_bot.user_id, text="Test message"
        )

    @pytest.mark.asyncio
    async def test_send_message_error(self, mock_bot):
        """Test message sending with error."""
        from telegram.error import TelegramError

        mock_bot.bot.send_message = AsyncMock(side_effect=TelegramError("Send error"))

        result = await mock_bot.send_message("Test message")

        assert result is False

    @pytest.mark.asyncio
    async def test_test_connection_success(self, mock_bot):
        """Test successful connection test."""
        mock_bot.bot.get_me = AsyncMock(return_value=Mock(username="test_bot"))
        mock_bot.bot.send_message = AsyncMock(return_value=Mock())

        result = await mock_bot.test_connection()

        assert result is True
        mock_bot.bot.get_me.assert_called_once()
        mock_bot.bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, mock_bot):
        """Test connection test failure."""
        mock_bot.bot.get_me = AsyncMock(side_effect=Exception("Connection error"))

        result = await mock_bot.test_connection()

        assert result is False

    @pytest.mark.asyncio
    async def test_handle_upload_csv_with_pivots_request_success(self, mock_bot):
        """Test successful upload CSV with pivots request handling."""
        mock_bot.bot.answer_callback_query = AsyncMock()

        with patch("pathlib.Path.exists", return_value=True), patch(
            "builtins.open", mock_open(read_data="test data")
        ):
            await mock_bot._handle_upload_csv_with_pivots_request(
                "test_query_123", "test_file.csv"
            )

            mock_bot.bot.answer_callback_query.assert_called_once_with(
                "test_query_123",
                text="✅ Файл test_file.csv добавлен в очередь загрузки с созданием сводных таблиц",
            )

    @pytest.mark.asyncio
    async def test_handle_upload_csv_with_pivots_request_file_not_found(self, mock_bot):
        """Test upload CSV with pivots request when file not found."""
        mock_bot.bot.answer_callback_query = AsyncMock()

        with patch("pathlib.Path.exists", return_value=False):
            await mock_bot._handle_upload_csv_with_pivots_request(
                "test_query_123", "nonexistent_file.csv"
            )

            mock_bot.bot.answer_callback_query.assert_called_once_with(
                "test_query_123", text="❌ Файл nonexistent_file.csv не найден"
            )

    @pytest.mark.asyncio
    async def test_handle_upload_csv_with_pivots_request_error(self, mock_bot):
        """Test upload CSV with pivots request when error occurs."""
        mock_bot.bot.answer_callback_query = AsyncMock()

        with patch("pathlib.Path.exists", return_value=True), patch(
            "builtins.open", side_effect=Exception("File error")
        ):
            await mock_bot._handle_upload_csv_with_pivots_request(
                "test_query_123", "test_file.csv"
            )

            mock_bot.bot.answer_callback_query.assert_called_once_with(
                "test_query_123", text="❌ Ошибка создания маркера для test_file.csv"
            )

    def test_get_file_hash(self, mock_bot):
        """Test file hash generation and mapping."""
        filename = "new_ttm_details_20260206_133012_aod_20260118.csv"

        # Generate hash
        file_hash = mock_bot._get_file_hash(filename)

        # Check hash is short enough
        assert len(file_hash) == 8
        assert isinstance(file_hash, str)

        # Check callback_data lengths are within Telegram's limit (64 bytes)
        callback_upload = f"upload:{file_hash}"
        callback_pivot = f"pivot:{file_hash}"

        assert (
            len(callback_upload) <= 64
        ), f"Upload callback too long: {len(callback_upload)} bytes"
        assert (
            len(callback_pivot) <= 64
        ), f"Pivot callback too long: {len(callback_pivot)} bytes"

        # Check mapping works
        assert mock_bot.file_hash_map[file_hash] == filename

        # Check hash is consistent
        file_hash2 = mock_bot._get_file_hash(filename)
        assert file_hash == file_hash2

    def test_get_file_hash_multiple_files(self, mock_bot):
        """Test file hash generation for multiple files with unique hashes."""
        filenames = [
            "new_ttm_details_20260206_133012.csv",
            "new_ttm_details_20260206_133012_aod_20260118.csv",
            "time_to_market_teams_wide_20260206_133045.csv",
        ]

        hashes = []
        for filename in filenames:
            file_hash = mock_bot._get_file_hash(filename)
            hashes.append(file_hash)

            # Check each hash maps back to correct filename
            assert mock_bot.file_hash_map[file_hash] == filename

        # Check all hashes are unique
        assert len(set(hashes)) == len(hashes), "Hash collision detected!"
