#!/usr/bin/env python3
"""Script for batch syncing tracker tasks by keys from file."""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from tqdm import tqdm


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

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        error_msg = f"Batch sync failed with return code {result.returncode}"
        if result.stderr:
            error_msg += f"\nError: {result.stderr}"
        raise RuntimeError(error_msg)


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

        # Синхронизируем каждый батч
        print("🔄 Starting batch sync...")

        for i, batch in enumerate(tqdm(batches, desc="Syncing batches")):
            batch_num = i + 1
            total_batches = len(batches)

            print(
                f"\n📦 Processing batch {batch_num}/{total_batches} ({len(batch)} keys)..."
            )

            try:
                sync_batch(batch, args.skip_history, args.limit)
                print(f"✅ Batch {batch_num} completed successfully")
            except RuntimeError as e:
                print(f"❌ Batch {batch_num} failed: {e}")
                print(
                    f"🛑 Stopping sync. Processed {batch_num - 1}/{total_batches} batches"
                )
                sys.exit(1)

        print(f"\n🎉 All {len(batches)} batches completed successfully!")

    except FileNotFoundError:
        print(f"❌ File not found: {args.file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
