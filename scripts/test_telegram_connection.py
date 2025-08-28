#!/usr/bin/env python3
"""Test script for Telegram bot connection."""

import asyncio
import os
import sys
from pathlib import Path
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

# Load environment variables
load_dotenv()

@pytest.mark.asyncio
async def test_telegram_connection():
    """Test Telegram bot connection and get chat info."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    user_id = os.getenv("TELEGRAM_USER_ID")
    
    if not bot_token:
        pytest.skip("TELEGRAM_BOT_TOKEN not found in .env")
    
    if not user_id:
        pytest.skip("TELEGRAM_USER_ID not found in .env")
    
    try:
        bot = Bot(token=bot_token)
        
        # Get bot info
        me = await bot.get_me()
        assert me.is_bot is True
        assert me.username is not None
        assert me.first_name is not None
        
        # Try to get chat info
        try:
            chat = await bot.get_chat(chat_id=user_id)
            assert chat.id == int(user_id)
            assert chat.type in ["private", "group", "supergroup", "channel"]
            
        except TelegramError as e:
            if "Chat not found" in str(e):
                # This is expected if user hasn't started chat with bot
                pytest.skip("Chat not found - user needs to start chat with bot")
            else:
                pytest.fail(f"Unexpected Telegram error: {e}")
            
    except Exception as e:
        pytest.fail(f"Connection error: {e}")

@pytest.mark.asyncio
async def test_get_updates():
    """Get recent updates to see available chats."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        pytest.skip("TELEGRAM_BOT_TOKEN not found in .env")
    
    try:
        bot = Bot(token=bot_token)
        updates = await bot.get_updates()
        
        # This is just a test that the function doesn't crash
        # get_updates returns a tuple, not a list
        assert isinstance(updates, (list, tuple))
        
    except Exception as e:
        pytest.fail(f"Failed to get updates: {e}")

@pytest.mark.asyncio
async def test_bot_token_validation():
    """Test bot token validation."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        pytest.skip("TELEGRAM_BOT_TOKEN not found in .env")
    
    # Basic validation that token looks like a Telegram bot token
    assert len(bot_token) > 20
    assert ":" in bot_token
    assert bot_token.split(":")[0].isdigit()

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

if __name__ == "__main__":
    main()
