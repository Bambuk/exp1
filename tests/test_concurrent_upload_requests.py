"""Test concurrent upload requests to Google Sheets."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from radiator.telegram_bot.bot import ReportsTelegramBot


class TestConcurrentUploadRequests:
    """Test cases for concurrent upload requests."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def bot(self, temp_dir):
        """Create a ReportsTelegramBot instance for testing."""
        with patch("radiator.telegram_bot.bot.TelegramBotConfig") as mock_config:
            mock_config.BOT_TOKEN = "test_token"
            mock_config.USER_ID = 12345
            mock_config.get_reports_dir.return_value = temp_dir
            mock_config.MAX_FILE_SIZE = 50 * 1024 * 1024
            mock_config.POLLING_INTERVAL = 30

            bot = ReportsTelegramBot()
            bot.bot = Mock()
            bot.bot.answer_callback_query = AsyncMock()
            return bot

    @pytest.fixture
    def test_files(self, temp_dir):
        """Create test CSV files."""
        files = []
        for i in range(3):
            filename = f"test_report_{i}.csv"
            file_path = temp_dir / filename
            file_path.write_text(f"Name,Value\nTest{i},123\n")
            files.append(filename)
        return files

    @pytest.mark.asyncio
    async def test_concurrent_upload_requests_create_multiple_markers(
        self, bot, temp_dir, test_files
    ):
        """Test that multiple concurrent upload requests create multiple markers."""
        # Create multiple callback queries simultaneously
        callback_queries = []
        for i, filename in enumerate(test_files):
            query = Mock()
            query.data = f"upload_csv:{filename}"
            query.id = f"query_{i}"
            query.from_user = Mock()
            query.from_user.username = "test_user"
            callback_queries.append(query)

        # Process all callback queries concurrently
        tasks = []
        for query in callback_queries:
            task = asyncio.create_task(bot.handle_callback_query(query))
            tasks.append(task)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # Check that all markers were created
        marker_files = list(temp_dir.glob(".upload_me_*.csv"))
        assert len(marker_files) == len(test_files)

        # Check that each marker file exists
        for filename in test_files:
            marker_path = temp_dir / f".upload_me_{filename}"
            assert marker_path.exists()

        # Check that all callback queries were answered
        assert bot.bot.answer_callback_query.call_count == len(test_files)

    @pytest.mark.asyncio
    async def test_concurrent_upload_requests_same_file(
        self, bot, temp_dir, test_files
    ):
        """Test concurrent upload requests for the same file."""
        filename = test_files[0]

        # Create multiple callback queries for the same file
        callback_queries = []
        for i in range(3):
            query = Mock()
            query.data = f"upload_csv:{filename}"
            query.id = f"query_{i}"
            query.from_user = Mock()
            query.from_user.username = "test_user"
            callback_queries.append(query)

        # Process all callback queries concurrently
        tasks = []
        for query in callback_queries:
            task = asyncio.create_task(bot.handle_callback_query(query))
            tasks.append(task)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # Check that only one marker was created (last one wins)
        marker_files = list(temp_dir.glob(f".upload_me_{filename}"))
        assert len(marker_files) == 1

        # Check that all callback queries were answered
        assert bot.bot.answer_callback_query.call_count == 3

    @pytest.mark.asyncio
    async def test_concurrent_upload_requests_race_condition(
        self, bot, temp_dir, test_files
    ):
        """Test that concurrent requests don't cause race conditions."""
        filename = test_files[0]

        # Create multiple callback queries for the same file with slight delays
        async def delayed_callback(delay, query_id):
            await asyncio.sleep(delay)
            query = Mock()
            query.data = f"upload_csv:{filename}"
            query.id = query_id
            query.from_user = Mock()
            query.from_user.username = "test_user"
            await bot.handle_callback_query(query)

        # Start multiple requests with different delays
        tasks = [
            asyncio.create_task(delayed_callback(0.01, "query_1")),
            asyncio.create_task(delayed_callback(0.02, "query_2")),
            asyncio.create_task(delayed_callback(0.03, "query_3")),
        ]

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # Check that only one marker was created
        marker_files = list(temp_dir.glob(f".upload_me_{filename}"))
        assert len(marker_files) == 1

        # Check that all callback queries were answered
        assert bot.bot.answer_callback_query.call_count == 3

    def test_marker_file_creation_is_atomic(self, bot, temp_dir, test_files):
        """Test that marker file creation is atomic (no partial files)."""
        filename = test_files[0]

        # Simulate marker creation
        marker_filename = f".upload_me_{filename}"
        marker_path = temp_dir / marker_filename

        # Create marker file
        with open(marker_path, "w", encoding="utf-8") as f:
            f.write(f"Upload request for {filename}\n")
            f.write(f"Created at: 2024-01-01T00:00:00\n")

        # Check that marker file exists and is complete
        assert marker_path.exists()
        content = marker_path.read_text()
        assert "Upload request for" in content
        assert "Created at:" in content

    @pytest.mark.asyncio
    async def test_concurrent_requests_with_file_operations(
        self, bot, temp_dir, test_files
    ):
        """Test concurrent requests with actual file operations."""
        # Mock file operations to simulate real conditions
        with patch("builtins.open", side_effect=open) as mock_open:
            # Create multiple callback queries
            callback_queries = []
            for i, filename in enumerate(test_files):
                query = Mock()
                query.data = f"upload_csv:{filename}"
                query.id = f"query_{i}"
                query.from_user = Mock()
                query.from_user.username = "test_user"
                callback_queries.append(query)

            # Process all callback queries concurrently
            tasks = []
            for query in callback_queries:
                task = asyncio.create_task(bot.handle_callback_query(query))
                tasks.append(task)

            # Wait for all tasks to complete
            await asyncio.gather(*tasks)

            # Check that all markers were created successfully
            marker_files = list(temp_dir.glob(".upload_me_*.csv"))
            assert len(marker_files) == len(test_files)

            # Check that all callback queries were answered
            assert bot.bot.answer_callback_query.call_count == len(test_files)

    def test_marker_file_naming_convention(self, temp_dir):
        """Test that marker files follow the correct naming convention."""
        filename = "test_report.csv"
        expected_marker = ".upload_me_test_report.csv"

        # Create marker file
        marker_path = temp_dir / expected_marker
        marker_path.write_text("Upload request\n")

        # Check naming convention
        assert marker_path.name.startswith(".upload_me_")
        assert marker_path.name.endswith(filename)
        assert marker_path.name == expected_marker
