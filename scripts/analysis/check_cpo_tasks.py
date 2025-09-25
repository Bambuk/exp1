#!/usr/bin/env python3
"""
Проверка задач CPO в базе данных
"""

import os
import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.core.database import SessionLocal
# CRUD operations removed - using direct SQLAlchemy queries

def check_cpo_tasks():
    """Проверяем задачи CPO в базе данных."""
    print("🔍 Проверяем задачи CPO в базе данных...")
    
    try:
        db = SessionLocal()
        
        # Ищем задачи CPO
        print("📋 Ищем задачи с ключом CPO...")
        cpo_tasks = db.query(tracker_task.model).filter(
            tracker_task.model.key.like('CPO-%')
        ).all()
        
        print(f"✅ Найдено задач CPO: {len(cpo_tasks)}")
        
        if cpo_tasks:
            print("Задачи CPO:")
            for task in cpo_tasks:
                print(f"  - {task.key}: {task.summary[:50] if task.summary else 'N/A'}...")
                print(f"    Статус: {task.status}, Автор: {task.author}")
        else:
            print("❌ Задачи CPO не найдены в базе данных")
            
            # Показываем все доступные ключи задач
            print("\n📋 Все доступные ключи задач:")
            all_tasks = db.query(tracker_task.model.key).limit(20).all()
            keys = [task[0] for task in all_tasks if task[0]]
            for key in sorted(keys):
                print(f"  - {key}")
        
        db.close()
        return len(cpo_tasks) > 0
        
    except Exception as e:
        print(f"❌ Ошибка при проверке задач CPO: {e}")
        return False

if __name__ == "__main__":
    has_cpo = check_cpo_tasks()
    sys.exit(0 if has_cpo else 1)
