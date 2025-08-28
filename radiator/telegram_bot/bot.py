"""Telegram bot for sending new report files."""

import asyncio
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from telegram import Bot
from telegram.error import TelegramError

from .config import TelegramBotConfig
from .file_monitor import FileMonitor

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class ReportsTelegramBot:
    """Telegram bot for sending new report files."""
    
    def __init__(self):
        self.bot = Bot(token=TelegramBotConfig.BOT_TOKEN)
        self.file_monitor = FileMonitor()
        self.user_id = TelegramBotConfig.USER_ID
        
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
            if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                with open(file_path, 'rb') as photo_file:
                    await self.bot.send_photo(
                        chat_id=self.user_id,
                        photo=photo_file,
                        caption=caption
                    )
            elif file_path.suffix.lower() == '.csv':
                with open(file_path, 'rb') as doc_file:
                    await self.bot.send_document(
                        chat_id=self.user_id,
                        document=doc_file,
                        caption=caption
                    )
            else:
                with open(file_path, 'rb') as doc_file:
                    await self.bot.send_document(
                        chat_id=self.user_id,
                        document=doc_file,
                        caption=caption
                    )
            
            logger.info(f"File {file_path.name} sent successfully")
            return True
            
        except TelegramError as e:
            logger.error(f"Failed to send file {file_path.name}: {e}")
            await self.send_message(f"❌ Ошибка отправки файла {file_path.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending file {file_path.name}: {e}")
            await self.send_message(f"❌ Неожиданная ошибка при отправке файла {file_path.name}: {e}")
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
                size_mb = file_info['size'] / (1024 * 1024)
                modified = file_info['modified'].strftime("%d.%m.%Y %H:%M")
                summary += f"• {filename} ({size_mb:.1f}MB, {modified})\n"
        
        await self.send_message(summary)
        
        # Send each file
        for filename in sorted(new_files):
            file_info = self.file_monitor.get_file_info(filename)
            if file_info:
                file_path = file_info['path']
                
                # Create caption
                caption = f"📄 {filename}\n"
                caption += f"📅 Создан: {file_info['modified'].strftime('%d.%m.%Y %H:%M')}\n"
                caption += f"📏 Размер: {file_info['size'] / (1024*1024):.1f}MB"
                
                # Send file
                success = await self.send_file(file_path, caption)
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
                await self.send_message("🤖 Бот запущен и начал мониторинг папки reports")
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
                f"📁 Мониторинг папки: {TelegramBotConfig.REPORTS_DIR}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Bot connection test failed: {e}")
            return False
    
    def cleanup(self):
        """Cleanup resources."""
        self.file_monitor.cleanup_old_files()
