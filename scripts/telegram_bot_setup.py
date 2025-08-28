#!/usr/bin/env python3
"""Setup script for Telegram bot."""

import os
import sys
from pathlib import Path

def setup_telegram_bot():
    """Setup Telegram bot configuration."""
    print("🤖 Настройка Telegram бота для отчетов")
    print("=" * 50)
    
    # Check if .env exists
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ Файл .env не найден!")
        print("Создайте файл .env на основе env.example")
        return False
    
    # Read current .env
    with open(env_file, 'r', encoding='utf-8') as f:
        env_content = f.read()
    
    # Check if Telegram config already exists
    if "TELEGRAM_BOT_TOKEN" in env_content:
        print("✅ Telegram конфигурация уже настроена в .env")
        return True
    
    print("📝 Настройка переменных окружения для Telegram бота...")
    
    # Get bot token
    bot_token = input("Введите токен вашего бота (от @BotFather): ").strip()
    if not bot_token:
        print("❌ Токен бота обязателен!")
        return False
    
    # Get user ID
    user_id = input("Введите ваш User ID (можно получить от @userinfobot): ").strip()
    if not user_id:
        print("❌ User ID обязателен!")
        return False
    
    try:
        int(user_id)  # Validate it's a number
    except ValueError:
        print("❌ User ID должен быть числом!")
        return False
    
    # Add to .env
    telegram_config = f"""
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN={bot_token}
TELEGRAM_USER_ID={user_id}
"""
    
    with open(env_file, 'a', encoding='utf-8') as f:
        f.write(telegram_config)
    
    print("✅ Telegram конфигурация добавлена в .env")
    print("\n📋 Следующие шаги:")
    print("1. Установите зависимости: pip install -r requirements.txt")
    print("2. Протестируйте бота: make telegram-test")
    print("3. Запустите мониторинг: make telegram-bot")
    
    return True

def main():
    """Main function."""
    try:
        success = setup_telegram_bot()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Настройка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
