"""Telegram bot for sending new report files."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from .command_executor import CommandExecutor
from .config import TelegramBotConfig
from .file_monitor import FileMonitor

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class ReportsTelegramBot:
    """Telegram bot for sending new report files."""

    def __init__(self):
        self.bot = Bot(token=TelegramBotConfig.BOT_TOKEN)
        self.file_monitor = FileMonitor()
        self.user_id = TelegramBotConfig.USER_ID
        self.reports_dir = TelegramBotConfig.get_reports_dir()
        self.command_executor = CommandExecutor()

    async def send_file(self, file_path: Path, caption: str = None) -> bool:
        """
        Send file to Telegram user.

        Args:
            file_path: Path to file to send
            caption: Optional caption for the file

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > TelegramBotConfig.MAX_FILE_SIZE:
                await self.send_message(
                    f"⚠️ Файл {file_path.name} слишком большой ({file_size / (1024*1024):.1f}MB). "
                    f"Максимальный размер: {TelegramBotConfig.MAX_FILE_SIZE / (1024*1024):.1f}MB"
                )
                return False

            # Send file based on type
            if file_path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                with open(file_path, "rb") as photo_file:
                    await self.bot.send_photo(
                        chat_id=self.user_id, photo=photo_file, caption=caption
                    )
            elif file_path.suffix.lower() == ".csv":
                with open(file_path, "rb") as doc_file:
                    await self.bot.send_document(
                        chat_id=self.user_id, document=doc_file, caption=caption
                    )
            else:
                with open(file_path, "rb") as doc_file:
                    await self.bot.send_document(
                        chat_id=self.user_id, document=doc_file, caption=caption
                    )

            logger.info(f"File {file_path.name} sent successfully")
            return True

        except TelegramError as e:
            logger.error(f"Failed to send file {file_path.name}: {e}")
            await self.send_message(f"❌ Ошибка отправки файла {file_path.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending file {file_path.name}: {e}")
            await self.send_message(
                f"❌ Неожиданная ошибка при отправке файла {file_path.name}: {e}"
            )
            return False

    async def send_file_with_upload_button(
        self, file_path: Path, caption: str = None
    ) -> bool:
        """
        Send file to Telegram user with upload button for CSV files.

        Args:
            file_path: Path to file to send
            caption: Optional caption for the file

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > TelegramBotConfig.MAX_FILE_SIZE:
                await self.send_message(
                    f"⚠️ Файл {file_path.name} слишком большой ({file_size / (1024*1024):.1f}MB). "
                    f"Максимальный размер: {TelegramBotConfig.MAX_FILE_SIZE / (1024*1024):.1f}MB"
                )
                return False

            # Create keyboard for CSV files
            keyboard = None
            if file_path.suffix.lower() == ".csv":
                keyboard = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "📊 Загрузить в Google Sheets",
                                callback_data=f"upload_csv:{file_path.name}",
                            )
                        ]
                    ]
                )

            # Send file based on type
            if file_path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                with open(file_path, "rb") as photo_file:
                    await self.bot.send_photo(
                        chat_id=self.user_id,
                        photo=photo_file,
                        caption=caption,
                        reply_markup=keyboard,
                    )
            elif file_path.suffix.lower() == ".csv":
                with open(file_path, "rb") as doc_file:
                    await self.bot.send_document(
                        chat_id=self.user_id,
                        document=doc_file,
                        caption=caption,
                        reply_markup=keyboard,
                    )
            else:
                with open(file_path, "rb") as doc_file:
                    await self.bot.send_document(
                        chat_id=self.user_id,
                        document=doc_file,
                        caption=caption,
                        reply_markup=keyboard,
                    )

            logger.info(f"File {file_path.name} sent successfully with upload button")
            return True

        except TelegramError as e:
            logger.error(f"Failed to send file {file_path.name}: {e}")
            await self.send_message(f"❌ Ошибка отправки файла {file_path.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending file {file_path.name}: {e}")
            await self.send_message(
                f"❌ Неожиданная ошибка при отправке файла {file_path.name}: {e}"
            )
            return False

    async def send_message(self, text: str) -> bool:
        """
        Send text message to Telegram user.

        Args:
            text: Message text to send

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            await self.bot.send_message(chat_id=self.user_id, text=text)
            return True
        except TelegramError as e:
            logger.error(f"Failed to send message: {e}")
            return False

    async def handle_callback_query(self, callback_query) -> None:
        """
        Handle callback query from inline keyboard buttons.

        Args:
            callback_query: Callback query from Telegram
        """
        try:
            query_data = callback_query.data
            query_id = callback_query.id

            logger.info(f"Received callback query: {query_data} (ID: {query_id})")

            if query_data.startswith("upload_csv:"):
                filename = query_data.split(":", 1)[1]
                logger.info(f"Processing upload request for file: {filename}")
                await self._handle_upload_csv_request(query_id, filename)
            else:
                # Answer unknown callback
                logger.warning(f"Unknown callback query: {query_data}")
                await self.bot.answer_callback_query(
                    query_id, text="❌ Неизвестная команда"
                )

        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            try:
                await self.bot.answer_callback_query(
                    callback_query.id, text="❌ Ошибка обработки запроса"
                )
            except:
                pass

    async def _handle_upload_csv_request(self, query_id: str, filename: str) -> None:
        """
        Handle CSV upload request from button press.

        Args:
            query_id: Callback query ID
            filename: Name of the CSV file
        """
        try:
            # Check if file exists
            file_path = self.reports_dir / filename
            if not file_path.exists():
                await self.bot.answer_callback_query(
                    query_id, text=f"❌ Файл {filename} не найден"
                )
                return

            # Create marker file
            marker_filename = f".upload_me_{filename}"
            marker_path = self.reports_dir / marker_filename

            try:
                with open(marker_path, "w", encoding="utf-8") as f:
                    f.write(f"Upload request for {filename}\n")
                    f.write(f"Created at: {datetime.now().isoformat()}\n")

                await self.bot.answer_callback_query(
                    query_id,
                    text=f"✅ Файл {filename} добавлен в очередь загрузки в Google Sheets",
                )
                logger.info(f"Upload marker created for {filename}")

            except Exception as e:
                logger.error(f"Failed to create marker file for {filename}: {e}")
                await self.bot.answer_callback_query(
                    query_id, text=f"❌ Ошибка создания маркера для {filename}"
                )

        except Exception as e:
            logger.error(f"Error handling upload request for {filename}: {e}")
            await self.bot.answer_callback_query(
                query_id, text=f"❌ Ошибка обработки запроса для {filename}"
            )

    async def send_new_files_notification(self, new_files: List[str]) -> None:
        """
        Send notification about new files.

        Args:
            new_files: List of new filenames
        """
        if not new_files:
            return

        # Send summary message
        summary = f"📊 Новые отчеты ({len(new_files)} файлов):\n\n"
        for filename in sorted(new_files):
            file_info = self.file_monitor.get_file_info(filename)
            if file_info:
                size_mb = file_info["size"] / (1024 * 1024)
                modified = file_info["modified"].strftime("%d.%m.%Y %H:%M")
                summary += f"• {filename} ({size_mb:.1f}MB, {modified})\n"

        await self.send_message(summary)

        # Send each file
        for filename in sorted(new_files):
            file_info = self.file_monitor.get_file_info(filename)
            if file_info:
                file_path = file_info["path"]

                # Create caption
                caption = f"📄 {filename}\n"
                caption += (
                    f"📅 Создан: {file_info['modified'].strftime('%d.%m.%Y %H:%M')}\n"
                )
                caption += f"📏 Размер: {file_info['size'] / (1024*1024):.1f}MB"

                # Send file with upload button for CSV files
                success = await self.send_file_with_upload_button(file_path, caption)
                if success:
                    await asyncio.sleep(1)  # Small delay between files

    async def check_and_send_new_files(self) -> None:
        """Check for new files and send them."""
        try:
            new_files = self.file_monitor.get_new_files()
            if new_files:
                logger.info(f"Found {len(new_files)} new files: {', '.join(new_files)}")
                await self.send_new_files_notification(list(new_files))
            else:
                logger.debug("No new files found")

        except Exception as e:
            logger.error(f"Error checking for new files: {e}")
            await self.send_message(f"❌ Ошибка проверки новых файлов: {e}")

    async def start_monitoring(self) -> None:
        """Start continuous monitoring of reports directory."""
        logger.info("Starting Telegram bot monitoring...")

        try:
            # Send startup message only if successful
            try:
                await self.send_message(
                    "🤖 Бот запущен и начал мониторинг папки reports"
                )
            except Exception as e:
                logger.warning(f"Could not send startup message: {e}")

            while True:
                await self.check_and_send_new_files()
                await asyncio.sleep(TelegramBotConfig.POLLING_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
            try:
                await self.send_message("🛑 Мониторинг остановлен")
            except Exception as e:
                logger.warning(f"Could not send stop message: {e}")
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            try:
                await self.send_message(f"❌ Ошибка мониторинга: {e}")
            except Exception as send_error:
                logger.warning(f"Could not send error message: {send_error}")

    async def test_connection(self) -> bool:
        """Test bot connection and send test message."""
        try:
            me = await self.bot.get_me()
            logger.info(f"Bot connected: @{me.username}")

            await self.send_message(
                f"✅ Бот успешно подключен!\n"
                f"🤖 Имя: {me.first_name}\n"
                f"👤 Username: @{me.username}\n"
                f"📁 Мониторинг папки: {TelegramBotConfig.get_reports_dir()}"
            )
            return True

        except Exception as e:
            logger.error(f"Bot connection test failed: {e}")
            return False

    async def set_bot_commands(self) -> bool:
        """Set bot commands in Telegram."""
        try:
            from telegram import BotCommand

            commands = [
                BotCommand("help", "Показать доступные команды"),
                BotCommand(
                    "generate_time_to_market_teams",
                    "Сгенерировать отчет Time to Market по командам",
                ),
                BotCommand(
                    "sync_and_report", "Синхронизировать трекер и сгенерировать отчет"
                ),
                BotCommand("sync_tracker", "Синхронизировать трекер с фильтром"),
                BotCommand("restart_service", "Перезапустить сервис телеграм бота"),
            ]

            await self.bot.set_my_commands(commands)
            logger.info("Bot commands registered successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to set bot commands: {e}")
            return False

    async def handle_command(self, command: str, args: List[str] = None) -> None:
        """
        Handle command from user.

        Args:
            command: Command name
            args: Command arguments
        """
        try:
            logger.info(f"Handling command: {command} with args: {args}")

            if command == "help":
                await self._handle_help_command()
            elif command == "generate_time_to_market_teams":
                # Parse format argument (default to "wide")
                csv_format = "wide"
                if args and args[0].lower() in ["long", "wide"]:
                    csv_format = args[0].lower()
                await self._handle_generate_time_to_market_teams(csv_format)
            elif command == "sync_and_report":
                await self._handle_sync_and_report()
            elif command == "sync_tracker":
                if not args:
                    await self.send_message(
                        "❌ Для команды /sync_tracker необходимо указать фильтр!\n\n"
                        "📝 Примеры использования:\n"
                        "• /sync_tracker Queue: CPO Status: In Progress\n"
                        "• /sync_tracker key:CPO-*\n"
                        "• /sync_tracker Queue: CPO Updated: >=01.01.2025\n\n"
                        "💡 Фильтр определяет, какие задачи синхронизировать из трекера."
                    )
                    return
                filter_str = " ".join(args)
                await self._handle_sync_tracker(filter_str)
            elif command == "restart_service":
                await self._handle_restart_service()
            else:
                await self.send_message(
                    f"❌ Неизвестная команда: {command}\n\n{self.command_executor.format_command_help()}"
                )

        except Exception as e:
            logger.error(f"Error handling command {command}: {e}")
            await self.send_message(f"❌ Ошибка выполнения команды {command}: {e}")

    async def _handle_help_command(self) -> None:
        """Handle help command."""
        help_text = self.command_executor.format_command_help()
        await self.send_message(help_text)

    async def _handle_generate_time_to_market_teams(
        self, csv_format: str = "wide"
    ) -> None:
        """
        Handle generate time to market report by teams command.

        Args:
            csv_format: CSV format - "wide" or "long"
        """
        format_text = "длинном" if csv_format == "long" else "широком"
        await self.send_message(
            f"🔄 Запускаю генерацию отчета Time to Market по командам ({format_text} формат)..."
        )

        (
            success,
            stdout,
            stderr,
        ) = await self.command_executor.generate_time_to_market_report_teams(csv_format)

        if success:
            await self.send_message(
                f"✅ Отчет Time to Market по командам ({format_text} формат) успешно сгенерирован!"
            )

            # Send detailed output
            if stdout.strip() or stderr.strip():
                await self._send_command_output(
                    stdout, stderr, "📋 Вывод команды генерации отчета:"
                )
        else:
            error_msg = f"❌ Ошибка генерации отчета:\n```\n{stderr or stdout}\n```"
            await self.send_message(error_msg)

    async def _handle_sync_and_report(self) -> None:
        """Handle sync and report command."""
        await self.send_message(
            "🔄 Запускаю полный процесс: синхронизация трекера + генерация отчета..."
        )

        success, stdout, stderr = await self.command_executor.sync_and_report()

        if success:
            await self.send_message("✅ Полный процесс завершен успешно!")

            # Send detailed output
            if stdout.strip() or stderr.strip():
                await self._send_command_output(
                    stdout, stderr, "📋 Вывод команды полного процесса:"
                )
        else:
            error_msg = f"❌ Ошибка выполнения процесса:\n```\n{stderr or stdout}\n```"
            await self.send_message(error_msg)

    async def _handle_sync_tracker(self, filter_str: str) -> None:
        """Handle sync tracker command."""
        await self.send_message(
            f"🔄 Запускаю синхронизацию трекера с фильтром: {filter_str}"
        )

        success, stdout, stderr = await self.command_executor.sync_tracker(filter_str)

        if success:
            await self.send_message("✅ Синхронизация трекера завершена успешно!")

            # Send detailed output
            if stdout.strip() or stderr.strip():
                await self._send_command_output(
                    stdout, stderr, "📋 Вывод команды синхронизации:"
                )
        else:
            error_msg = f"❌ Ошибка синхронизации трекера:\n```\n{stderr or stdout}\n```"
            await self.send_message(error_msg)

    async def _send_command_output(self, stdout: str, stderr: str, title: str) -> None:
        """
        Send command output to user with proper formatting.

        Args:
            stdout: Standard output from command
            stderr: Standard error from command
            title: Title for the output message
        """
        try:
            # Combine stdout and stderr
            full_output = ""
            if stdout.strip():
                full_output += stdout.strip()
            if stderr.strip():
                if full_output:
                    full_output += "\n" + stderr.strip()
                else:
                    full_output = stderr.strip()

            if not full_output.strip():
                return

            # Filter out common warnings and noise
            filtered_output = self._filter_command_output(full_output)

            if not filtered_output.strip():
                return

            # Split output into chunks if too long
            max_length = (
                3000  # Telegram message limit is ~4000 chars, leave some margin
            )
            if len(filtered_output) <= max_length:
                await self.send_message(f"{title}\n```\n{filtered_output}\n```")
            else:
                # Send in chunks
                lines = filtered_output.split("\n")
                current_chunk = ""

                for line in lines:
                    if len(current_chunk + line + "\n") > max_length:
                        if current_chunk:
                            await self.send_message(
                                f"{title} (часть 1):\n```\n{current_chunk}\n```"
                            )
                            current_chunk = line + "\n"
                        else:
                            # Single line is too long, truncate it
                            await self.send_message(
                                f"{title} (часть 1):\n```\n{line[:max_length-100]}...\n```"
                            )
                    else:
                        current_chunk += line + "\n"

                # Send remaining chunk
                if current_chunk.strip():
                    await self.send_message(
                        f"{title} (часть 2):\n```\n{current_chunk}\n```"
                    )

        except Exception as e:
            logger.error(f"Error sending command output: {e}")
            await self.send_message(f"❌ Ошибка отправки вывода команды: {e}")

    def _filter_command_output(self, output: str) -> str:
        """
        Filter command output to remove noise and keep useful information.

        Args:
            output: Raw command output

        Returns:
            Filtered output
        """
        lines = output.split("\n")
        filtered_lines = []

        for line in lines:
            # Skip common noise
            if any(
                noise in line
                for noise in [
                    "Makefile:93: предупреждение: переопределение способа",
                    "Makefile:74: предупреждение: старый способ",
                    "RuntimeWarning: 'radiator.commands.sync_tracker' found in sys.modules",
                    "make: *** [Makefile:122: sync-tracker] Ошибка 1",
                    "make: *** [Makefile:",
                    "предупреждение:",
                    "warning:",
                    "RuntimeWarning:",
                    "frozen runpy:",
                ]
            ):
                continue

            # Skip progress bars and intermediate output
            if any(
                progress in line
                for progress in [
                    "Общий прогресс:",
                    "Загрузка истории:",
                    "Обработка истории:",
                    "Progress:",
                    "Loading:",
                    "Processing:",
                    "|",  # Progress bar characters
                    "[A",  # ANSI escape sequences
                    "задача/s",
                    "этап/s",
                    "task=",
                ]
            ):
                continue

            # Keep only final results and important messages
            if any(
                useful in line
                for useful in [
                    "🎉",
                    "✅",
                    "❌",
                    "📝",
                    "🔄",
                    "📋",
                    "📚",
                    "Синхронизация завершена",
                    "Создано:",
                    "Обновлено:",
                    "Записей истории:",
                    "Задач с историей:",
                    "Generating",
                    "Report",
                    "Success",
                    "Error",
                    "Warning",
                    "Completed",
                    "отчет",
                    "report",
                    "успешно",
                    "successfully",
                    "завершена",
                    "completed",
                ]
            ):
                filtered_lines.append(line)
            elif (
                line.strip()
                and not line.startswith(" ")
                and not any(char in line for char in ["|", "[", "]", "%"])
            ):
                # Keep non-empty lines that don't start with spaces and don't contain progress indicators
                filtered_lines.append(line)

        return "\n".join(filtered_lines)

    async def _handle_restart_service(self) -> None:
        """Handle restart service command."""
        await self.send_message(
            "🔄 Перезапускаю сервис телеграм бота...\n\n"
            "⚠️ Внимание: Бот будет перезапущен через 3 секунды!"
        )

        # Wait a bit to ensure message is sent
        await asyncio.sleep(3)

        # Send final message before restart
        await self.send_message("🔄 Перезапуск сервиса...")

        # Log the restart
        logger.info("Service restart requested via Telegram command")

        # Exit the process to trigger restart by systemd or supervisor
        import os
        import signal

        os.kill(os.getpid(), signal.SIGTERM)

    def cleanup(self):
        """Cleanup resources."""
        self.file_monitor.cleanup_old_files()
