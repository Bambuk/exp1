#!/usr/bin/env python3
"""
Проверка содержимого базы данных
"""

import os
import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.core.database import SessionLocal
from radiator.models.tracker import TrackerTask, TrackerTaskHistory, TrackerSyncLog

def check_database():
    """Проверяем содержимое базы данных."""
    print("🔍 Проверяем содержимое базы данных...")
    
    try:
        db = SessionLocal()
        
        # Проверяем задачи
        print("📋 Проверяем таблицу tracker_tasks...")
        tasks = db.query(TrackerTask).limit(5).all()
        print(f"✅ Найдено задач в БД: {len(tasks)}")
        
        if tasks:
            print("Примеры задач:")
            for task in tasks[:3]:
                print(f"  - {task.key}: {task.summary[:50] if task.summary else 'N/A'}...")
        
        # Проверяем историю
        print("\n📊 Проверяем таблицу tracker_task_history...")
        history = db.query(TrackerTaskHistory).limit(5).all()
        print(f"✅ Найдено записей истории: {len(history)}")
        
        if history:
            print("Примеры записей истории:")
            for entry in history[:3]:
                print(f"  - Task ID: {entry.task_id}, Status: {entry.status}, Date: {entry.start_date}")
        
        # Проверяем логи синхронизации
        print("\n🔄 Проверяем логи синхронизации...")
        sync_logs = db.query(TrackerSyncLog).limit(5).all()
        print(f"✅ Найдено логов синхронизации: {len(sync_logs)}")
        
        if sync_logs:
            print("Последние логи:")
            for log in sync_logs[-3:]:
                print(f"  - {log.sync_started_at}: {log.status} - {log.tasks_processed} задач")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке БД: {e}")
        return False

if __name__ == "__main__":
    success = check_database()
    sys.exit(0 if success else 1)
