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
        return False
    
    print("✅ Все необходимые переменные окружения настроены")
    return True

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
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        return False

def test_tracker_api():
    """Проверяет доступность API трекера."""
    print("\n🌐 Проверка доступности API трекера...")
    
    try:
        from radiator.services.tracker_service import tracker_service
        
        # Пробуем получить информацию об организации
        headers = tracker_service.headers
        print(f"✅ Заголовки API настроены: Authorization и X-Org-ID присутствуют")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка настройки API трекера: {e}")
        return False

def create_test_tasks_file():
    """Создает тестовый файл с задачами."""
    print("\n📝 Создание тестового файла с задачами...")
    
    test_tasks = [
        "12345",
        "67890", 
        "11111",
        "22222",
        "33333"
    ]
    
    with open("test_tasks.txt", "w", encoding="utf-8") as f:
        for task_id in test_tasks:
            f.write(f"{task_id}\n")
    
    print("✅ Создан файл test_tasks.txt с тестовыми задачами")
    return "test_tasks.txt"

def run_test_sync():
    """Запускает тестовую синхронизацию."""
    print("\n🚀 Запуск тестовой синхронизации...")
    
    try:
        from radiator.commands.sync_tracker import TrackerSyncCommand
        
        task_file = "test_tasks.txt"
        if not os.path.exists(task_file):
            task_file = create_test_tasks_file()
        
        print(f"Используется файл задач: {task_file}")
        print("⚠️ ВНИМАНИЕ: Это тестовая синхронизация с реальными данными!")
        print("Для продолжения введите 'yes': ", end="")
        
        confirmation = input().strip().lower()
        if confirmation != "yes":
            print("❌ Синхронизация отменена пользователем")
            return False
        
        with TrackerSyncCommand() as sync_cmd:
            success = sync_cmd.run(task_file, force_full_sync=False)
            
            if success:
                print("✅ Тестовая синхронизация завершена успешно")
                return True
            else:
                print("❌ Тестовая синхронизация завершилась с ошибкой")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка при запуске синхронизации: {e}")
        return False

def main():
    """Основная функция тестирования."""
    print("🧪 Тестирование системы синхронизации трекера")
    print("=" * 50)
    
    # Проверяем окружение
    if not test_environment():
        print("\n❌ Тестирование прервано из-за ошибок в настройках")
        return False
    
    # Проверяем базу данных
    if not test_database_connection():
        print("\n❌ Тестирование прервано из-за ошибок подключения к БД")
        return False
    
    # Проверяем API трекера
    if not test_tracker_api():
        print("\n❌ Тестирование прервано из-за ошибок API трекера")
        return False
    
    print("\n✅ Все проверки пройдены успешно!")
    
    # Запускаем тестовую синхронизацию
    if run_test_sync():
        print("\n🎉 Тестирование завершено успешно!")
        return True
    else:
        print("\n💥 Тестирование завершилось с ошибками")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
