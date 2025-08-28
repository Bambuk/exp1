#!/usr/bin/env python3
"""
Тест Tracker API с загрузкой переменных из .env
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.services.tracker_service import tracker_service

def test_api_access():
    """Тестируем доступ к Tracker API."""
    print("🔍 Тестируем доступ к Tracker API...")
    
    # Проверяем переменные окружения
    token = os.getenv('TRACKER_API_TOKEN')
    org_id = os.getenv('TRACKER_ORG_ID')
    
    print(f"Token: {token[:20]}..." if token else "Token: не найден")
    print(f"Org ID: {org_id}")
    
    if not token or not org_id:
        print("❌ Переменные окружения не настроены")
        return False
    
    try:
        # Пробуем простой поиск без фильтров
        print("📡 Пробуем простой поиск задач...")
        tasks = tracker_service.search_tasks("", limit=5)
        print(f"✅ Найдено задач: {len(tasks)}")
        
        if tasks:
            print(f"Примеры ID задач: {tasks[:3]}")
            
            # Пробуем получить детали первой задачи
            if tasks:
                print(f"📋 Получаем детали задачи {tasks[0]}...")
                task_data = tracker_service.get_task(tasks[0])
                if task_data:
                    print(f"✅ Задача получена: {task_data.get('key', 'N/A')} - {task_data.get('summary', 'N/A')[:50]}...")
                else:
                    print("❌ Не удалось получить детали задачи")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обращении к API: {e}")
        return False

if __name__ == "__main__":
    success = test_api_access()
    sys.exit(0 if success else 1)
