#!/usr/bin/env python3
"""Simple script to get Chat ID from Telegram bot."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from telegram import Bot

# Load environment variables
load_dotenv()

async def get_chat_id():
    """Get chat ID by sending a message and checking updates."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN не найден в .env")
        return
    
    try:
        bot = Bot(token=bot_token)
        
        # Get bot info
        me = await bot.get_me()
        print(f"🤖 Бот: @{me.username} ({me.first_name})")
        
        print("\n📱 Инструкции:")
        print("1. Найдите бота @{} в Telegram".format(me.username))
        print("2. Отправьте ему любое сообщение (например, 'привет')")
        print("3. Нажмите Enter здесь для проверки обновлений...")
        
        input()
        
        # Get updates
        print("🔄 Получение обновлений...")
        updates = await bot.get_updates()
        
        if not updates:
            print("📭 Обновлений нет.")
            print("💡 Убедитесь, что вы написали боту сообщение")
            return
        
        print(f"📨 Найдено {len(updates)} обновлений:")
        
        for i, update in enumerate(updates[-3:], 1):  # Show last 3 updates
            if update.message:
                chat = update.message.chat
                user = update.message.from_user
                print(f"\n{i}. Сообщение от пользователя:")
                print(f"   👤 User: {user.first_name} (@{user.username or 'без username'})")
                print(f"   🆔 User ID: {user.id}")
                print(f"   💬 Chat ID: {chat.id}")
                print(f"   📝 Тип чата: {chat.type}")
                print(f"   📅 Время: {update.message.date}")
                print(f"   💭 Текст: {update.message.text[:50]}...")
                
                # Suggest the correct ID to use
                if chat.type == "private":
                    print(f"   ✅ Используйте Chat ID: {chat.id}")
                else:
                    print(f"   ✅ Используйте Chat ID: {chat.id}")
        
        print(f"\n💡 Рекомендация:")
        print(f"   Замените TELEGRAM_USER_ID в .env на: {updates[-1].message.chat.id}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def main():
    """Main function."""
    print("🔧 Получение Chat ID от Telegram бота")
    print("=" * 50)
    
    try:
        asyncio.run(get_chat_id())
    except KeyboardInterrupt:
        print("\n🛑 Прервано пользователем")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
