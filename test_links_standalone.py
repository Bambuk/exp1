"""
Standalone тестирование производительности получения связей задач.
Не требует изменений в существующем коде - работает напрямую с API.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import requests

from radiator.core.config import settings
from radiator.core.database import SessionLocal
from radiator.models.tracker import TrackerTask


class LinksAPITester:
    """Тестер для проверки разных методов получения связей"""

    def __init__(self):
        self.headers = {
            "Authorization": f"OAuth {settings.TRACKER_API_TOKEN}",
            "X-Org-ID": settings.TRACKER_ORG_ID,
            "Content-Type": "application/json",
        }
        self.base_url = settings.TRACKER_BASE_URL
        self.request_delay = 0.1

    def _make_request(self, url: str, method: str = "GET", **kwargs):
        """Выполнить HTTP запрос"""
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            time.sleep(self.request_delay)
            return response
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️  Ошибка запроса: {e}")
            raise

    def get_task_links(self, task_key: str) -> Optional[List[Dict]]:
        """Получить связи задачи"""
        try:
            url = f"{self.base_url}issues/{task_key}/links"
            response = self._make_request(url)
            return response.json()
        except Exception as e:
            print(f"  ❌ Ошибка получения связей для {task_key}: {e}")
            return None

    def get_task_links_batch(
        self, task_keys: List[str], max_workers: int = 10
    ) -> Dict[str, List[Dict]]:
        """Получить связи для множества задач параллельно"""
        results = {}
        total = len(task_keys)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_key = {
                executor.submit(self.get_task_links, key): key for key in task_keys
            }

            completed = 0
            for future in as_completed(future_to_key):
                task_key = future_to_key[future]
                completed += 1

                try:
                    links = future.result()
                    results[task_key] = links if links else []

                    # Прогресс каждые 10 задач
                    if completed % 10 == 0 or completed == total:
                        print(f"  Прогресс: {completed}/{total} задач")

                except Exception as e:
                    print(f"  ❌ Ошибка для {task_key}: {e}")
                    results[task_key] = []

        return results

    def test_expand_in_get_task(self, task_key: str) -> bool:
        """Проверить поддержку expand=links при получении задачи"""
        try:
            url = f"{self.base_url}issues/{task_key}"
            response = self._make_request(url, params={"expand": "links"})
            task_data = response.json()
            return "links" in task_data
        except:
            return False

    def test_expand_in_search(self) -> bool:
        """Проверить поддержку expand=links в поиске"""
        try:
            url = f"{self.base_url}issues/_search"
            params = {"expand": "links", "perPage": 2}
            post_data = {"filter": {"queue": "CPO"}}

            response = self._make_request(
                url, method="POST", json=post_data, params=params
            )
            results = response.json()

            if results and len(results) > 0:
                return "links" in results[0]
            return False
        except:
            return False


def analyze_links(results: Dict[str, List[Dict]]) -> None:
    """Анализ полученных связей"""
    print("\n📊 АНАЛИЗ СВЯЗЕЙ:")
    print("=" * 80)

    total_tasks = len(results)
    tasks_with_links = len([k for k, v in results.items() if v and len(v) > 0])
    total_links = sum(len(v) for v in results.values() if v)

    # Подсчет FULLSTACK связей
    fullstack_tasks = 0
    fullstack_links_count = 0
    relates_links = 0
    outward_links = 0

    examples = []

    for task_key, links in results.items():
        if not links:
            continue

        task_fs_links = []
        for link in links:
            link_type = link.get("type", {}).get("id", "")
            direction = link.get("direction", "")
            queue = link.get("object", {}).get("queue", {}).get("key", "")
            linked_key = link.get("object", {}).get("key", "")

            if queue == "FULLSTACK":
                fullstack_links_count += 1
                if link_type == "relates" and direction == "outward":
                    task_fs_links.append(linked_key)

            if link_type == "relates":
                relates_links += 1
            if direction == "outward":
                outward_links += 1

        if task_fs_links:
            fullstack_tasks += 1
            if len(examples) < 5:
                examples.append((task_key, task_fs_links))

    print(f"  Всего задач проверено: {total_tasks}")
    print(
        f"  Задач со связями: {tasks_with_links} ({tasks_with_links/total_tasks*100:.1f}%)"
    )
    print(f"  Всего связей найдено: {total_links}")
    print(f"")
    print(f"  🎯 Связи с очередью FULLSTACK: {fullstack_links_count}")
    print(f"  🔗 Связи типа 'relates': {relates_links}")
    print(f"  ➡️  Связи 'outward': {outward_links}")
    print(f"")
    print(
        f"  📝 CPO задач с FULLSTACK связями: {fullstack_tasks} ({fullstack_tasks/total_tasks*100:.1f}%)"
    )

    if examples:
        print(f"\n  Примеры CPO → FULLSTACK связей:")
        for cpo_key, fs_keys in examples:
            print(f"    {cpo_key} → {', '.join(fs_keys[:3])}")


def main():
    """Основная функция"""
    print("\n" + "🚀" * 40)
    print("ТЕСТИРОВАНИЕ ПОЛУЧЕНИЯ СВЯЗЕЙ ЗАДАЧ (STANDALONE)")
    print("🚀" * 40)

    # Получить задачи из БД
    db = SessionLocal()
    cpo_tasks = (
        db.query(TrackerTask.key).filter(TrackerTask.key.like("CPO%")).limit(50).all()
    )
    task_keys = [t[0] for t in cpo_tasks]
    db.close()

    if not task_keys:
        print("❌ Не найдено CPO задач в базе данных")
        return

    print(f"\n📝 Найдено {len(task_keys)} CPO задач для тестирования")
    print(f"   Примеры: {task_keys[:5]}")

    tester = LinksAPITester()

    # ===== ТЕСТ 1: Проверка expand параметра =====
    print("\n" + "=" * 80)
    print("ТЕСТ 1: Проверка поддержки expand=links")
    print("=" * 80)

    test_key = task_keys[0]
    print(f"  Проверяем expand в GET /issues/{test_key}...")
    expand_in_get = tester.test_expand_in_get_task(test_key)

    print(f"  Проверяем expand в POST /issues/_search...")
    expand_in_search = tester.test_expand_in_search()

    print(f"\n  Результаты:")
    print(
        f"    expand в GET /issues/{{key}}: {'✅ ПОДДЕРЖИВАЕТСЯ' if expand_in_get else '❌ НЕ поддерживается'}"
    )
    print(
        f"    expand в POST /issues/_search: {'✅ ПОДДЕРЖИВАЕТСЯ' if expand_in_search else '❌ НЕ поддерживается'}"
    )

    # ===== ТЕСТ 2: Последовательные запросы (на 5 задачах) =====
    print("\n" + "=" * 80)
    print("ТЕСТ 2: Последовательные запросы (5 задач)")
    print("=" * 80)

    sequential_keys = task_keys[:5]
    start_time = time.time()

    sequential_results = {}
    for i, key in enumerate(sequential_keys, 1):
        print(f"  [{i}/5] Получение связей для {key}...")
        links = tester.get_task_links(key)
        sequential_results[key] = links if links else []

    sequential_time = time.time() - start_time
    print(f"\n⏱️  Время выполнения: {sequential_time:.2f} сек")
    print(f"📊 Среднее время на задачу: {sequential_time/5:.2f} сек")

    # ===== ТЕСТ 3: Параллельные batch запросы =====
    print("\n" + "=" * 80)
    print(f"ТЕСТ 3: Параллельные batch запросы ({len(task_keys)} задач)")
    print("=" * 80)

    start_time = time.time()
    batch_results = tester.get_task_links_batch(task_keys, max_workers=10)
    batch_time = time.time() - start_time

    print(f"\n⏱️  Время выполнения: {batch_time:.2f} сек")
    print(f"📊 Среднее время на задачу: {batch_time/len(task_keys):.2f} сек")

    # Анализ результатов
    analyze_links(batch_results)

    # ===== ИТОГИ =====
    print("\n" + "=" * 80)
    print("📊 СРАВНЕНИЕ ПРОИЗВОДИТЕЛЬНОСТИ")
    print("=" * 80)

    if sequential_time > 0:
        speedup = (sequential_time / 5 * len(task_keys)) / batch_time
        print(
            f"  Последовательно (экстраполяция на 50 задач): ~{sequential_time/5*len(task_keys):.1f} сек"
        )
        print(f"  Параллельно (batch): {batch_time:.1f} сек")
        print(f"  Ускорение: в {speedup:.1f} раз")

    print("\n" + "=" * 80)
    print("💡 РЕКОМЕНДАЦИИ ДЛЯ ПЛАНА")
    print("=" * 80)

    if expand_in_get or expand_in_search:
        print("  ✅ Используйте expand=links при синхронизации")
        print("     → Получайте связи вместе с задачами")
        print("     → Уменьшит количество запросов к API")
    else:
        print("  ⚠️  expand=links не поддерживается")
        print("     → Используйте batch-запросы с ThreadPoolExecutor")

    print("\n  📌 Обязательно:")
    print("     1. Получать связи batch-запросами при синхронизации")
    print("     2. Сохранять связи в БД (модель TrackerTaskLink)")
    print("     3. При генерации отчета читать из БД")
    print(
        f"     4. Ожидаемое время синхронизации связей для 100 задач: ~{batch_time*2:.1f} сек"
    )

    print("\n" + "🏁" * 40 + "\n")


if __name__ == "__main__":
    main()
