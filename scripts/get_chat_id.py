#!/usr/bin/env python3
"""Script to get Chat ID from Telegram bot."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Load environment variables
load_dotenv()

class ChatIDBot:
    """Simple bot to get chat ID."""
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            print("❌ TELEGRAM_BOT_TOKEN не найден в .env")
            sys.exit(1)
        
        self.application = Application.builder().token(self.bot_token).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup bot command handlers."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("chatid", self.chatid_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        chat = update.effective_chat
        user = update.effective_user
        
        message = f"""🤖 Привет! Я бот для получения Chat ID.

📱 Информация о чате:
• Chat ID: `{chat.id}`
• Тип чата: {chat.type}
• Название: {chat.title or chat.first_name or chat.username or 'Не указано'}

👤 Информация о пользователе:
• User ID: `{user.id}`
• Имя: {user.first_name}
• Username: @{user.username or 'Не указан'}

💡 Используйте Chat ID в переменной TELEGRAM_USER_ID в файле .env
"""
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def chatid_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /chatid command."""
        chat = update.effective_chat
        await update.message.reply_text(
            f"🆔 Chat ID: `{chat.id}`\n"
            f"📝 Тип: {chat.type}",
            parse_mode='Markdown'
        )
    
    async def echo_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Echo all messages with chat info."""
        chat = update.effective_chat
        user = update.effective_user
        
        await update.message.reply_text(
            f"💬 Вы написали: {update.message.text}\n\n"
            f"🆔 Chat ID: `{chat.id}`\n"
            f"👤 User ID: `{user.id}`"
        )
    
    async def run(self):
        """Run the bot."""
        print("🤖 Запуск бота для получения Chat ID...")
        print("📱 Напишите боту @{} в Telegram".format(
            (await self.application.bot.get_me()).username
        ))
        print("💡 Используйте команды /start или /chatid")
        print("🔄 Бот будет отвечать на все сообщения с информацией о чате")
        print("⏹️  Нажмите Ctrl+C для остановки")
        
        try:
            await self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        except KeyboardInterrupt:
            print("\n🛑 Бот остановлен")

async def main():
    """Main function."""
    bot = ChatIDBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
