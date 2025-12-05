#!/usr/bin/env python3
"""
Проверка последней синхронизации с Яндекс.Трекером
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import desc, func

from radiator.core.database import SessionLocal
from radiator.models.tracker import TrackerSyncLog, TrackerTask


def format_datetime(dt):
    """Форматирует datetime для вывода."""
    if dt is None:
        return "N/A"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - dt

    # Форматируем дату
    date_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    # Добавляем информацию о том, сколько времени прошло
    if delta.days > 0:
        time_str = f"({delta.days} дн. назад)"
    elif delta.seconds >= 3600:
        hours = delta.seconds // 3600
        time_str = f"({hours} ч. назад)"
    elif delta.seconds >= 60:
        minutes = delta.seconds // 60
        time_str = f"({minutes} мин. назад)"
    else:
        time_str = "(только что)"

    return f"{date_str} {time_str}"


def check_last_sync():
    """Проверяет информацию о последней синхронизации."""
    print("=" * 70)
    print("🔄 Проверка последней синхронизации с Яндекс.Трекером")
    print("=" * 70)

    try:
        db = SessionLocal()

        # 1. Последняя успешная синхронизация
        print("\n📊 Последняя успешная синхронизация:")
        last_completed = (
            db.query(TrackerSyncLog)
            .filter(TrackerSyncLog.status == "completed")
            .order_by(desc(TrackerSyncLog.sync_completed_at))
            .first()
        )

        if last_completed:
            print(f"   ✅ Статус: {last_completed.status}")
            print(f"   📅 Начало: {format_datetime(last_completed.sync_started_at)}")
            print(
                f"   ✅ Завершение: {format_datetime(last_completed.sync_completed_at)}"
            )
            if last_completed.sync_completed_at and last_completed.sync_started_at:
                duration = (
                    last_completed.sync_completed_at - last_completed.sync_started_at
                )
                print(f"   ⏱️  Длительность: {duration.total_seconds():.1f} сек.")
            print(f"   📋 Обработано задач: {last_completed.tasks_processed}")
            print(f"   ➕ Создано: {last_completed.tasks_created}")
            print(f"   🔄 Обновлено: {last_completed.tasks_updated}")
            if last_completed.errors_count > 0:
                print(f"   ⚠️  Ошибок: {last_completed.errors_count}")
        else:
            print("   ❌ Успешных синхронизаций не найдено")

        # 2. Последняя синхронизация (любая)
        print("\n📊 Последняя синхронизация (любая):")
        last_any = (
            db.query(TrackerSyncLog)
            .order_by(desc(TrackerSyncLog.sync_started_at))
            .first()
        )

        if last_any:
            print(f"   📅 Начало: {format_datetime(last_any.sync_started_at)}")
            print(f"   📊 Статус: {last_any.status}")
            if last_any.sync_completed_at:
                print(f"   ✅ Завершение: {format_datetime(last_any.sync_completed_at)}")
            else:
                print(f"   ⏳ Завершение: еще не завершена")
            print(f"   📋 Обработано задач: {last_any.tasks_processed}")
        else:
            print("   ❌ Синхронизаций не найдено")

        # 3. Максимальное значение last_sync_at из задач
        print("\n📊 Последняя синхронизация задач (max last_sync_at):")
        max_sync = db.query(func.max(TrackerTask.last_sync_at)).scalar()

        if max_sync:
            print(f"   📅 Последняя синхронизация задачи: {format_datetime(max_sync)}")

            # Количество задач, синхронизированных в последние 24 часа
            from datetime import timedelta

            day_ago = datetime.now(timezone.utc) - timedelta(days=1)
            recent_tasks = (
                db.query(func.count(TrackerTask.id))
                .filter(TrackerTask.last_sync_at >= day_ago)
                .scalar()
            )
            total_tasks = db.query(func.count(TrackerTask.id)).scalar()
            print(
                f"   📈 Задач синхронизировано за 24 ч.: {recent_tasks} из {total_tasks}"
            )
        else:
            print("   ❌ Нет данных о синхронизации задач")

        # 4. Статистика по синхронизациям
        print("\n📊 Статистика синхронизаций:")
        total_syncs = db.query(func.count(TrackerSyncLog.id)).scalar()
        completed_syncs = (
            db.query(func.count(TrackerSyncLog.id))
            .filter(TrackerSyncLog.status == "completed")
            .scalar()
        )
        failed_syncs = (
            db.query(func.count(TrackerSyncLog.id))
            .filter(TrackerSyncLog.status == "failed")
            .scalar()
        )
        running_syncs = (
            db.query(func.count(TrackerSyncLog.id))
            .filter(TrackerSyncLog.status == "running")
            .scalar()
        )

        print(f"   📊 Всего синхронизаций: {total_syncs}")
        print(f"   ✅ Успешных: {completed_syncs}")
        print(f"   ❌ Неудачных: {failed_syncs}")
        if running_syncs > 0:
            print(f"   ⏳ Выполняющихся: {running_syncs}")

        # 5. Последние 5 синхронизаций
        print("\n📊 Последние 5 синхронизаций:")
        recent_syncs = (
            db.query(TrackerSyncLog)
            .order_by(desc(TrackerSyncLog.sync_started_at))
            .limit(5)
            .all()
        )

        if recent_syncs:
            for i, sync in enumerate(recent_syncs, 1):
                status_icon = {"completed": "✅", "failed": "❌", "running": "⏳"}.get(
                    sync.status, "❓"
                )
                print(
                    f"   {i}. {status_icon} {format_datetime(sync.sync_started_at)} - "
                    f"{sync.status} ({sync.tasks_processed} задач)"
                )
        else:
            print("   ❌ Нет данных")

        db.close()
        print("\n" + "=" * 70)
        return True

    except Exception as e:
        print(f"\n❌ Ошибка при проверке: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = check_last_sync()
    sys.exit(0 if success else 1)
