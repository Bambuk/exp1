"""Test for restart service command."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from radiator.telegram_bot.bot import ReportsTelegramBot


class TestRestartServiceCommand:
    """Test cases for restart service command."""

    @pytest.fixture
    def bot(self):
        """Create a ReportsTelegramBot instance for testing."""
        with patch("radiator.telegram_bot.bot.TelegramBotConfig") as mock_config:
            mock_config.BOT_TOKEN = "test_token"
            mock_config.USER_ID = 12345
            mock_config.get_reports_dir.return_value = Mock()
            mock_config.MAX_FILE_SIZE = 50 * 1024 * 1024
            mock_config.POLLING_INTERVAL = 30

            bot = ReportsTelegramBot()
            bot.bot = Mock()
            bot.bot.send_message = AsyncMock()
            return bot

    @pytest.mark.asyncio
    async def test_handle_restart_service_command(self, bot):
        """Test handling restart service command."""
        # Mock the send_message method
        bot.send_message = AsyncMock()

        # Mock os.kill to prevent actual process termination
        with patch("os.kill") as mock_kill, patch("os.getpid", return_value=12345):
            # Call the restart service handler
            await bot._handle_restart_service()

            # Check that messages were sent
            assert bot.send_message.call_count == 2

            # Check first message
            first_call = bot.send_message.call_args_list[0]
            assert "Перезапускаю сервис телеграм бота" in first_call[0][0]
            assert "Внимание: Бот будет перезапущен через 3 секунды" in first_call[0][0]

            # Check second message
            second_call = bot.send_message.call_args_list[1]
            assert "Перезапуск сервиса" in second_call[0][0]

            # Check that os.kill was called with SIGTERM
            mock_kill.assert_called_once_with(12345, 15)  # SIGTERM = 15

    @pytest.mark.asyncio
    async def test_restart_service_command_in_handle_command(self, bot):
        """Test that restart service command is handled in handle_command method."""
        # Mock the _handle_restart_service method
        bot._handle_restart_service = AsyncMock()

        # Call handle_command with restart_service command
        await bot.handle_command("restart_service")

        # Check that _handle_restart_service was called
        bot._handle_restart_service.assert_called_once()

    def test_restart_service_in_available_commands(self):
        """Test that restart_service is in available commands."""
        from radiator.telegram_bot.command_executor import CommandExecutor

        executor = CommandExecutor()
        commands = executor.get_available_commands()

        assert "restart_service" in commands
        assert "Перезапустить сервис телеграм бота" in commands["restart_service"]

    def test_restart_service_in_bot_commands(self):
        """Test that restart_service is in bot commands list."""
        with patch("radiator.telegram_bot.bot.TelegramBotConfig") as mock_config:
            mock_config.BOT_TOKEN = "test_token"
            mock_config.USER_ID = 12345
            mock_config.get_reports_dir.return_value = Mock()
            mock_config.MAX_FILE_SIZE = 50 * 1024 * 1024
            mock_config.POLLING_INTERVAL = 30

            bot = ReportsTelegramBot()

            # Check that restart_service command is in the commands list
            # by checking the set_bot_commands method
            import inspect

            source = inspect.getsource(bot.set_bot_commands)
            assert "restart_service" in source
            assert "Перезапустить сервис телеграм бота" in source
