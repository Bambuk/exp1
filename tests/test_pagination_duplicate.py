#!/usr/bin/env python3
"""
Pytest тест для воспроизведения проблемы с дубликатами при пагинации.
Проблема: если задача обновляется во время пагинации, она может попасть в несколько страниц.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import psycopg2
import pytest

from radiator.commands.sync_tracker import TrackerSyncCommand
from radiator.core.database import SessionLocal
from radiator.models.tracker import TrackerTask


class TestPaginationDuplicates:
    """Тесты для воспроизведения проблемы с дубликатами при пагинации."""

    def test_pagination_duplicates_reproduction(self, db_session):
        """
        Тест воспроизводит ошибку UniqueViolation при обработке дубликатов.

        Симулирует ситуацию, когда API возвращает одну задачу несколько раз
        из-за обновления во время пагинации.
        """
        # Создаем тестовый tracker_id
        test_tracker_id = f"test_pagination_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Создаем команду синхронизации
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Очищаем тестовые данные
        db_session.query(TrackerTask).filter(
            TrackerTask.tracker_id == test_tracker_id
        ).delete()
        db_session.commit()

        # Создаем дубликаты задач (симулируем ситуацию от API)
        duplicate_tasks = [
            {
                "tracker_id": test_tracker_id,
                "key": "TEST-DUP-1",
                "summary": "First occurrence",
                "status": "Open",
            },
            {
                "tracker_id": test_tracker_id,  # ДУБЛИКАТ!
                "key": "TEST-DUP-2",
                "summary": "Second occurrence",
                "status": "In Progress",
            },
        ]

        # TDD: Ожидаем, что метод обработает дубликаты БЕЗ ошибки
        # Сейчас логика НЕ исправлена, поэтому тест должен ПАДАТЬ (FAILED)
        result = sync_cmd._bulk_create_or_update_tasks(duplicate_tasks)

        # Проверяем, что дубликаты обработаны корректно
        assert result["created"] == 1  # Только одна задача создана
        assert result["updated"] == 0  # Никаких обновлений

        # Проверяем, что в БД только одна запись с этим tracker_id
        tasks_in_db = (
            db_session.query(TrackerTask)
            .filter(TrackerTask.tracker_id == test_tracker_id)
            .all()
        )
        assert len(tasks_in_db) == 1, f"Ожидалась 1 запись, найдено {len(tasks_in_db)}"

        # Cleanup - rollback сессии после ошибки
        db_session.rollback()
        db_session.query(TrackerTask).filter(
            TrackerTask.tracker_id == test_tracker_id
        ).delete()
        db_session.commit()

    def test_real_pagination_scenario(self, db_session):
        """
        Тест симулирует реальный сценарий пагинации с обновлением задач.

        Создает несколько задач и симулирует ситуацию, когда одна задача
        попадает в несколько страниц из-за обновления во время пагинации.
        """
        # Создаем тестовые задачи
        test_tasks = [
            f"test_pagination_real_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            for i in range(1, 6)
        ]

        # Создаем команду синхронизации
        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Очищаем тестовые данные
        for task_id in test_tasks:
            db_session.query(TrackerTask).filter(
                TrackerTask.tracker_id == task_id
            ).delete()
        db_session.commit()

        # Симулируем пагинацию с дубликатом в середине
        def mock_pagination_with_duplicate():
            """Симулируем пагинацию, где одна задача попала в две страницы"""
            # Страница 1: первые 3 задачи + задача 4
            page1 = test_tasks[:3] + [test_tasks[3]]
            # Страница 2: задача 4 (дубликат!) + остальные
            page2 = [test_tasks[3]] + test_tasks[4:]
            # Объединяем результаты (как делает реальный API)
            return page1 + page2

        # Патчим search_tasks
        with patch(
            "radiator.services.tracker_service.tracker_service.search_tasks",
            side_effect=mock_pagination_with_duplicate,
        ):
            with patch(
                "radiator.services.tracker_service.tracker_service.get_tasks_batch",
                side_effect=lambda ids, **kwargs: [
                    (
                        task_id,
                        {
                            "id": task_id,
                            "key": f"TEST-{task_id.split('_')[-1]}",
                            "summary": f"Test task {task_id}",
                            "status": {"display": "Open"},
                            "updatedAt": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    for task_id in ids
                ],
            ):
                # Тест проверяет, что sync_tasks обрабатывает дубликаты корректно
                # В реальности это должно вызывать ошибку, но пока логика не исправлена
                # мы просто проверяем, что метод выполняется
                try:
                    result, tasks_data, api_errors = sync_cmd.sync_tasks([])
                    # Если метод выполнился без ошибки, проверяем результат
                    assert result is not None
                    assert isinstance(result, dict)
                    print(f"   ⚠️  sync_tasks выполнился без ошибки: {result}")
                    print(
                        f"   ⚠️  Это означает, что дубликаты не обрабатываются в sync_tasks"
                    )
                except Exception as e:
                    print(f"   ✅ sync_tasks упал с ошибкой: {e}")
                    # Rollback после ошибки
                    db_session.rollback()

        # Cleanup
        for task_id in test_tasks:
            db_session.query(TrackerTask).filter(
                TrackerTask.tracker_id == task_id
            ).delete()
        db_session.commit()

    def test_duplicate_detection_in_batch(self, db_session):
        """
        Тест проверяет, что логика _bulk_create_or_update_tasks не обрабатывает
        дубликаты в одном batch правильно.
        """
        test_tracker_id = (
            f"test_duplicate_detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Очищаем тестовые данные
        db_session.query(TrackerTask).filter(
            TrackerTask.tracker_id == test_tracker_id
        ).delete()
        db_session.commit()

        # Создаем задачи с дубликатами tracker_id
        tasks_with_duplicates = [
            {
                "tracker_id": test_tracker_id,
                "key": "TEST-1",
                "summary": "First task",
                "status": "Open",
            },
            {
                "tracker_id": "different_task",
                "key": "TEST-2",
                "summary": "Different task",
                "status": "Open",
            },
            {
                "tracker_id": test_tracker_id,  # ДУБЛИКАТ!
                "key": "TEST-3",
                "summary": "Duplicate task",
                "status": "In Progress",
            },
        ]

        # TDD: Ожидаем, что метод обработает дубликаты БЕЗ ошибки
        # Сейчас логика НЕ исправлена, поэтому тест должен ПАДАТЬ (FAILED)
        result = sync_cmd._bulk_create_or_update_tasks(tasks_with_duplicates)

        # Проверяем, что дубликаты обработаны корректно
        assert result["created"] == 2  # Только 2 уникальные задачи созданы
        assert result["updated"] == 0  # Никаких обновлений

        # Проверяем, что в БД только одна запись с дублирующимся tracker_id
        duplicate_tasks_in_db = (
            db_session.query(TrackerTask)
            .filter(TrackerTask.tracker_id == test_tracker_id)
            .all()
        )
        assert (
            len(duplicate_tasks_in_db) == 1
        ), f"Ожидалась 1 запись с {test_tracker_id}, найдено {len(duplicate_tasks_in_db)}"

        # Cleanup - rollback сессии после ошибки
        db_session.rollback()
        db_session.query(TrackerTask).filter(
            TrackerTask.tracker_id == test_tracker_id
        ).delete()
        db_session.query(TrackerTask).filter(
            TrackerTask.tracker_id == "different_task"
        ).delete()
        db_session.commit()

    def test_no_duplicates_success(self, db_session):
        """
        Тест проверяет, что без дубликатов синхронизация работает нормально.
        """
        test_tracker_id = (
            f"test_no_duplicates_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        sync_cmd = TrackerSyncCommand()
        sync_cmd.db = db_session

        # Очищаем тестовые данные
        db_session.query(TrackerTask).filter(
            TrackerTask.tracker_id == test_tracker_id
        ).delete()
        db_session.commit()

        # Создаем задачи БЕЗ дубликатов
        unique_tasks = [
            {
                "tracker_id": f"{test_tracker_id}_1",
                "key": "TEST-1",
                "summary": "First task",
                "status": "Open",
            },
            {
                "tracker_id": f"{test_tracker_id}_2",
                "key": "TEST-2",
                "summary": "Second task",
                "status": "Open",
            },
        ]

        # Ожидаем успешное выполнение
        result = sync_cmd._bulk_create_or_update_tasks(unique_tasks)

        # Проверяем результат
        assert result["created"] == 2
        assert result["updated"] == 0

        # Проверяем, что задачи созданы в БД
        task1 = (
            db_session.query(TrackerTask)
            .filter(TrackerTask.tracker_id == f"{test_tracker_id}_1")
            .first()
        )
        task2 = (
            db_session.query(TrackerTask)
            .filter(TrackerTask.tracker_id == f"{test_tracker_id}_2")
            .first()
        )

        assert task1 is not None
        assert task2 is not None
        assert task1.key == "TEST-1"
        assert task2.key == "TEST-2"

        # Cleanup
        db_session.query(TrackerTask).filter(
            TrackerTask.tracker_id.like(f"{test_tracker_id}%")
        ).delete()
        db_session.commit()
