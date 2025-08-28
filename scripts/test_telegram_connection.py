#!/usr/bin/env python3
"""Test script for Telegram bot connection."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

# Load environment variables
load_dotenv()

async def test_telegram_connection():
    """Test Telegram bot connection and get chat info."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    user_id = os.getenv("TELEGRAM_USER_ID")
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN не найден в .env")
        return False
    
    if not user_id:
        print("❌ TELEGRAM_USER_ID не найден в .env")
        return False
    
    print(f"🤖 Тестирование подключения к Telegram боту...")
    print(f"📱 User ID: {user_id}")
    
    try:
        bot = Bot(token=bot_token)
        
        # Get bot info
        me = await bot.get_me()
        print(f"✅ Бот подключен: @{me.username} ({me.first_name})")
        
        # Try to get chat info
        try:
            chat = await bot.get_chat(chat_id=user_id)
            print(f"✅ Чат найден: {chat.type} - {chat.title or chat.first_name or chat.username or 'Unknown'}")
            
            # Try to send test message
            print("📤 Отправка тестового сообщения...")
            message = await bot.send_message(
                chat_id=user_id,
                text="🧪 Тестовое сообщение от бота для отчетов!\n\nЕсли вы видите это сообщение, значит бот настроен корректно."
            )
            print(f"✅ Тестовое сообщение отправлено! Message ID: {message.message_id}")
            
            return True
            
        except TelegramError as e:
            print(f"❌ Ошибка с чатом: {e}")
            
            if "Chat not found" in str(e):
                print("\n💡 Возможные решения:")
                print("1. Убедитесь, что вы написали боту @{} в Telegram".format(me.username))
                print("2. Отправьте боту команду /start")
                print("3. Проверьте, что User ID указан правильно")
                print("4. Попробуйте использовать Chat ID вместо User ID")
            
            return False
            
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

async def get_updates():
    """Get recent updates to see available chats."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN не найден в .env")
        return
    
    try:
        bot = Bot(token=bot_token)
        updates = await bot.get_updates()
        
        if not updates:
            print("📭 Обновлений нет. Попробуйте написать боту сообщение.")
            return
        
        print(f"📨 Найдено {len(updates)} обновлений:")
        for i, update in enumerate(updates[-5:], 1):  # Show last 5 updates
            if update.message:
                chat = update.message.chat
                print(f"{i}. Chat ID: {chat.id}, Type: {chat.type}, Title: {chat.title or chat.first_name or chat.username or 'Unknown'}")
            elif update.my_chat_member:
                chat = update.my_chat_member.chat
                print(f"{i}. Chat ID: {chat.id}, Type: {chat.type}, Title: {chat.title or chat.first_name or chat.username or 'Unknown'}")
    
    except Exception as e:
        print(f"❌ Ошибка получения обновлений: {e}")

def main():
    """Main function."""
    print("🔧 Тестирование Telegram бота для отчетов")
    print("=" * 50)
    
    # Test connection
    success = asyncio.run(test_telegram_connection())
    
    if not success:
        print("\n🔄 Попытка получить информацию об обновлениях...")
        asyncio.run(get_updates())
    
    print("\n📋 Инструкции:")
    print("1. Напишите боту в Telegram (команда /start)")
    print("2. Проверьте User ID в .env")
    print("3. Запустите тест снова: python scripts/test_telegram_connection.py")

if __name__ == "__main__":
    main()
