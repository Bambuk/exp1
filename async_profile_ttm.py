#!/usr/bin/env python3
"""Async profiling of TTM Details report generation with parallel testing returns calculation."""

import asyncio
import concurrent.futures
import time
from threading import Lock

from radiator.commands.generate_ttm_details_report import TTMDetailsReportGenerator
from radiator.core.database import SessionLocal


class AsyncTTMDetailsReportGenerator(TTMDetailsReportGenerator):
    """Async version of TTMDetailsReportGenerator with parallel testing returns calculation."""

    def __init__(self, db, config_dir="data/config", max_workers=50):
        super().__init__(db, config_dir)
        self.max_workers = max_workers
        self.testing_returns_cache = {}
        self.cache_lock = Lock()

    def _calculate_testing_returns_sync(self, task_key: str) -> tuple[int, int]:
        """Synchronous version of testing returns calculation."""
        try:
            return self.testing_returns_service.calculate_testing_returns_for_cpo_task(
                task_key, self.data_service.get_task_history_by_key
            )
        except Exception as e:
            print(f"Warning: Failed to calculate testing returns for {task_key}: {e}")
            return 0, 0

    async def _calculate_testing_returns_async(self, task_key: str) -> tuple[int, int]:
        """Async version of testing returns calculation."""
        # Check cache first
        with self.cache_lock:
            if task_key in self.testing_returns_cache:
                return self.testing_returns_cache[task_key]

        # Run in thread pool
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            result = await loop.run_in_executor(
                executor, self._calculate_testing_returns_sync, task_key
            )

        # Cache result
        with self.cache_lock:
            self.testing_returns_cache[task_key] = result

        return result

    async def _collect_csv_rows_async(self):
        """Async version of CSV rows collection with parallel testing returns."""
        rows = []
        quarters = self._load_quarters()
        done_statuses = self._load_done_statuses()

        print(f"🔄 Processing {len(quarters)} quarters...")

        for quarter in quarters:
            print(f"📅 Processing quarter {quarter.name}...")
            tasks = self._get_ttm_tasks_for_quarter(quarter)
            print(f"📋 Found {len(tasks)} tasks for {quarter.name}")

            if not tasks:
                continue

            # Load history for all tasks in this quarter
            history_data = {}
            for task in tasks:
                history = self.data_service.get_task_history(task.id)
                if history:
                    history_data[task.id] = history

            # Calculate all metrics in parallel
            print(f"⚡ Calculating metrics for {len(tasks)} tasks in parallel...")

            # Create tasks for parallel execution
            async_tasks = []
            for task in tasks:
                history = history_data.get(task.id, [])
                if not history:
                    continue

                # Create async task for this task
                async_task = self._process_single_task_async(
                    task, quarter, history, done_statuses
                )
                async_tasks.append(async_task)

            # Execute all tasks in parallel with limited concurrency
            semaphore = asyncio.Semaphore(self.max_workers)

            async def process_with_semaphore(async_task):
                async with semaphore:
                    return await async_task

            # Run all tasks
            results = await asyncio.gather(
                *[process_with_semaphore(task) for task in async_tasks]
            )

            # Add results to rows
            for result in results:
                if result:
                    rows.append(result)

            print(
                f"✅ Completed {quarter.name}: {len([r for r in results if r])} valid tasks"
            )

        return rows

    async def _process_single_task_async(self, task, quarter, history, done_statuses):
        """Process a single task asynchronously."""
        try:
            # Calculate TTM
            ttm = self._calculate_ttm(task.id, done_statuses, history)
            if ttm is None:
                print(f"⚠️  No TTM for {task.key}")
                return None

            # Calculate other metrics
            tail = self._calculate_tail(task.id, history)
            devlt = self._calculate_devlt(task.id, history)

            # Calculate TTD
            ttd = self._calculate_ttd(task.id, ["Готова к разработке"], history)
            ttd_quarter = None
            if ttd is not None:
                ttd_target_date = self._get_ttd_target_date(history)
                if ttd_target_date:
                    quarters = self._load_quarters()
                    ttd_quarter = self._determine_quarter_for_date(
                        ttd_target_date, quarters
                    )

            # Calculate pause metrics
            pause = self._calculate_pause(task.id, history)
            ttd_pause = self._calculate_ttd_pause(task.id, history)

            # Calculate status duration metrics
            discovery_backlog_days = self._calculate_discovery_backlog_days(
                task.id, history
            )
            ready_for_dev_days = self._calculate_ready_for_dev_days(task.id, history)

            # Calculate testing returns ASYNC
            (
                testing_returns,
                external_returns,
            ) = await self._calculate_testing_returns_async(task.key)
            total_returns = testing_returns + external_returns

            # Format row
            row = self._format_task_row(
                task,
                ttm,
                quarter.name,
                tail,
                devlt,
                ttd,
                ttd_quarter,
                pause,
                ttd_pause,
                discovery_backlog_days,
                ready_for_dev_days,
                testing_returns,
                external_returns,
                total_returns,
            )

            return row

        except Exception as e:
            print(f"Error processing task {task.key}: {e}")
            return None

    async def generate_csv_async(self, output_path: str) -> str:
        """Async version of CSV generation."""
        try:
            import csv
            from pathlib import Path

            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Collect CSV rows data asynchronously
            rows = await self._collect_csv_rows_async()

            # Create CSV with data
            with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = [
                    "Ключ задачи",
                    "Название",
                    "Автор",
                    "Команда",
                    "Квартал",
                    "TTM",
                    "Пауза",
                    "Tail",
                    "DevLT",
                    "TTD",
                    "TTD Pause",
                    "Discovery backlog (дни)",
                    "Готова к разработке (дни)",
                    "Возвраты с Testing",
                    "Возвраты с Внешний тест",
                    "Всего возвратов",
                    "Квартал TTD",
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            print(f"📄 TTM Details CSV generated: {output_path} with {len(rows)} rows")
            return output_path

        except Exception as e:
            print(f"❌ Failed to generate TTM Details CSV: {e}")
            raise


async def run_async_profile():
    """Run async profiling with detailed timing."""
    print("🚀 Async TTM Details Report Profiling")
    print("=" * 60)

    with SessionLocal() as db:
        # Create async generator
        generator = AsyncTTMDetailsReportGenerator(db=db, max_workers=50)

        # Time the generation
        start_time = time.time()
        result_path = await generator.generate_csv_async(
            "data/reports/async_ttm_details.csv"
        )
        total_time = time.time() - start_time

        print(f"\n⏱️  Total async generation time: {total_time:.2f}s")
        print(f"📄 Report generated: {result_path}")

        # Show cache statistics
        with generator.cache_lock:
            cache_size = len(generator.testing_returns_cache)
            print(f"💾 Testing returns cache size: {cache_size}")

        return result_path, total_time


async def main():
    """Main async function."""
    print("🚀 Async TTM Details Report Generation")
    print("=" * 60)

    # Run async version only
    async_result, async_time = await run_async_profile()

    print(f"\n⏱️  Async generation time: {async_time:.2f}s")
    print(f"📄 Report generated: {async_result}")


if __name__ == "__main__":
    asyncio.run(main())
