#!/usr/bin/env python3
"""Скрипт для генерации файла с отсутствующими задачами."""

import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Добавляем корень проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from radiator.core.config import settings
from radiator.models.tracker import TrackerTask


def generate_missing_tasks(keys_file: str, output_file: str):
    """Генерирует файл с отсутствующими задачами."""

    # Читаем ключи из файла
    print(f"📖 Читаем ключи из {keys_file}...")
    with open(keys_file, "r") as f:
        all_keys = [line.strip() for line in f if line.strip()]

    print(f"📊 Всего ключей в файле: {len(all_keys)}")

    # Подключаемся к базе данных (используем синхронный URL)
    print("🔌 Подключаемся к базе данных...")
    sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(sync_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with SessionLocal() as db:
        # Получаем все ключи из базы данных
        print("🔍 Загружаем существующие ключи из базы данных...")
        existing_keys_query = (
            db.query(TrackerTask.key).filter(TrackerTask.key.in_(all_keys)).all()
        )

        existing_keys = {row[0] for row in existing_keys_query}
        print(f"📋 Найдено в базе: {len(existing_keys)} задач")

        # Находим отсутствующие
        missing_keys = set(all_keys) - existing_keys
        print(f"❌ Отсутствует в базе: {len(missing_keys)} задач")

        # Сохраняем отсутствующие ключи в файл
        print(f"💾 Сохраняем отсутствующие задачи в {output_file}...")
        with open(output_file, "w") as f:
            for key in sorted(missing_keys):
                f.write(f"{key}\n")

        print(f"✅ Готово! Создан файл {output_file} с {len(missing_keys)} задачами")

        # Показываем статистику
        print(f"\n📈 Статистика:")
        print(f"   Всего в файле: {len(all_keys)}")
        print(f"   Есть в базе: {len(existing_keys)}")
        print(f"   Отсутствует: {len(missing_keys)}")
        print(f"   Процент загруженных: {len(existing_keys)/len(all_keys)*100:.1f}%")

        # Показываем количество батчей
        batch_size = 200
        total_batches = (len(missing_keys) + batch_size - 1) // batch_size
        print(f"\n🔄 Планирование загрузки:")
        print(f"   Размер батча: {batch_size}")
        print(f"   Количество батчей: {total_batches}")
        print(f"   Время загрузки (примерно): {total_batches * 2.5 / 60:.1f} часов")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Использование: python generate_missing_tasks.py <входной_файл> <выходной_файл>"
        )
        print(
            "Пример: python generate_missing_tasks.py data/input/fs_ids.txt data/input/missing_tasks.txt"
        )
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    if not Path(input_file).exists():
        print(f"❌ Файл {input_file} не найден")
        sys.exit(1)

    generate_missing_tasks(input_file, output_file)
