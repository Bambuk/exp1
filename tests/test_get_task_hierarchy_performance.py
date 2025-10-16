"""Performance tests for get_task_hierarchy method."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from radiator.commands.services.testing_returns_service import TestingReturnsService
from radiator.models.tracker import TrackerTask


class QueryCounter:
    """Utility to count database queries."""

    def __init__(self, db_session):
        self.db_session = db_session
        self.query_count = 0
        self.original_execute = None

    def __enter__(self):
        """Start counting queries."""
        self.query_count = 0
        self.original_execute = self.db_session.execute

        def counting_execute(*args, **kwargs):
            self.query_count += 1
            return self.original_execute(*args, **kwargs)

        self.db_session.execute = counting_execute
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop counting queries."""
        if self.original_execute:
            self.db_session.execute = self.original_execute


class TestGetTaskHierarchyPerformance:
    """Performance tests for get_task_hierarchy."""

    def test_get_task_hierarchy_does_not_load_all_tasks(self, db_session):
        """
        Проверка производительности: не должно быть > 50 запросов для иерархии из 10 задач.

        Создаем:
        - 1 родительская задача
        - 5 subtasks первого уровня
        - 5 subtasks второго уровня (вложенные в одну из subtasks первого уровня)

        Ожидаемое количество запросов:
        - 1 запрос для получения subtasks первого уровня
        - 5 запросов для получения subtasks второго уровня (по одному на каждую задачу первого уровня)
        - Итого: ~6 запросов (не 62,111!)
        """
        # Создать родительскую задачу
        parent_task = TrackerTask(
            tracker_id="fs-parent",
            key="FULLSTACK-1000",
            summary="Parent Task",
            status="In Progress",
            author="test_dev",
            links=[],
        )
        db_session.add(parent_task)
        db_session.flush()

        # Создать 5 subtasks первого уровня
        first_level_tasks = []
        for i in range(1, 6):
            subtask = TrackerTask(
                tracker_id=f"fs-subtask-l1-{i}",
                key=f"FULLSTACK-100{i}",
                summary=f"Subtask L1 {i}",
                status="In Progress",
                author="test_dev",
                links=[
                    {
                        "type": {"id": "subtask"},
                        "direction": "inward",
                        "object": {"key": "FULLSTACK-1000"},
                    }
                ],
            )
            db_session.add(subtask)
            first_level_tasks.append(subtask)

        db_session.flush()

        # Создать 5 subtasks второго уровня (вложенные в первую задачу первого уровня)
        for i in range(1, 6):
            subtask = TrackerTask(
                tracker_id=f"fs-subtask-l2-{i}",
                key=f"FULLSTACK-200{i}",
                summary=f"Subtask L2 {i}",
                status="In Progress",
                author="test_dev",
                links=[
                    {
                        "type": {"id": "subtask"},
                        "direction": "inward",
                        "object": {"key": "FULLSTACK-1001"},
                    }
                ],
            )
            db_session.add(subtask)

        db_session.commit()

        # Подсчитать количество запросов
        testing_returns_service = TestingReturnsService(db_session)

        with QueryCounter(db_session) as counter:
            hierarchy = testing_returns_service.get_task_hierarchy("FULLSTACK-1000")

        # Проверить результат
        assert (
            "FULLSTACK-1000" in hierarchy
        ), "Родительская задача должна быть в иерархии"
        assert (
            len(hierarchy) == 11
        ), f"Иерархия должна содержать 11 задач (1+5+5), получено {len(hierarchy)}"

        # Проверить производительность
        assert counter.query_count < 50, (
            f"Слишком много запросов к БД: {counter.query_count}. "
            f"Ожидается < 50 для 11 задач."
        )

    def test_get_task_hierarchy_with_large_dataset(self, db_session):
        """
        Проверка производительности на большом датасете.

        Создаем 100 FULLSTACK задач, из которых только 10 связаны с родительской задачей.
        Проверяем, что НЕ загружаются все 100 задач (что было в старой версии).
        """
        # Создать родительскую задачу
        parent_task = TrackerTask(
            tracker_id="fs-parent-large",
            key="FULLSTACK-9000",
            summary="Parent Task for Large Dataset",
            status="In Progress",
            author="test_dev",
            links=[],
        )
        db_session.add(parent_task)
        db_session.flush()

        # Создать 100 FULLSTACK задач
        for i in range(1, 101):
            # Только первые 10 будут связаны с родительской задачей
            is_subtask = i <= 10

            subtask = TrackerTask(
                tracker_id=f"fs-large-{i}",
                key=f"FULLSTACK-900{i}",
                summary=f"Task {i}",
                status="In Progress",
                author="test_dev",
                links=[
                    {
                        "type": {"id": "subtask"},
                        "direction": "inward",
                        "object": {"key": "FULLSTACK-9000"},
                    }
                ]
                if is_subtask
                else [],
            )
            db_session.add(subtask)

        db_session.commit()

        # Подсчитать количество запросов
        testing_returns_service = TestingReturnsService(db_session)

        with QueryCounter(db_session) as counter:
            hierarchy = testing_returns_service.get_task_hierarchy("FULLSTACK-9000")

        # Проверить результат
        assert (
            len(hierarchy) == 11
        ), f"Иерархия должна содержать 11 задач (1+10), получено {len(hierarchy)}"

        # Проверить производительность: не должно быть 100+ запросов
        assert counter.query_count < 20, (
            f"Слишком много запросов к БД: {counter.query_count}. "
            f"Ожидается < 20 для иерархии из 11 задач (не должны загружаться все 100 задач)."
        )

    def test_get_task_hierarchy_single_task_minimal_queries(self, db_session):
        """
        Проверка минимального количества запросов для одной задачи без subtasks.
        """
        # Создать одну задачу без subtasks
        single_task = TrackerTask(
            tracker_id="fs-single",
            key="FULLSTACK-8000",
            summary="Single Task",
            status="In Progress",
            author="test_dev",
            links=[],
        )
        db_session.add(single_task)
        db_session.commit()

        # Подсчитать количество запросов
        testing_returns_service = TestingReturnsService(db_session)

        with QueryCounter(db_session) as counter:
            hierarchy = testing_returns_service.get_task_hierarchy("FULLSTACK-8000")

        # Проверить результат
        assert hierarchy == [
            "FULLSTACK-8000"
        ], f"Ожидается ['FULLSTACK-8000'], получено {hierarchy}"

        # Проверить производительность: минимум запросов
        assert counter.query_count <= 2, (
            f"Слишком много запросов для одной задачи: {counter.query_count}. "
            f"Ожидается <= 2 (проверка существования + запрос subtasks)."
        )

    def test_get_task_hierarchy_circular_reference_performance(self, db_session):
        """
        Проверка производительности при циклических ссылках.
        Защита от бесконечной рекурсии должна предотвращать множественные запросы.
        """
        # Создать задачи с циклической ссылкой (task1 -> task2 -> task1)
        task1 = TrackerTask(
            tracker_id="fs-circular-1",
            key="FULLSTACK-7001",
            summary="Circular Task 1",
            status="In Progress",
            author="test_dev",
            links=[
                {
                    "type": {"id": "subtask"},
                    "direction": "inward",
                    "object": {"key": "FULLSTACK-7002"},
                }
            ],
        )
        db_session.add(task1)

        task2 = TrackerTask(
            tracker_id="fs-circular-2",
            key="FULLSTACK-7002",
            summary="Circular Task 2",
            status="In Progress",
            author="test_dev",
            links=[
                {
                    "type": {"id": "subtask"},
                    "direction": "inward",
                    "object": {"key": "FULLSTACK-7001"},
                }
            ],
        )
        db_session.add(task2)
        db_session.commit()

        # Подсчитать количество запросов
        testing_returns_service = TestingReturnsService(db_session)

        with QueryCounter(db_session) as counter:
            hierarchy = testing_returns_service.get_task_hierarchy("FULLSTACK-7001")

        # Проверить, что метод завершился без бесконечной рекурсии
        assert len(hierarchy) >= 1, "Иерархия должна содержать хотя бы одну задачу"

        # Проверить производительность: не должно быть сотен запросов из-за циклов
        assert counter.query_count < 10, (
            f"Слишком много запросов при циклических ссылках: {counter.query_count}. "
            f"Защита от циклов должна ограничивать количество запросов."
        )

    def test_get_task_hierarchy_three_level_depth(self, db_session):
        """
        Проверка производительности для трехуровневой иерархии.
        Parent -> Child -> Grandchild
        """
        # Уровень 1: Parent
        parent = TrackerTask(
            tracker_id="fs-3level-parent",
            key="FULLSTACK-6000",
            summary="Parent",
            status="In Progress",
            author="test_dev",
            links=[],
        )
        db_session.add(parent)

        # Уровень 2: Child
        child = TrackerTask(
            tracker_id="fs-3level-child",
            key="FULLSTACK-6001",
            summary="Child",
            status="In Progress",
            author="test_dev",
            links=[
                {
                    "type": {"id": "subtask"},
                    "direction": "inward",
                    "object": {"key": "FULLSTACK-6000"},
                }
            ],
        )
        db_session.add(child)

        # Уровень 3: Grandchild
        grandchild = TrackerTask(
            tracker_id="fs-3level-grandchild",
            key="FULLSTACK-6002",
            summary="Grandchild",
            status="In Progress",
            author="test_dev",
            links=[
                {
                    "type": {"id": "subtask"},
                    "direction": "inward",
                    "object": {"key": "FULLSTACK-6001"},
                }
            ],
        )
        db_session.add(grandchild)
        db_session.commit()

        # Подсчитать количество запросов
        testing_returns_service = TestingReturnsService(db_session)

        with QueryCounter(db_session) as counter:
            hierarchy = testing_returns_service.get_task_hierarchy("FULLSTACK-6000")

        # Проверить результат
        assert "FULLSTACK-6000" in hierarchy
        assert "FULLSTACK-6001" in hierarchy
        assert "FULLSTACK-6002" in hierarchy
        assert (
            len(hierarchy) == 3
        ), f"Иерархия должна содержать 3 задачи, получено {len(hierarchy)}"

        # Проверить производительность: ~ 3-4 запроса для 3 уровней
        assert counter.query_count <= 10, (
            f"Слишком много запросов для трехуровневой иерархии: {counter.query_count}. "
            f"Ожидается <= 10 для 3 уровней."
        )
