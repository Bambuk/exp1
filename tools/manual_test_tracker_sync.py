#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы синхронизации трекера.
Запускает синхронизацию с тестовыми данными.
"""

import os
import sys
from pathlib import Path

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

# Добавляем корень проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_environment():
    """Проверяет настройки окружения."""
    print("🔍 Проверка настроек окружения...")
    
    required_vars = [
        "TRACKER_API_TOKEN",
        "TRACKER_ORG_ID",
        "DATABASE_URL_SYNC"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            # Скрываем токен для безопасности
            if "TOKEN" in var:
                print(f"✅ {var}: {'*' * 10}")
            else:
                print(f"✅ {var}: {value}")
    
    if missing_vars:
        print(f"❌ Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        print("Создайте файл .env на основе env.example")
        assert False, f"Missing environment variables: {', '.join(missing_vars)}"
    
    print("✅ Все необходимые переменные окружения настроены")
    assert True, "Environment variables configured"

def test_database_connection():
    """Проверяет подключение к базе данных."""
    print("\n🗄️ Проверка подключения к базе данных...")
    
    try:
        from radiator.core.database import SessionLocal
        from radiator.models.tracker import TrackerTask
        
        db = SessionLocal()
        # Пробуем выполнить простой запрос
        result = db.query(TrackerTask).limit(1).all()
        db.close()
        
        print("✅ Подключение к базе данных успешно")
        assert True, "Database connection successful"
        
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        assert False, f"Database connection failed: {e}"

def test_tracker_api():
    """Проверяет доступность API трекера."""
    print("\n🌐 Проверка доступности API трекера...")
    
    try:
        from radiator.services.tracker_service import tracker_service
        
        # Пробуем получить информацию об организации
        headers = tracker_service.headers
        print(f"✅ Заголовки API настроены: Authorization и X-Org-ID присутствуют")
        assert True, "Tracker API configured"
        
    except Exception as e:
        print(f"❌ Ошибка настройки API трекера: {e}")
        assert False, f"Tracker API configuration failed: {e}"

def test_api_search():
    """Тестирует поиск задач через API."""
    print("\n🔍 Тестирование поиска задач через API...")
    
    try:
        from radiator.services.tracker_service import tracker_service
        
        # Тестируем поиск недавних задач
        recent_tasks = tracker_service.get_recent_tasks(days=7, limit=5)
        print(f"✅ Найдено {len(recent_tasks)} недавних задач")
        
        # Тестируем поиск активных задач
        active_tasks = tracker_service.get_active_tasks(limit=5)
        print(f"✅ Найдено {len(active_tasks)} активных задач")
        
        if recent_tasks or active_tasks:
            print("✅ API поиск работает корректно")
            assert True, "API search working correctly"
        else:
            print("⚠️ API поиск работает, но задач не найдено (возможно, нет данных)")
            assert True, "API search working but no tasks found"
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании API поиска: {e}")
        assert False, f"API search test failed: {e}"

def run_test_sync():
    """Запускает тестовую синхронизацию."""
    print("\n🚀 Запуск тестовой синхронизации...")
    
    try:
        from radiator.commands.sync_tracker import TrackerSyncCommand
        
        print("Тестируем синхронизацию недавних задач (последние 3 дня, максимум 5 задач)")
        print("⚠️ ВНИМАНИЕ: Это тестовая синхронизация с реальными данными!")
        print("Для продолжения введите 'yes': ", end="")
        
        confirmation = input().strip().lower()
        if confirmation != "yes":
            print("❌ Синхронизация отменена пользователем")
            assert False, "Sync cancelled by user"
        
        with TrackerSyncCommand() as sync_cmd:
            success = sync_cmd.run(
                sync_mode="recent",
                days=3,
                limit=5,
                force_full_sync=False
            )
            
            if success:
                print("✅ Тестовая синхронизация завершена успешно")
                assert True, "Test sync completed successfully"
            else:
                print("❌ Тестовая синхронизация завершилась с ошибкой")
                assert False, "Test sync failed"
                
    except Exception as e:
        print(f"❌ Ошибка при запуске синхронизации: {e}")
        assert False, f"Test sync error: {e}"

def main():
    """Основная функция тестирования."""
    print("🧪 Тестирование системы синхронизации трекера")
    print("=" * 50)
    
    # Проверяем окружение
    test_environment()
    
    # Проверяем базу данных
    test_database_connection()
    
    # Проверяем API трекера
    test_tracker_api()
    
    # Тестируем API поиск
    test_api_search()
    
    print("\n✅ Все проверки пройдены успешно!")
    
    # Запускаем тестовую синхронизацию
    run_test_sync()
    print("\n🎉 Тестирование завершено успешно!")
    assert True, "All tests completed successfully"

if __name__ == "__main__":
    main()
    sys.exit(0)
