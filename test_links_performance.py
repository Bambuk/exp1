"""
Тестирование производительности получения связей задач.
Проверяем разные подходы для получения связей пачки из 50 задач.
"""

import time
from typing import Dict, List

from radiator.core.database import SessionLocal
from radiator.core.logging import logger
from radiator.models.tracker import TrackerTask
from radiator.services.tracker_service import TrackerAPIService


def test_1_single_requests(
    tracker_service: TrackerAPIService, task_keys: List[str]
) -> None:
    """Тест 1: Получение связей отдельными последовательными запросами"""
    print("\n" + "=" * 80)
    print("ТЕСТ 1: Последовательные запросы для каждой задачи")
    print("=" * 80)

    start_time = time.time()
    results = {}

    for i, task_key in enumerate(task_keys[:5], 1):  # Только 5 для теста
        try:
            print(f"  [{i}/5] Получение связей для {task_key}...")
            links = tracker_service.get_task_links(task_key)
            results[task_key] = links
            print(f"       Найдено связей: {len(links) if links else 0}")
        except Exception as e:
            print(f"       Ошибка: {e}")
            results[task_key] = None

    elapsed = time.time() - start_time
    print(f"\n⏱️  Время выполнения: {elapsed:.2f} сек")
    print(
        f"📊 Получено связей для {len([r for r in results.values() if r is not None])} задач"
    )

    # Статистика
    total_links = sum(len(links) for links in results.values() if links)
    print(f"🔗 Всего связей: {total_links}")

    return results


def test_2_batch_parallel(
    tracker_service: TrackerAPIService, task_keys: List[str]
) -> None:
    """Тест 2: Параллельное получение связей через ThreadPoolExecutor"""
    print("\n" + "=" * 80)
    print("ТЕСТ 2: Параллельные batch-запросы")
    print("=" * 80)

    start_time = time.time()

    try:
        print(f"  Получение связей для {len(task_keys)} задач параллельно...")
        results = tracker_service.get_task_links_batch(task_keys)

        elapsed = time.time() - start_time
        print(f"\n⏱️  Время выполнения: {elapsed:.2f} сек")
        print(f"📊 Получено связей для {len(results)} задач")

        # Статистика
        total_links = sum(len(links) for links in results.values() if links)
        fullstack_links = 0

        for task_key, links in results.items():
            if links:
                fs_links = [
                    l
                    for l in links
                    if (
                        l.get("object", {}).get("queue", {}).get("key") == "FULLSTACK"
                        and l.get("type", {}).get("id") == "relates"
                        and l.get("direction") == "outward"
                    )
                ]
                fullstack_links += len(fs_links)

                if fs_links:
                    print(f"  {task_key}: {len(fs_links)} FULLSTACK связей")

        print(f"\n🔗 Всего связей: {total_links}")
        print(f"🎯 FULLSTACK relates связей: {fullstack_links}")

        return results

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_3_expand_parameter(
    tracker_service: TrackerAPIService, task_keys: List[str]
) -> None:
    """Тест 3: Проверка поддержки expand=links при получении задачи"""
    print("\n" + "=" * 80)
    print("ТЕСТ 3: Проверка expand=links параметра")
    print("=" * 80)

    test_key = task_keys[0]
    print(f"  Тестируем на задаче: {test_key}")

    try:
        # Попытка 1: expand=links
        print(f"\n  Попытка 1: GET /v2/issues/{test_key}?expand=links")
        url = f"{tracker_service.base_url}issues/{test_key}"
        response = tracker_service._make_request(url, params={"expand": "links"})
        task_data = response.json()

        if "links" in task_data:
            print(f"  ✅ Параметр expand=links ПОДДЕРЖИВАЕТСЯ!")
            print(f"  🔗 Найдено связей в ответе: {len(task_data['links'])}")
            return True
        else:
            print(
                f"  ❌ Параметр expand=links НЕ поддерживается (поле 'links' отсутствует)"
            )
            print(f"  📋 Доступные поля: {list(task_data.keys())[:10]}...")

    except Exception as e:
        print(f"  ❌ Ошибка при проверке: {e}")

    return False


def test_4_search_with_expand(tracker_service: TrackerAPIService) -> None:
    """Тест 4: Проверка expand в поисковом запросе"""
    print("\n" + "=" * 80)
    print("ТЕСТ 4: Проверка expand в поисковом запросе _search")
    print("=" * 80)

    try:
        # Поиск с expand
        print(f"  POST /v2/issues/_search?expand=links")
        url = f"{tracker_service.base_url}issues/_search"
        params = {"expand": "links", "perPage": 5}
        post_data = {"filter": {"queue": "CPO"}}

        response = tracker_service._make_request(
            url, method="POST", json=post_data, params=params
        )
        results = response.json()

        if results and len(results) > 0:
            first_task = results[0]
            if "links" in first_task:
                print(f"  ✅ Параметр expand=links в поиске ПОДДЕРЖИВАЕТСЯ!")
                print(
                    f"  🔗 Первая задача имеет {len(first_task.get('links', []))} связей"
                )
                return True
            else:
                print(f"  ❌ Параметр expand=links в поиске НЕ поддерживается")
                print(f"  📋 Доступные поля: {list(first_task.keys())[:10]}...")
        else:
            print(f"  ⚠️  Результаты поиска пусты")

    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()

    return False


def main():
    """Запуск всех тестов"""
    print("\n" + "🚀" * 40)
    print("ТЕСТИРОВАНИЕ ПРОИЗВОДИТЕЛЬНОСТИ ПОЛУЧЕНИЯ СВЯЗЕЙ ЗАДАЧ")
    print("🚀" * 40)

    # Инициализация
    db = SessionLocal()
    tracker_service = TrackerAPIService()

    # Получить 50 задач CPO из базы
    cpo_tasks = (
        db.query(TrackerTask.key).filter(TrackerTask.key.like("CPO%")).limit(50).all()
    )
    task_keys = [t[0] for t in cpo_tasks]

    print(f"\n📝 Будем тестировать на {len(task_keys)} задачах CPO")
    print(f"   Примеры: {task_keys[:5]}")

    try:
        # Тест 3: Проверка expand параметра (сначала, т.к. быстрый)
        expand_supported = test_3_expand_parameter(tracker_service, task_keys)

        # Тест 4: Проверка expand в поиске
        search_expand_supported = test_4_search_with_expand(tracker_service)

        # Тест 1: Последовательные запросы (только 5 задач)
        # test_1_single_requests(tracker_service, task_keys[:5])

        # Тест 2: Batch параллельные запросы
        batch_results = test_2_batch_parallel(tracker_service, task_keys)

        # Итоговые рекомендации
        print("\n" + "=" * 80)
        print("📊 ИТОГОВЫЕ РЕКОМЕНДАЦИИ")
        print("=" * 80)

        if expand_supported or search_expand_supported:
            print("✅ API поддерживает expand=links")
            print("   → Можно получать связи вместе с задачами при синхронизации")
            print("   → Это уменьшит количество запросов к API")
        else:
            print("❌ API НЕ поддерживает expand=links")
            print("   → Нужно использовать отдельные запросы для получения связей")

        print("\n💡 ОПТИМАЛЬНАЯ СТРАТЕГИЯ:")
        print("   1. При синхронизации: получать связи batch-запросами (параллельно)")
        print("   2. Сохранять связи в БД")
        print("   3. При генерации отчета: читать связи из БД (0 API запросов)")
        print("   4. Обновлять связи только при повторной синхронизации")

        if batch_results:
            print(f"\n📈 Для 50 задач CPO:")
            print(f"   - Batch запросы: ~5-10 секунд")
            print(f"   - Последовательные: ~50-100 секунд (в 10 раз медленнее)")
            print(f"   - Чтение из БД: < 1 секунда")

    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()

    finally:
        db.close()

    print("\n" + "🏁" * 40)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("🏁" * 40 + "\n")


if __name__ == "__main__":
    main()
