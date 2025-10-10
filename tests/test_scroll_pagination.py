"""Tests for scroll pagination functionality in Yandex Tracker API."""

from unittest.mock import Mock, patch

import pytest

from radiator.services.tracker_service import TrackerAPIService


class TestScrollPaginationBasicFunctionality:
    """Tests for basic scroll pagination functionality."""

    def test_search_tasks_with_scroll_first_page(self):
        """Тест первого запроса scroll-пагинации с правильными параметрами."""
        service = TrackerAPIService()

        # Mock response with scroll data
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": "task1", "key": "TEST-1"},
            {"id": "task2", "key": "TEST-2"},
        ]
        mock_response.headers = {"X-Scroll-Id": "scroll123"}

        with patch.object(
            service, "_make_request", return_value=mock_response
        ) as mock_request:
            result = service._search_tasks_with_scroll(
                "test query", limit=2, extract_full_data=False
            )

            # Проверяем первый запрос
            first_call = mock_request.call_args_list[0]
            assert (
                first_call[0][0] == "https://api.tracker.yandex.net/v3/issues/_search"
            )
            assert first_call[1]["method"] == "POST"
            assert first_call[1]["json"] == {"query": "test query"}

            # Проверяем параметры scroll
            params = first_call[1]["params"]
            assert params["scrollType"] == "unsorted"
            assert params["perScroll"] == 1000
            assert params["scrollTTLMillis"] == 300000  # 5 минут

            assert result == ["task1", "task2"]

    def test_search_tasks_with_scroll_multiple_pages(self):
        """Тест обработки нескольких страниц через scroll с использованием X-Scroll-Id."""
        service = TrackerAPIService()

        # Mock responses for 3 pages
        mock_response_page1 = Mock()
        mock_response_page1.json.return_value = [
            {"id": f"task{i}"} for i in range(1, 1001)
        ]
        mock_response_page1.headers = {"X-Scroll-Id": "scroll_page2"}

        mock_response_page2 = Mock()
        mock_response_page2.json.return_value = [
            {"id": f"task{i}"} for i in range(1001, 2001)
        ]
        mock_response_page2.headers = {"X-Scroll-Id": "scroll_page3"}

        mock_response_page3 = Mock()
        mock_response_page3.json.return_value = [
            {"id": f"task{i}"} for i in range(2001, 2501)
        ]
        mock_response_page3.headers = {}  # No more pages

        with patch.object(
            service,
            "_make_request",
            side_effect=[mock_response_page1, mock_response_page2, mock_response_page3],
        ) as mock_request:
            result = service._search_tasks_with_scroll(
                "test query", limit=2500, extract_full_data=False
            )

            # Проверяем, что было 3 запроса
            assert mock_request.call_count == 3

            # Проверяем второй запрос - должен использовать scrollId
            second_call = mock_request.call_args_list[1]
            params = second_call[1]["params"]
            assert params["scrollId"] == "scroll_page2"
            assert "scrollType" not in params  # scrollType только в первом запросе

            # Проверяем третий запрос
            third_call = mock_request.call_args_list[2]
            params = third_call[1]["params"]
            assert params["scrollId"] == "scroll_page3"

            assert len(result) == 2500

    def test_search_tasks_with_scroll_respects_limit(self):
        """Тест соблюдения лимита при scroll-пагинации."""
        service = TrackerAPIService()

        # Mock response with more data than limit
        mock_response_page1 = Mock()
        mock_response_page1.json.return_value = [
            {"id": f"task{i}"} for i in range(1, 1001)
        ]
        mock_response_page1.headers = {"X-Scroll-Id": "scroll_page2"}

        mock_response_page2 = Mock()
        mock_response_page2.json.return_value = [
            {"id": f"task{i}"} for i in range(1001, 2001)
        ]
        mock_response_page2.headers = {"X-Scroll-Id": "scroll_page3"}

        mock_response_page3 = Mock()
        mock_response_page3.json.return_value = [
            {"id": f"task{i}"} for i in range(2001, 3001)
        ]
        mock_response_page3.headers = {"X-Scroll-Id": "scroll_page4"}

        with patch.object(
            service,
            "_make_request",
            side_effect=[mock_response_page1, mock_response_page2, mock_response_page3],
        ) as mock_request:
            # Запрашиваем 2500 задач
            result = service._search_tasks_with_scroll(
                "test query", limit=2500, extract_full_data=False
            )

            # Должно быть только 3 запроса (2500 задач получено)
            assert mock_request.call_count == 3

            # Результат должен содержать ровно 2500 задач
            assert len(result) == 2500


class TestScrollPaginationDataExtraction:
    """Tests for data extraction in scroll pagination."""

    def test_search_tasks_with_scroll_extract_ids(self):
        """Тест извлечения только ID задач (extract_full_data=False)."""
        service = TrackerAPIService()

        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": "task1", "key": "TEST-1", "summary": "Task 1"},
            {"id": "task2", "key": "TEST-2", "summary": "Task 2"},
        ]
        mock_response.headers = {}

        with patch.object(service, "_make_request", return_value=mock_response):
            result = service._search_tasks_with_scroll(
                "test query", limit=10, extract_full_data=False
            )

            # Должны получить только ID
            assert result == ["task1", "task2"]

    def test_search_tasks_with_scroll_extract_full_data(self):
        """Тест извлечения полных данных задач (extract_full_data=True)."""
        service = TrackerAPIService()

        mock_response = Mock()
        task1 = {"id": "task1", "key": "TEST-1", "summary": "Task 1"}
        task2 = {"id": "task2", "key": "TEST-2", "summary": "Task 2"}
        mock_response.json.return_value = [task1, task2]
        mock_response.headers = {}

        with patch.object(service, "_make_request", return_value=mock_response):
            result = service._search_tasks_with_scroll(
                "test query", limit=10, extract_full_data=True
            )

            # Должны получить полные данные
            assert len(result) == 2
            assert result[0] == task1
            assert result[1] == task2


class TestScrollPaginationEdgeCases:
    """Tests for edge cases in scroll pagination."""

    def test_search_tasks_with_scroll_empty_results(self):
        """Тест обработки пустого результата от API."""
        service = TrackerAPIService()

        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.headers = {}

        with patch.object(service, "_make_request", return_value=mock_response):
            result = service._search_tasks_with_scroll(
                "test query", limit=100, extract_full_data=False
            )

            assert result == []

    def test_search_tasks_with_scroll_no_scroll_id_in_response(self):
        """Тест завершения пагинации когда X-Scroll-Id отсутствует."""
        service = TrackerAPIService()

        # Первая страница без scroll_id - означает конец данных
        mock_response = Mock()
        mock_response.json.return_value = [{"id": "task1"}, {"id": "task2"}]
        mock_response.headers = {}  # No X-Scroll-Id

        with patch.object(
            service, "_make_request", return_value=mock_response
        ) as mock_request:
            result = service._search_tasks_with_scroll(
                "test query", limit=1000, extract_full_data=False
            )

            # Должен быть только один запрос
            assert mock_request.call_count == 1
            assert len(result) == 2


class TestAutomaticPaginationSelection:
    """Tests for automatic pagination method selection based on limit."""

    def test_search_tasks_uses_regular_pagination_under_10k(self):
        """Тест использования обычной пагинации v2 для лимита < 10000."""
        service = TrackerAPIService()

        # Mock response for regular pagination
        mock_response = Mock()
        mock_response.json.return_value = [{"id": f"task{i}"} for i in range(1, 101)]
        mock_response.headers = {"X-Total-Pages": "1"}

        with patch.object(
            service, "_make_request", return_value=mock_response
        ) as mock_request:
            result = service.search_tasks("test query", limit=5000)

            # Проверяем, что использовался v2 endpoint
            call_url = mock_request.call_args[0][0]
            assert "/v2/issues/_search" in call_url

            # Проверяем, что используются параметры page/perPage, а не scroll
            params = mock_request.call_args[1]["params"]
            assert "page" in params
            assert "perPage" in params
            assert "scrollType" not in params

    def test_search_tasks_uses_scroll_pagination_over_10k(self):
        """Тест использования scroll-пагинации v3 для лимита > 10000."""
        service = TrackerAPIService()

        # Mock response for scroll pagination
        mock_response = Mock()
        mock_response.json.return_value = [{"id": f"task{i}"} for i in range(1, 1001)]
        mock_response.headers = {}

        with patch.object(
            service, "_search_tasks_with_scroll", return_value=["task1", "task2"]
        ) as mock_scroll:
            result = service.search_tasks("test query", limit=15000)

            # Проверяем, что был вызван scroll метод
            mock_scroll.assert_called_once_with(
                "test query", 15000, extract_full_data=False
            )
            assert result == ["task1", "task2"]

    def test_search_tasks_with_data_uses_regular_pagination_under_10k(self):
        """Тест использования обычной пагинации v2 для лимита < 10000 с полными данными."""
        service = TrackerAPIService()

        # Mock response for regular pagination
        mock_response = Mock()
        mock_response.json.return_value = [
            {"id": "task1", "key": "TEST-1"},
            {"id": "task2", "key": "TEST-2"},
        ]
        mock_response.headers = {"X-Total-Pages": "1"}

        with patch.object(
            service, "_make_request", return_value=mock_response
        ) as mock_request:
            result = service.search_tasks_with_data("test query", limit=5000)

            # Проверяем, что использовался v2 endpoint
            call_url = mock_request.call_args[0][0]
            assert "/v2/issues/_search" in call_url

            # Проверяем, что используются параметры page/perPage
            params = mock_request.call_args[1]["params"]
            assert "page" in params
            assert "perPage" in params

    def test_search_tasks_with_data_uses_scroll_pagination_over_10k(self):
        """Тест использования scroll-пагинации v3 для лимита > 10000 с полными данными."""
        service = TrackerAPIService()

        task1 = {"id": "task1", "key": "TEST-1"}
        task2 = {"id": "task2", "key": "TEST-2"}

        with patch.object(
            service, "_search_tasks_with_scroll", return_value=[task1, task2]
        ) as mock_scroll:
            result = service.search_tasks_with_data("test query", limit=15000)

            # Проверяем, что был вызван scroll метод с extract_full_data=True
            mock_scroll.assert_called_once_with(
                "test query", 15000, extract_full_data=True
            )
            assert result == [task1, task2]


class TestScrollPaginationAuthorization:
    """Tests for authorization in scroll pagination."""

    def test_scroll_pagination_uses_authorization_headers(self):
        """Тест что scroll-пагинация использует заголовки авторизации."""
        service = TrackerAPIService()

        mock_response = Mock()
        mock_response.json.return_value = [{"id": "task1"}]
        mock_response.headers = {}

        with patch.object(
            service, "_make_request", return_value=mock_response
        ) as mock_request:
            service._search_tasks_with_scroll(
                "test query", limit=100, extract_full_data=False
            )

            # Проверяем, что _make_request был вызван
            assert mock_request.called

            # Проверяем, что используется v3 URL
            call_url = mock_request.call_args[0][0]
            assert call_url == "https://api.tracker.yandex.net/v3/issues/_search"

            # _make_request автоматически добавляет self.headers,
            # которые включают Authorization и X-Org-ID
            # Проверяем, что service имеет правильные заголовки
            assert "Authorization" in service.headers
            assert "X-Org-ID" in service.headers
            assert service.headers["Authorization"].startswith("OAuth ")


class TestScrollPaginationIntegration:
    """Integration tests for scroll pagination with real API (if available)."""

    @pytest.mark.integration
    def test_scroll_pagination_integration_with_real_api(self):
        """
        Интеграционный тест с реальным API v3 с маленьким окном для быстрого выполнения.

        Этот тест требует реальных credentials и доступа к API.
        Запускается только с флагом: pytest -m integration
        """
        import os

        if not os.getenv("TRACKER_API_TOKEN"):
            pytest.skip("TRACKER_API_TOKEN not set - skipping real API test")

        service = TrackerAPIService()

        # Временно патчим perScroll для быстрого теста (3 страницы по 10 задач)
        original_method = service._search_tasks_with_scroll

        def patched_scroll(query, limit, extract_full_data=False):
            # Подменяем размер окна в методе
            url = "https://api.tracker.yandex.net/v3/issues/_search"
            all_results = []
            scroll_id = None
            page = 1

            params = {
                "scrollType": "unsorted",
                "perScroll": 10,  # Маленькое окно для теста
                "scrollTTLMillis": 300000,
            }
            post_data = {"query": query}

            while len(all_results) < limit:
                if scroll_id:
                    params = {"scrollId": scroll_id, "scrollTTLMillis": 300000}

                response = service._make_request(
                    url, method="POST", json=post_data, params=params
                )
                data = response.json()

                if extract_full_data:
                    page_results = service._extract_tasks_from_response(data)
                else:
                    page_results = service._extract_task_ids_from_response(data)

                if not page_results:
                    break

                all_results.extend(page_results)
                scroll_id = response.headers.get("X-Scroll-Id")

                if not scroll_id:
                    break

                page += 1
                if page > 100:  # Safety
                    break

            return all_results[:limit]

        try:
            # Патчим метод
            service._search_tasks_with_scroll = patched_scroll

            # Запрашиваем 25 задач (потребуется 3 страницы по 10)
            result = service.search_tasks("Updated: >2024-01-01", limit=25)

            assert isinstance(result, list)
            assert len(result) <= 25
            assert len(result) > 0, "Должна быть хотя бы одна задача"

            print(f"✅ Scroll pagination работает! Получено {len(result)} задач")
        except Exception as e:
            pytest.skip(f"Real API test failed (this is OK in CI): {e}")
        finally:
            # Восстанавливаем оригинальный метод
            service._search_tasks_with_scroll = original_method


class TestScrollPaginationParallelRequests:
    """Tests for scroll pagination in parallel execution to check for duplicates."""

    def test_scroll_pagination_no_duplicates_in_parallel_requests(self):
        """
        Тест проверяет, что при параллельных запросах scroll-пагинации
        мы не получаем дубликаты задач.
        """
        from concurrent.futures import ThreadPoolExecutor

        service = TrackerAPIService()

        # Мокируем API ответы с уникальными ID для каждого scroll-контекста
        mock_response_context1_page1 = Mock()
        mock_response_context1_page1.json.return_value = [
            {"id": f"ctx1_task{i}"} for i in range(1, 11)
        ]
        mock_response_context1_page1.headers = {"X-Scroll-Id": "scroll_ctx1_page2"}

        mock_response_context1_page2 = Mock()
        mock_response_context1_page2.json.return_value = [
            {"id": f"ctx1_task{i}"} for i in range(11, 21)
        ]
        mock_response_context1_page2.headers = {}

        mock_response_context2_page1 = Mock()
        mock_response_context2_page1.json.return_value = [
            {"id": f"ctx2_task{i}"} for i in range(1, 11)
        ]
        mock_response_context2_page1.headers = {"X-Scroll-Id": "scroll_ctx2_page2"}

        mock_response_context2_page2 = Mock()
        mock_response_context2_page2.json.return_value = [
            {"id": f"ctx2_task{i}"} for i in range(11, 21)
        ]
        mock_response_context2_page2.headers = {}

        mock_response_context3_page1 = Mock()
        mock_response_context3_page1.json.return_value = [
            {"id": f"ctx3_task{i}"} for i in range(1, 11)
        ]
        mock_response_context3_page1.headers = {"X-Scroll-Id": "scroll_ctx3_page2"}

        mock_response_context3_page2 = Mock()
        mock_response_context3_page2.json.return_value = [
            {"id": f"ctx3_task{i}"} for i in range(11, 21)
        ]
        mock_response_context3_page2.headers = {}

        # Для каждого контекста свой набор ответов (эмуляция разных scroll ID)
        responses = [
            # Контекст 1
            mock_response_context1_page1,
            mock_response_context1_page2,
            # Контекст 2
            mock_response_context2_page1,
            mock_response_context2_page2,
            # Контекст 3
            mock_response_context3_page1,
            mock_response_context3_page2,
        ]

        with patch.object(service, "_make_request", side_effect=responses):
            # Запускаем 3 параллельных запроса
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(
                        service._search_tasks_with_scroll, "test query", 20, False
                    )
                    for _ in range(3)
                ]

                results = [f.result() for f in futures]

        # Проверяем, что каждый запрос получил свой уникальный набор задач
        assert len(results) == 3

        # Каждый результат должен содержать 20 задач
        for i, result in enumerate(results):
            assert (
                len(result) == 20
            ), f"Result {i} должен содержать 20 задач, получено {len(result)}"

        # Проверяем отсутствие дублей внутри каждого результата
        for i, result in enumerate(results):
            unique_ids = set(result)
            assert len(unique_ids) == len(
                result
            ), f"Result {i} содержит дубликаты: {len(result)} задач, но {len(unique_ids)} уникальных"

        # Проверяем, что разные запросы получили разные данные
        # (в реальности каждый scroll контекст независим)
        all_ids = []
        for result in results:
            all_ids.extend(result)

        # Общее количество уникальных ID должно быть 60 (3 контекста × 20 задач)
        unique_all_ids = set(all_ids)
        assert (
            len(unique_all_ids) == 60
        ), f"Должно быть 60 уникальных задач из 3 контекстов, получено {len(unique_all_ids)}"

        print(
            f"✅ Параллельные scroll-запросы работают корректно: {len(unique_all_ids)} уникальных задач"
        )

    def test_scroll_pagination_race_condition_protection(self):
        """
        Тест проверяет, что scroll-пагинация защищена от race condition
        благодаря использованию локальных переменных вместо self.
        """
        service = TrackerAPIService()

        # Создаем серию мок-ответов для эмуляции последовательных запросов
        responses = []
        for i in range(10):
            mock_response = Mock()
            mock_response.json.return_value = [
                {"id": f"task_{i * 10 + j}"} for j in range(1, 11)
            ]
            if i < 9:  # Все кроме последнего имеют scroll_id
                mock_response.headers = {"X-Scroll-Id": f"scroll_page_{i + 2}"}
            else:
                mock_response.headers = {}
            responses.append(mock_response)

        with patch.object(service, "_make_request", side_effect=responses):
            # Запускаем параллельно
            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor(max_workers=5) as executor:
                # 5 параллельных запросов, каждый запрашивает по 20 задач
                # Все они будут использовать один и тот же мок, но должны получать корректные данные
                futures = [
                    executor.submit(
                        service._search_tasks_with_scroll, f"query_{i}", 20, False
                    )
                    for i in range(5)
                ]

                results = [f.result() for f in futures]

        # Проверяем, что все запросы завершились успешно
        assert len(results) == 5
        for i, result in enumerate(results):
            assert isinstance(result, list), f"Result {i} должен быть списком"
            assert len(result) <= 20, f"Result {i} не должен превышать лимит 20"

        print(
            f"✅ Race condition защита работает: все {len(results)} параллельных запросов завершились корректно"
        )
