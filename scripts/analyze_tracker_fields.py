#!/usr/bin/env python3
"""
Скрипт для анализа полей API Tracker и тестирования параметра fields.

Извлекает все поля из ответа API, сохраняет их в файл и тестирует параметр fields.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from radiator.core.config import settings
from radiator.core.logging import logger
from radiator.services.tracker_service import tracker_service


def extract_all_fields_from_tasks(tasks: List[Dict[str, Any]]) -> Set[str]:
    """
    Извлекает все уникальные поля верхнего уровня из списка задач.

    Args:
        tasks: Список задач из API

    Returns:
        Множество уникальных полей
    """
    all_fields = set()

    for task in tasks:
        if isinstance(task, dict):
            # Добавляем все поля верхнего уровня
            for field_name in task.keys():
                all_fields.add(field_name)

    return all_fields


def save_fields_to_file(fields: Set[str], file_path: Path) -> None:
    """
    Сохраняет поля в файл, отсортированные по алфавиту.

    Args:
        fields: Множество полей
        file_path: Путь к файлу для сохранения
    """
    # Создаем директорию если не существует
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Сортируем поля по алфавиту
    sorted_fields = sorted(fields)

    with open(file_path, "w", encoding="utf-8") as f:
        for field in sorted_fields:
            f.write(f"{field}\n")

    logger.info(f"Сохранено {len(sorted_fields)} полей в {file_path}")


def load_fields_from_file(file_path: Path) -> List[str]:
    """
    Загружает поля из файла.

    Args:
        file_path: Путь к файлу с полями

    Returns:
        Список полей
    """
    if not file_path.exists():
        logger.error(f"Файл {file_path} не найден")
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        fields = [line.strip() for line in f if line.strip()]

    logger.info(f"Загружено {len(fields)} полей из {file_path}")
    return fields


def analyze_api_fields():
    """
    Анализирует поля API Tracker и сохраняет их в файл.
    """
    logger.info("🔍 Начинаем анализ полей API Tracker...")

    try:
        # Делаем POST запрос к API для получения 10 задач
        logger.info(
            "📥 Запрашиваем 10 задач с фильтром 'Queue: CPO Updated: >=2025-10-10'..."
        )

        url = f"{tracker_service.base_url}issues/_search"
        post_data = {"query": "Queue: CPO Updated: >=2025-10-10"}
        params = {"perPage": 10, "page": 1, "expand": "links"}

        response = tracker_service._make_request(
            url, method="POST", json=post_data, params=params
        )

        data = response.json()
        logger.info(f"✅ Получен ответ от API")

        # Извлекаем задачи из ответа
        tasks = tracker_service._extract_tasks_from_response(data)
        logger.info(f"📋 Найдено {len(tasks)} задач")

        if not tasks:
            logger.error("❌ Не получено ни одной задачи")
            return False

        # Извлекаем все уникальные поля
        all_fields = extract_all_fields_from_tasks(tasks)
        logger.info(f"🔍 Найдено {len(all_fields)} уникальных полей")

        # Выводим поля для отладки
        logger.info("📝 Найденные поля:")
        for field in sorted(all_fields):
            logger.info(f"  - {field}")

        # Сохраняем поля в файл
        fields_file = project_root / "data" / "config" / "fields.txt"
        save_fields_to_file(all_fields, fields_file)

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка при анализе полей: {e}")
        import traceback

        logger.error(f"📍 Stacktrace: {traceback.format_exc()}")
        return False


def test_fields_parameter():
    """
    Тестирует параметр fields с дополнительным полем customer.
    """
    logger.info("🧪 Тестируем параметр fields...")

    try:
        # Загружаем поля из файла
        fields_file = project_root / "data" / "config" / "fields.txt"
        fields = load_fields_from_file(fields_file)

        if not fields:
            logger.error("❌ Не удалось загрузить поля из файла")
            return False

        # Добавляем поле customer
        fields_with_customer = fields + ["customer"]
        fields_string = ",".join(fields_with_customer)

        logger.info(f"📝 Тестируем с полями: {fields_string}")

        # Делаем тестовый запрос с параметром fields
        url = f"{tracker_service.base_url}issues/_search"
        post_data = {"query": "Queue: CPO Updated: >=2025-10-10"}
        params = {"perPage": 1, "page": 1, "expand": "links", "fields": fields_string}

        logger.info("📥 Отправляем тестовый запрос с параметром fields...")
        response = tracker_service._make_request(
            url, method="POST", json=post_data, params=params
        )

        data = response.json()
        logger.info("✅ Получен ответ от API с параметром fields")

        # Извлекаем задачи из ответа
        tasks = tracker_service._extract_tasks_from_response(data)

        if not tasks:
            logger.error("❌ Не получено ни одной задачи в тестовом запросе")
            return False

        # Анализируем результат
        task = tasks[0]
        response_fields = set(task.keys())

        logger.info(f"📊 Результат тестирования:")
        logger.info(f"  - Запрошено полей: {len(fields_with_customer)}")
        logger.info(f"  - Получено полей: {len(response_fields)}")
        logger.info(f"  - Поля в ответе: {sorted(response_fields)}")

        # Проверяем, что customer не в ответе (если его нет в реальных данных)
        if "customer" in response_fields:
            logger.info("✅ Поле 'customer' присутствует в ответе")
            customer_value = task.get("customer")
            logger.info(f"   Значение customer: {customer_value}")
        else:
            logger.info(
                "ℹ️ Поле 'customer' отсутствует в ответе (возможно, не заполнено в данных)"
            )

        # Проверяем, что другие поля присутствуют
        expected_fields = set(fields)
        missing_fields = expected_fields - response_fields
        extra_fields = response_fields - expected_fields - {"customer"}

        if missing_fields:
            logger.warning(f"⚠️ Отсутствуют ожидаемые поля: {sorted(missing_fields)}")
        else:
            logger.info("✅ Все ожидаемые поля присутствуют")

        if extra_fields:
            logger.info(f"ℹ️ Дополнительные поля в ответе: {sorted(extra_fields)}")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании fields: {e}")
        import traceback

        logger.error(f"📍 Stacktrace: {traceback.format_exc()}")
        return False


def main():
    """Основная функция скрипта."""
    # Устанавливаем уровень логирования для отображения всех сообщений
    import logging

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    logger.info("🚀 Запуск анализа полей API Tracker")

    # Проверяем настройки
    if not settings.TRACKER_API_TOKEN:
        logger.error("❌ TRACKER_API_TOKEN не установлен")
        sys.exit(1)

    if not settings.TRACKER_ORG_ID:
        logger.error("❌ TRACKER_ORG_ID не установлен")
        sys.exit(1)

    # Анализируем поля
    if not analyze_api_fields():
        logger.error("❌ Не удалось проанализировать поля")
        sys.exit(1)

    # Тестируем параметр fields
    if not test_fields_parameter():
        logger.error("❌ Не удалось протестировать параметр fields")
        sys.exit(1)

    logger.info("🎉 Анализ и тестирование завершены успешно!")


if __name__ == "__main__":
    main()
