#!/usr/bin/env python3
"""
Экспорт существующих задач CPO в файл для синхронизации
"""

import os
import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.core.database import SessionLocal
# CRUD operations removed - using direct SQLAlchemy queries

def export_cpo_tasks():
    """Экспортируем существующие задачи CPO в файл."""
    print("📤 Экспортируем существующие задачи CPO...")
    
    try:
        db = SessionLocal()
        
        # Получаем все задачи CPO
        cpo_tasks = db.query(tracker_task.model).filter(
            tracker_task.model.key.like('CPO-%')
        ).all()
        
        print(f"✅ Найдено задач CPO: {len(cpo_tasks)}")
        
        if not cpo_tasks:
            print("❌ Задачи CPO не найдены")
            return False
        
        # Создаем файл со списком задач
        output_file = "data/output/cpo_tasks_list.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Список задач CPO для синхронизации\n")
            f.write(f"# Всего задач: {len(cpo_tasks)}\n")
            f.write(f"# Дата экспорта: {Path(__file__).stat().st_mtime}\n\n")
            
            for task in cpo_tasks:
                f.write(f"{task.tracker_id}\n")
        
        print(f"✅ Список задач сохранен в файл: {output_file}")
        print(f"📋 Первые 5 задач:")
        
        for i, task in enumerate(cpo_tasks[:5]):
            print(f"  {i+1}. {task.key}: {task.summary[:50] if task.summary else 'N/A'}...")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при экспорте: {e}")
        return False

if __name__ == "__main__":
    success = export_cpo_tasks()
    sys.exit(0 if success else 1)
