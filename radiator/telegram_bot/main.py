"""Main entry point for Telegram bot."""

import argparse
import asyncio
import logging
import sys
import threading
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    Updater,
    filters,
)

from radiator.telegram_bot.bot import ReportsTelegramBot
from radiator.telegram_bot.config import TelegramBotConfig
from radiator.telegram_bot.file_monitor import FileMonitor

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class TelegramBotWithCallbacks:
    """Telegram bot with callback query handling."""

    def __init__(self):
        self.bot_instance = ReportsTelegramBot()
        self.application = None

    async def callback_query_handler(self, update, context):
        """Handle callback queries."""
        query = update.callback_query
        logger.info(f"🔔 CALLBACK QUERY RECEIVED: {query.data}")
        logger.info(f"   Query ID: {query.id}")
        logger.info(
            f"   From user: {query.from_user.username if query.from_user else 'Unknown'}"
        )

        await query.answer()
        await self.bot_instance.handle_callback_query(query)

    async def command_handler(self, update, context):
        """Handle command messages."""
        message = update.message
        if not message:
            return

        # Check if user is authorized
        if message.from_user.id != TelegramBotConfig.USER_ID:
            await message.reply_text("❌ У вас нет прав для выполнения команд.")
            return

        command_text = message.text
        logger.info(f"🔔 COMMAND RECEIVED: {command_text}")
        logger.info(f"   From user: {message.from_user.username or 'Unknown'}")

        # Parse command and arguments
        parts = command_text.split()
        if not parts:
            return

        command = parts[0].lstrip("/")
        args = parts[1:] if len(parts) > 1 else []

        # Handle command
        await self.bot_instance.handle_command(command, args)

    def start_monitoring_with_callbacks(self):
        """Start monitoring with callback query support."""
        # Create application
        self.application = (
            Application.builder().token(TelegramBotConfig.BOT_TOKEN).build()
        )

        # Add callback query handler
        self.application.add_handler(CallbackQueryHandler(self.callback_query_handler))
        logger.info("Callback query handler registered")

        # Add command handler for messages starting with /
        self.application.add_handler(
            MessageHandler(filters.Regex(r"^/"), self.command_handler)
        )
        logger.info("Command handler registered")

        # Register bot commands
        async def post_init(application):
            # Create a new bot instance for command registration to avoid event loop issues
            temp_bot = ReportsTelegramBot()
            await temp_bot.set_bot_commands()

        self.application.post_init = post_init

        # Start file monitoring in background
        def start_monitoring():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.bot_instance.start_monitoring())
            finally:
                loop.close()

        monitoring_thread = threading.Thread(target=start_monitoring, daemon=True)
        monitoring_thread.start()

        logger.info("Telegram bot with callback support started")

        try:
            # Run the application with polling
            self.application.run_polling()
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Telegram bot for sending new report files"
    )
    parser.add_argument("--test", action="store_true", help="Test bot connection only")
    parser.add_argument(
        "--reset", action="store_true", help="Reset file monitoring state"
    )
    parser.add_argument(
        "--cleanup", action="store_true", help="Clean up old files from state"
    )
    parser.add_argument(
        "--config", action="store_true", help="Show current configuration"
    )

    args = parser.parse_args()

    # Validate configuration
    if not TelegramBotConfig.validate():
        sys.exit(1)

    # Show configuration if requested
    if args.config:
        TelegramBotConfig.print_config()
        return

    try:
        if args.test:
            # Test connection only
            print("Testing bot connection...")
            bot = ReportsTelegramBot()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(bot.test_connection())
                if success:
                    print("✅ Bot connection test successful!")
                    # Also register commands during test
                    print("Registering bot commands...")
                    cmd_success = loop.run_until_complete(bot.set_bot_commands())
                    if cmd_success:
                        print("✅ Bot commands registered successfully!")
                    else:
                        print("⚠️ Bot commands registration failed!")
                else:
                    print("❌ Bot connection test failed!")
                    sys.exit(1)
            finally:
                loop.close()
            return

        if args.reset:
            # Reset file monitoring state
            print("Resetting file monitoring state...")
            bot = ReportsTelegramBot()
            bot.file_monitor.reset_state()
            print("✅ File monitoring state reset!")
            return

        if args.cleanup:
            # Clean up old files from state
            print("Cleaning up old files from state...")
            bot = ReportsTelegramBot()
            bot.cleanup()
            print("✅ Cleanup completed!")
            return

        # Start monitoring with callbacks
        print("Starting Telegram bot with callback support...")
        bot_with_callbacks = TelegramBotWithCallbacks()
        bot_with_callbacks.start_monitoring_with_callbacks()

    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
