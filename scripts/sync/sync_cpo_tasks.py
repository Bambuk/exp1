#!/usr/bin/env python3
"""
Скрипт для синхронизации задач CPO за последние полгода
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.commands.sync_tracker import TrackerSyncCommand
from radiator.core.logging import logger

def main():
    """Основная функция синхронизации."""
    print("🔄 Начинаем синхронизацию задач CPO за последние полгода...")
    
    # Проверяем переменные окружения
    if not os.getenv('TRACKER_API_TOKEN') or os.getenv('TRACKER_API_TOKEN') == 'your_tracker_api_token_here':
        print("❌ Ошибка: Не настроен TRACKER_API_TOKEN")
        print("Создайте файл .env и заполните TRACKER_API_TOKEN и TRACKER_ORG_ID")
        return False
    
    if not os.getenv('TRACKER_ORG_ID') or os.getenv('TRACKER_ORG_ID') == 'your_organization_id_here':
        print("❌ Ошибка: Не настроен TRACKER_ORG_ID")
        print("Создайте файл .env и заполните TRACKER_API_TOKEN и TRACKER_ORG_ID")
        return False
    
    print("✅ Переменные окружения настроены")
    
    # Рассчитываем дату 6 месяцев назад
    six_months_ago = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    print(f"📅 Ищем задачи, обновленные с: {six_months_ago}")
    
    # Настраиваем фильтры
    filters = {
        "key": "CPO-*",  # Фильтр по ключу задачи
        "updated_since": six_months_ago  # Фильтр по дате обновления
    }
    
    print("🚀 Запускаем синхронизацию...")
    
    try:
        # Запускаем синхронизацию
        with TrackerSyncCommand() as sync_cmd:
            success = sync_cmd.run(
                sync_mode="filter",
                filters=filters,
                days=180,
                limit=1000,
            )
            
            if success:
                print("✅ Синхронизация завершена успешно!")
                return True
            else:
                print("❌ Синхронизация завершилась с ошибкой")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка при выполнении синхронизации: {e}")
        logger.error(f"Sync failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
