"""End-to-end tests for testing returns with real database."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from radiator.commands.generate_time_to_market_report import (
    GenerateTimeToMarketReportCommand,
)
from radiator.commands.models.time_to_market_models import GroupBy
from radiator.models.tracker import TrackerTask, TrackerTaskHistory


class TestTestingReturnsE2E:
    """End-to-end tests for testing returns functionality with real database."""

    def test_ttm_report_finds_testing_returns_in_real_data(self, db_session):
        """
        E2E тест: CPO задача связана с FULLSTACK задачей, имеющей возвраты.
        Проверяем, что возвраты корректно отображаются в отчете.
        """
        # 1. Создать CPO задачу в test DB
        cpo_task = TrackerTask(
            tracker_id="cpo-test-001",
            key="CPO-999",
            summary="Test CPO Task",
            status="In Progress",
            author="test_author",
            links=[
                {
                    "type": {"id": "relates"},
                    "direction": "outward",
                    "object": {"key": "FULLSTACK-999"},
                }
            ],
        )
        db_session.add(cpo_task)
        db_session.flush()

        # 2. Создать FULLSTACK задачу с историей (3 входа в Testing = 2 возврата)
        fullstack_task = TrackerTask(
            tracker_id="fs-test-001",
            key="FULLSTACK-999",
            summary="Test FULLSTACK Task",
            status="Testing",
            author="test_dev",
            links=[
                {
                    "type": {"id": "relates"},
                    "direction": "inward",
                    "object": {"key": "CPO-999"},
                }
            ],
        )
        db_session.add(fullstack_task)
        db_session.flush()

        # Создать историю с возвратами из Testing
        base_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        history_entries = [
            # Первый вход в Testing
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="Open",
                status_display="Open",
                start_date=base_date,
                end_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
            ),
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="Testing",
                status_display="Testing",
                start_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 3, tzinfo=timezone.utc),
            ),
            # Возврат из Testing
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="In Progress",
                status_display="In Progress",
                start_date=datetime(2024, 1, 3, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 4, tzinfo=timezone.utc),
            ),
            # Второй вход в Testing
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="Testing",
                status_display="Testing",
                start_date=datetime(2024, 1, 4, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 5, tzinfo=timezone.utc),
            ),
            # Возврат из Testing
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="In Progress",
                status_display="In Progress",
                start_date=datetime(2024, 1, 5, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 6, tzinfo=timezone.utc),
            ),
            # Третий вход в Testing
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="Testing",
                status_display="Testing",
                start_date=datetime(2024, 1, 6, tzinfo=timezone.utc),
                end_date=None,
            ),
        ]
        for entry in history_entries:
            db_session.add(entry)

        db_session.commit()

        # 3. Проверить, что TestingReturnsService корректно находит возвраты
        from radiator.commands.services.testing_returns_service import (
            TestingReturnsService,
        )

        testing_returns_service = TestingReturnsService(db_session)

        # Получить связанные FULLSTACK задачи
        fullstack_links = testing_returns_service.get_fullstack_links("CPO-999")
        assert "FULLSTACK-999" in fullstack_links, "FULLSTACK-999 должен быть найден"

        # Проверить подсчет возвратов
        from radiator.commands.services.data_service import DataService

        data_service = DataService(db_session)
        (
            testing_returns,
            external_returns,
        ) = testing_returns_service.calculate_testing_returns_for_cpo_task(
            "CPO-999", data_service.get_task_history_by_key
        )

        assert (
            testing_returns == 2
        ), f"Ожидается 2 возврата из Testing, получено {testing_returns}"
        assert (
            external_returns == 0
        ), f"Ожидается 0 возвратов из Внешний тест, получено {external_returns}"

    def test_get_fullstack_links_parses_real_db_structure(self, db_session):
        """
        Тест: Проверка парсинга реальной структуры links (БЕЗ queue.key).
        Важно: в реальной БД links не содержит поле queue.
        """
        # Создать CPO задачу с links БЕЗ поля queue (как в реальной БД)
        cpo_task = TrackerTask(
            tracker_id="cpo-test-002",
            key="CPO-888",
            summary="Test CPO Task for Links Parsing",
            status="In Progress",
            author="test_author",
            links=[
                {
                    "type": {"id": "relates"},
                    "direction": "outward",
                    "object": {"key": "FULLSTACK-111"},
                    # ❌ Специально БЕЗ "queue": {"key": "FULLSTACK"}
                },
                {
                    "type": {"id": "relates"},
                    "direction": "outward",
                    "object": {"key": "FULLSTACK-222"},
                    # ❌ Специально БЕЗ "queue"
                },
                {
                    "type": {"id": "relates"},
                    "direction": "outward",
                    "object": {"key": "BACKEND-333"},  # Не FULLSTACK
                },
            ],
        )
        db_session.add(cpo_task)
        db_session.commit()

        # Проверить, что get_fullstack_links корректно парсит links
        from radiator.commands.services.testing_returns_service import (
            TestingReturnsService,
        )

        testing_returns_service = TestingReturnsService(db_session)
        fullstack_links = testing_returns_service.get_fullstack_links("CPO-888")

        # Должны быть найдены только FULLSTACK задачи
        assert "FULLSTACK-111" in fullstack_links, "FULLSTACK-111 должен быть найден"
        assert "FULLSTACK-222" in fullstack_links, "FULLSTACK-222 должен быть найден"
        assert "BACKEND-333" not in fullstack_links, "BACKEND-333 НЕ должен быть найден"

    def test_get_fullstack_links_handles_malformed_links(self, db_session):
        """
        Тест: Проверка обработки некорректных links (None, пустые dict, отсутствующие поля).
        """
        cpo_task = TrackerTask(
            tracker_id="cpo-test-003",
            key="CPO-777",
            summary="Test CPO Task with Malformed Links",
            status="In Progress",
            author="test_author",
            links=[
                None,  # None link
                {},  # Пустой dict
                {"type": {"id": "relates"}},  # Отсутствует object
                {
                    "type": {"id": "relates"},
                    "object": {},
                },  # Пустой object
                {
                    "type": {"id": "relates"},
                    "object": {"key": "FULLSTACK-555"},
                },  # Валидный
            ],
        )
        db_session.add(cpo_task)
        db_session.commit()

        from radiator.commands.services.testing_returns_service import (
            TestingReturnsService,
        )

        testing_returns_service = TestingReturnsService(db_session)

        # Не должно быть исключений
        fullstack_links = testing_returns_service.get_fullstack_links("CPO-777")

        # Должен быть найден только валидный link
        assert "FULLSTACK-555" in fullstack_links
        assert len(fullstack_links) == 1

    def test_external_test_returns_counted_correctly(self, db_session):
        """
        Тест: Проверка подсчета возвратов из "Внешний тест".
        """
        cpo_task = TrackerTask(
            tracker_id="cpo-test-004",
            key="CPO-666",
            summary="Test CPO Task for External Test Returns",
            status="In Progress",
            author="test_author",
            links=[
                {
                    "type": {"id": "relates"},
                    "direction": "outward",
                    "object": {"key": "FULLSTACK-444"},
                }
            ],
        )
        db_session.add(cpo_task)
        db_session.flush()

        fullstack_task = TrackerTask(
            tracker_id="fs-test-004",
            key="FULLSTACK-444",
            summary="Test FULLSTACK Task",
            status="Внешний тест",
            author="test_dev",
            links=[
                {
                    "type": {"id": "relates"},
                    "direction": "inward",
                    "object": {"key": "CPO-666"},
                }
            ],
        )
        db_session.add(fullstack_task)
        db_session.flush()

        # Создать историю с возвратами из Внешний тест
        base_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        history_entries = [
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="Open",
                status_display="Open",
                start_date=base_date,
                end_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
            ),
            # Первый вход в Внешний тест
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="Внешний тест",
                status_display="Внешний тест",
                start_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 3, tzinfo=timezone.utc),
            ),
            # Возврат
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="In Progress",
                status_display="In Progress",
                start_date=datetime(2024, 1, 3, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 4, tzinfo=timezone.utc),
            ),
            # Второй вход в Внешний тест
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="Внешний тест",
                status_display="Внешний тест",
                start_date=datetime(2024, 1, 4, tzinfo=timezone.utc),
                end_date=None,
            ),
        ]
        for entry in history_entries:
            db_session.add(entry)

        db_session.commit()

        # Проверить подсчет возвратов
        from radiator.commands.services.data_service import DataService
        from radiator.commands.services.testing_returns_service import (
            TestingReturnsService,
        )

        testing_returns_service = TestingReturnsService(db_session)
        data_service = DataService(db_session)

        (
            testing_returns,
            external_returns,
        ) = testing_returns_service.calculate_testing_returns_for_cpo_task(
            "CPO-666", data_service.get_task_history_by_key
        )

        assert (
            testing_returns == 0
        ), f"Ожидается 0 возвратов из Testing, получено {testing_returns}"
        assert (
            external_returns == 1
        ), f"Ожидается 1 возврат из Внешний тест, получено {external_returns}"

    def test_both_testing_and_external_test_returns(self, db_session):
        """
        Тест: Проверка подсчета возвратов из обоих статусов (Testing + Внешний тест).
        """
        cpo_task = TrackerTask(
            tracker_id="cpo-test-005",
            key="CPO-555",
            summary="Test CPO Task",
            status="In Progress",
            author="test_author",
            links=[
                {
                    "type": {"id": "relates"},
                    "direction": "outward",
                    "object": {"key": "FULLSTACK-333"},
                }
            ],
        )
        db_session.add(cpo_task)
        db_session.flush()

        fullstack_task = TrackerTask(
            tracker_id="fs-test-005",
            key="FULLSTACK-333",
            summary="Test FULLSTACK Task",
            status="Testing",
            author="test_dev",
            links=[
                {
                    "type": {"id": "relates"},
                    "direction": "inward",
                    "object": {"key": "CPO-555"},
                }
            ],
        )
        db_session.add(fullstack_task)
        db_session.flush()

        # Создать историю с возвратами из обоих статусов
        base_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        history_entries = [
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="Open",
                status_display="Open",
                start_date=base_date,
                end_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
            ),
            # Testing 1
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="Testing",
                status_display="Testing",
                start_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 3, tzinfo=timezone.utc),
            ),
            # Возврат
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="In Progress",
                status_display="In Progress",
                start_date=datetime(2024, 1, 3, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 4, tzinfo=timezone.utc),
            ),
            # Внешний тест 1
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="Внешний тест",
                status_display="Внешний тест",
                start_date=datetime(2024, 1, 4, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 5, tzinfo=timezone.utc),
            ),
            # Возврат
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="In Progress",
                status_display="In Progress",
                start_date=datetime(2024, 1, 5, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 6, tzinfo=timezone.utc),
            ),
            # Testing 2
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="Testing",
                status_display="Testing",
                start_date=datetime(2024, 1, 6, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 7, tzinfo=timezone.utc),
            ),
            # Возврат
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="In Progress",
                status_display="In Progress",
                start_date=datetime(2024, 1, 7, tzinfo=timezone.utc),
                end_date=datetime(2024, 1, 8, tzinfo=timezone.utc),
            ),
            # Внешний тест 2 (второй вход = 1 возврат!)
            TrackerTaskHistory(
                task_id=fullstack_task.id,
                tracker_id=fullstack_task.tracker_id,
                status="Внешний тест",
                status_display="Внешний тест",
                start_date=datetime(2024, 1, 8, tzinfo=timezone.utc),
                end_date=None,
            ),
        ]
        for entry in history_entries:
            db_session.add(entry)

        db_session.commit()

        # Проверить подсчет возвратов
        from radiator.commands.services.data_service import DataService
        from radiator.commands.services.testing_returns_service import (
            TestingReturnsService,
        )

        testing_returns_service = TestingReturnsService(db_session)
        data_service = DataService(db_session)

        (
            testing_returns,
            external_returns,
        ) = testing_returns_service.calculate_testing_returns_for_cpo_task(
            "CPO-555", data_service.get_task_history_by_key
        )

        assert (
            testing_returns == 1
        ), f"Ожидается 1 возврат из Testing, получено {testing_returns}"
        assert (
            external_returns == 1
        ), f"Ожидается 1 возврат из Внешний тест, получено {external_returns}"
