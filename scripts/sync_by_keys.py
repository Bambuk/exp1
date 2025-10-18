#!/usr/bin/env python3
"""Script for batch syncing tracker tasks by keys from file."""

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from tqdm import tqdm

# Progress tracking
PROGRESS_DIR = Path("data/.progress")


def get_progress_file_path(keys_file: str) -> Path:
    """Генерирует путь к файлу прогресса на основе имени файла с ключами"""
    # Используем hash для уникальности, но сохраняем читаемое имя
    file_hash = hashlib.md5(Path(keys_file).absolute().as_posix().encode()).hexdigest()[
        :8
    ]
    filename = f"{Path(keys_file).name}.{file_hash}.progress"
    return PROGRESS_DIR / filename


def save_progress(keys_file: str, batch_index: int, total_batches: int) -> None:
    """Сохраняет прогресс обработки"""
    PROGRESS_DIR.mkdir(exist_ok=True)
    progress_file = get_progress_file_path(keys_file)
    with open(progress_file, "w") as f:
        f.write(f"{batch_index}\n{total_batches}\n")


def load_progress(keys_file: str) -> Optional[Tuple[int, int]]:
    """Загружает прогресс обработки. Возвращает (batch_index, total_batches) или None"""
    progress_file = get_progress_file_path(keys_file)
    if not progress_file.exists():
        return None
    with open(progress_file, "r") as f:
        lines = f.readlines()
        if len(lines) >= 2:
            return int(lines[0].strip()), int(lines[1].strip())
    return None


def clear_progress(keys_file: str) -> None:
    """Удаляет файл прогресса"""
    progress_file = get_progress_file_path(keys_file)
    if progress_file.exists():
        progress_file.unlink()


def read_keys_from_file(filepath: str) -> List[str]:
    """Читает ключи из файла, игнорирует пустые строки."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Игнорируем пустые строки и строки только с пробелами
    keys = [line.strip() for line in lines if line.strip()]
    return keys


def validate_key(key: str) -> bool:
    """Проверяет формат ключа: QUEUE-NUMBER."""
    # Паттерн: буквы-цифры, дефис, цифры
    pattern = r"^[A-Za-z0-9]+-\d+$"
    return bool(re.match(pattern, key))


def split_into_batches(keys: List[str], batch_size: int) -> List[List[str]]:
    """Разбивает список ключей на батчи."""
    batches = []
    for i in range(0, len(keys), batch_size):
        batch = keys[i : i + batch_size]
        batches.append(batch)
    return batches


def build_sync_command(
    keys: List[str], skip_history: bool, limit: Optional[int]
) -> List[str]:
    """Формирует команду для subprocess."""
    # Создаем фильтр с ключами
    filter_value = f"Key: {', '.join(keys)}"

    cmd = ["python", "-m", "radiator.commands.sync_tracker", "--filter", filter_value]

    if skip_history:
        cmd.append("--skip-history")

    if limit is not None:
        cmd.extend(["--limit", str(limit)])

    return cmd


def sync_batch(keys: List[str], skip_history: bool, limit: Optional[int]) -> None:
    """Синхронизирует один батч, выбрасывает исключение при ошибке."""
    cmd = build_sync_command(keys, skip_history, limit)

    # Запускаем без capture_output, чтобы вывод sync-tracker показывался в консоли
    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise RuntimeError(f"Batch sync failed with return code {result.returncode}")


def main():
    """Основная логика с argparse."""
    parser = argparse.ArgumentParser(
        description="Sync tracker tasks by keys from file in batches"
    )
    parser.add_argument(
        "--file", "-f", required=True, help="Path to file with task keys (one per line)"
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=200,
        help="Batch size for syncing (default: 200)",
    )
    parser.add_argument(
        "--skip-history", action="store_true", help="Skip history when syncing"
    )
    parser.add_argument("--limit", type=int, help="Limit number of tasks to sync")
    parser.add_argument(
        "--reset-progress",
        action="store_true",
        help="Reset progress and start from beginning",
    )

    args = parser.parse_args()

    try:
        # Читаем ключи из файла
        print(f"📖 Reading keys from {args.file}...")
        keys = read_keys_from_file(args.file)

        if not keys:
            print("❌ No keys found in file")
            sys.exit(1)

        # Валидируем ключи
        print("🔍 Validating keys...")
        invalid_keys = [key for key in keys if not validate_key(key)]
        if invalid_keys:
            print(f"❌ Invalid key format found: {invalid_keys}")
            sys.exit(1)

        print(f"✅ Found {len(keys)} valid keys")

        # Разбиваем на батчи
        batches = split_into_batches(keys, args.batch_size)
        print(f"📦 Split into {len(batches)} batches of max {args.batch_size} keys")

        # Обрабатываем прогресс
        if args.reset_progress:
            clear_progress(args.file)
            print("🔄 Progress reset")
            start_batch = 0
        else:
            progress = load_progress(args.file)
            if progress:
                saved_batch, saved_total = progress
                print(f"📌 Found saved progress: batch {saved_batch}/{saved_total}")

                # Проверяем что количество батчей не изменилось
                if saved_total == len(batches):
                    start_batch = saved_batch
                    print(f"▶️  Continuing from batch {start_batch + 1}")
                else:
                    print(
                        f"⚠️  Batch count changed ({saved_total} → {len(batches)}), starting from beginning"
                    )
                    start_batch = 0
            else:
                start_batch = 0

        # Синхронизируем начиная с start_batch
        print("🔄 Starting batch sync...")

        for i in range(start_batch, len(batches)):
            batch = batches[i]
            batch_num = i + 1
            total_batches = len(batches)

            print(
                f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} keys)..."
            )

            try:
                sync_batch(batch, args.skip_history, args.limit)
                # Сохраняем прогресс после успешного батча
                save_progress(args.file, i + 1, len(batches))
                print(f"✅ Batch {batch_num} completed successfully")
            except RuntimeError as e:
                print(f"❌ Batch {batch_num} failed: {e}")
                print(f"💾 Progress saved. Run again to continue from batch {batch_num}")
                sys.exit(1)

        # Успешно завершили все - удаляем прогресс
        clear_progress(args.file)
        print(f"\n🎉 All {len(batches)} batches completed successfully!")

    except FileNotFoundError:
        print(f"❌ File not found: {args.file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
