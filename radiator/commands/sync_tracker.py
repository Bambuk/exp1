"""Command for syncing data from Yandex Tracker."""

# Completely disable SQLAlchemy logging BEFORE any imports
import os
import sys

# Set environment variables to disable SQLAlchemy logging
os.environ["SQLALCHEMY_WARN_20"] = "false"
os.environ["SQLALCHEMY_SILENCE_UBER_WARNING"] = "1"

import contextlib

# Redirect stdout/stderr to suppress SQL logs
import io

# Completely disable all logging
import logging

# Disable SQLAlchemy verbose logging, but keep ERROR level
logging.getLogger("sqlalchemy").setLevel(logging.CRITICAL)
logging.getLogger("sqlalchemy.engine").setLevel(logging.CRITICAL)
logging.getLogger("sqlalchemy.pool").setLevel(logging.CRITICAL)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.CRITICAL)
logging.getLogger("sqlalchemy.orm").setLevel(logging.CRITICAL)

# Also disable any other database-related loggers
logging.getLogger("alembic").setLevel(logging.CRITICAL)
logging.getLogger("psycopg2").setLevel(logging.CRITICAL)

# Configure root logger: show only CRITICAL, but our app logger will show ERROR
logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Set radiator logger to ERROR level to show errors but not info/debug
logging.getLogger("radiator").setLevel(logging.ERROR)

import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from tqdm import tqdm

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.core.config import settings, with_default_limit
from radiator.core.database import SessionLocal
from radiator.core.logging import logger
from radiator.core.single_instance import SingleInstance
from radiator.models.tracker import TrackerSyncLog, TrackerTask, TrackerTaskHistory

# CRUD operations removed - using direct SQLAlchemy queries
from radiator.services.tracker_service import tracker_service
from radiator.utils.fields_loader import load_fields_list


class TrackerSyncCommand:
    """Command for syncing tracker data."""

    def __init__(self):
        self.db = SessionLocal()
        self.sync_log: Optional[TrackerSyncLog] = None
        try:
            self.fields = load_fields_list()
        except FileNotFoundError:
            logger.warning("Fields file not found, using all fields")
            self.fields = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()

    def create_sync_log(self) -> TrackerSyncLog:
        """Create new sync log entry."""
        sync_log = TrackerSyncLog(
            sync_started_at=datetime.now(timezone.utc), status="running"
        )
        self.db.add(sync_log)
        self.db.commit()
        self.db.refresh(sync_log)
        return sync_log

    def update_sync_log(self, **kwargs):
        """Update sync log with new data."""
        if self.sync_log:
            for key, value in kwargs.items():
                if hasattr(self.sync_log, key):
                    setattr(self.sync_log, key, value)
            self.db.commit()

    def get_tasks_to_sync(
        self,
        filters: Dict[str, Any] = None,
        limit: int = None,
        show_progress: bool = False,
    ) -> List[Any]:
        """
        Get list of tasks to sync using filters.

        Args:
            filters: Custom filters for getting tasks
            limit: Maximum number of tasks to sync (uses default from config if None)
            show_progress: Whether to show loading progress messages

        Returns:
            List of task data (either IDs or full task objects) to sync
        """
        try:
            # Use default limit from config if not provided
            if limit is None:
                limit = (
                    settings.MAX_UNLIMITED_LIMIT
                )  # Use unlimited for sync by default

            logger.info(f"Getting tasks using filters: {filters}")

            # Create progress bar if needed
            progress_bar = None
            if show_progress:
                progress_bar = tqdm(
                    desc="📥 Загрузка задач", unit="задача", unit_scale=False
                )

            def update_progress(count):
                if progress_bar is not None:
                    progress_bar.n = count
                    progress_bar.refresh()

            task_data = tracker_service.get_tasks_by_filter_with_data(
                filters,
                limit=limit,
                fields=self.fields,
                progress_callback=update_progress if show_progress else None,
            )

            if progress_bar is not None:
                progress_bar.close()

            logger.info(f"Found {len(task_data)} tasks to sync")
            return task_data

        except Exception as e:
            logger.error(f"Failed to get tasks to sync: {e}")
            if progress_bar is not None:
                progress_bar.close()
            return []

    def sync_tasks(
        self, task_data: List[Any]
    ) -> tuple[Dict[str, int], List[tuple[str, Optional[Dict[str, Any]]]], int]:
        """Sync tasks data from tracker."""
        logger.info(f"Starting sync for {len(task_data)} tasks")

        valid_tasks = []
        tasks_data = []
        api_errors = 0  # Count API errors

        # Check if we have full task data or just IDs
        if task_data and isinstance(task_data[0], dict) and "id" in task_data[0]:
            # We have full task data from search - use it directly
            logger.info("📥 Используем данные задач из поиска...")
            for task_obj in task_data:
                if task_obj and isinstance(task_obj, dict):
                    task_info = tracker_service.extract_task_data(task_obj)
                    valid_tasks.append(task_info)
                    tasks_data.append((task_obj["id"], task_obj))
                else:
                    logger.warning(f"Failed to process task data: {task_obj}")
                    api_errors += 1  # Count as API error
        else:
            # We have only IDs - use get_tasks_batch for backwards compatibility
            logger.info("📥 Получаем данные задач из Tracker...")
            task_ids = task_data
            # Use expand=links to get task links along with task data
            tasks_data = tracker_service.get_tasks_batch(task_ids, expand=["links"])

            # Process tasks data
            logger.info("🔄 Обрабатываем полученные данные...")
            for task_id, task_obj in tasks_data:
                if task_obj:
                    task_info = tracker_service.extract_task_data(task_obj)
                    valid_tasks.append(task_info)
                else:
                    logger.warning(f"Failed to get data for task {task_id}")
                    api_errors += 1  # Count as API error

        if not valid_tasks:
            logger.warning("No valid tasks data received")
            return {"created": 0, "updated": 0}, tasks_data, api_errors

        # Save tasks to database
        logger.info(f"💾 Сохраняем {len(valid_tasks)} задач в базу данных...")
        result = self._bulk_create_or_update_tasks(valid_tasks)
        logger.info(f"✅ Задачи синхронизированы: {result}")

        return result, tasks_data, api_errors

    def _bulk_create_or_update_tasks(
        self, tasks_data: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Bulk create or update tasks in database."""
        created = 0
        updated = 0

        # Дедупликация: оставляем только последнее вхождение каждого tracker_id
        # Это решает проблему, когда API возвращает дубликаты из-за обновления во время пагинации
        unique_tasks = {}
        for task_data in tasks_data:
            tracker_id = task_data.get("tracker_id")
            if tracker_id:
                # Берем последнее вхождение (более свежие данные)
                unique_tasks[tracker_id] = task_data

        logger.info(
            f"📊 Обрабатываем {len(tasks_data)} задач, после дедупликации: {len(unique_tasks)}"
        )

        # Обрабатываем только уникальные задачи
        for task_data in unique_tasks.values():
            # Check if task exists
            existing_task = (
                self.db.query(TrackerTask)
                .filter(TrackerTask.tracker_id == task_data.get("tracker_id"))
                .first()
            )

            if existing_task:
                # Update existing task
                for key, value in task_data.items():
                    if hasattr(existing_task, key):
                        setattr(existing_task, key, value)
                existing_task.last_sync_at = datetime.now(timezone.utc)
                updated += 1
            else:
                # Create new task
                new_task = TrackerTask(**task_data)
                new_task.last_sync_at = datetime.now(timezone.utc)
                self.db.add(new_task)
                created += 1

        logger.info("💾 Сохранение задач в базу данных...")
        self.db.commit()
        logger.info("✅ Задачи успешно сохранены")
        return {"created": created, "updated": updated}

    def sync_task_history(
        self,
        task_data: List[Any],
        tasks_data: List[tuple[str, Optional[Dict[str, Any]]]],
        force_full_history: bool = False,
    ) -> tuple[int, int, int]:
        """Sync task history data."""
        # Extract task IDs from task_data
        if task_data and isinstance(task_data[0], dict) and "id" in task_data[0]:
            # We have full task data - extract IDs
            task_ids = [task["id"] for task in task_data if task and "id" in task]
        else:
            # We have only IDs
            task_ids = task_data

        logger.info(f"📚 Начинаем синхронизацию истории для {len(task_ids)} задач")
        logger.info(f"🔍 ID задач для истории: {task_ids}")

        # Get changelogs with progress indication
        logger.info("📥 Получаем данные истории из Tracker...")
        start_time = datetime.now()
        changelogs_data = tracker_service.get_changelogs_batch(task_ids)
        load_time = datetime.now() - start_time
        logger.info(
            f"⏱️ Загрузка истории завершена за {load_time.total_seconds():.1f} секунд"
        )
        logger.info(f"🔍 Получено данных истории: {len(changelogs_data)} задач")

        # Use already loaded task data for initial status handling
        logger.info("🔄 Используем уже загруженные данные задач...")
        tasks_dict = {
            task_id: task_data for task_id, task_data in tasks_data if task_data
        }

        total_history_entries = 0
        tasks_with_history = 0
        api_errors = 0  # Count API errors

        # Process history with progress bar
        logger.info("💾 Обрабатываем и сохраняем историю в базу данных...")
        failed_tasks = []
        with tqdm(
            total=len(changelogs_data), desc="💾 Обработка истории", unit="задача"
        ) as pbar:
            for i, (task_id, changelog) in enumerate(changelogs_data, 1):
                try:
                    # Check if changelog is None (API error)
                    if changelog is None:
                        api_errors += 1
                        logger.warning(
                            f"API error for task {task_id} - no changelog data"
                        )
                        pbar.update(1)
                        continue

                    history_entries, has_history = self._process_single_task_history(
                        task_id, changelog, tasks_dict, force_full_history
                    )
                    total_history_entries += history_entries
                    if has_history:
                        tasks_with_history += 1

                    # Update progress bar
                    task_key = tasks_dict.get(task_id, {}).get(
                        "key", task_id[:8] + "..."
                    )
                    pbar.set_postfix({"task": task_key})
                    pbar.update(1)
                except Exception as e:
                    task_key = tasks_dict.get(task_id, {}).get("key", task_id)
                    error_msg = f"Ошибка обработки истории задачи {task_key} (ID: {task_id}): {type(e).__name__}: {str(e)}"
                    logger.error(f"❌ {error_msg}")
                    logger.error(f"📍 Stacktrace: {traceback.format_exc()}")
                    failed_tasks.append((task_key, str(e)))
                    api_errors += 1  # Count as API error
                    pbar.update(1)
                    # Продолжаем обработку остальных задач

        if failed_tasks:
            logger.warning(
                f"⚠️ Не удалось обработать историю для {len(failed_tasks)} задач:"
            )
            for task_key, error in failed_tasks[:10]:  # Показываем первые 10
                logger.warning(f"  - {task_key}: {error}")
            if len(failed_tasks) > 10:
                logger.warning(f"  ... и ещё {len(failed_tasks) - 10} задач")

        logger.info(
            f"✅ История синхронизирована: {total_history_entries} записей создано для {tasks_with_history} задач"
        )
        return total_history_entries, tasks_with_history, api_errors

    def _process_single_task_history(
        self,
        task_id: str,
        changelog: List[Dict[str, Any]],
        tasks_dict: Dict[str, Any],
        force_full_history: bool = False,
    ) -> tuple[int, bool]:
        """Process history for a single task. Returns (history_entries_count, has_history)."""
        # Get task from database
        db_task = (
            self.db.query(TrackerTask).filter(TrackerTask.tracker_id == task_id).first()
        )
        if not db_task:
            logger.warning(
                f"⚠️ Задача {task_id} не найдена в базе данных, пропускаем историю"
            )
            return 0, False

        # Get task data for initial status handling
        task_data = tasks_dict.get(task_id)
        if not task_data:
            logger.warning(f"⚠️ Данные задачи {task_id} не найдены, пропускаем историю")
            return 0, False

        # Check if we should use incremental update
        if db_task.last_changelog_id and not force_full_history:
            # INCREMENTAL MODE: Use incremental update
            logger.debug(f"Using incremental history update for task {task_id}")
            added_count = self._incremental_history_update(
                db_task.id, changelog, db_task
            )

            return added_count, added_count > 0
        else:
            # FULL MODE: First time sync for this task or forced full sync
            if force_full_history:
                logger.debug(f"Using forced full history update for task {task_id}")
            else:
                logger.debug(
                    f"Using full history update for task {task_id} (first time)"
                )

            # Extract task data
            task_info = tracker_service.extract_task_data(task_data)

            # Extract status history with initial status support
            task_key = (
                db_task.key if hasattr(db_task, "key") and db_task.key else task_id
            )
            status_history = tracker_service.extract_status_history_with_initial_status(
                changelog, task_info, task_key
            )
            if not status_history:
                return 0, False

            # Delete existing history for this task to ensure clean slate
            self.db.query(TrackerTaskHistory).filter(
                TrackerTaskHistory.task_id == db_task.id
            ).delete()

            # Prepare history data with duplicate prevention
            history_data = self._prepare_history_data(
                status_history, db_task.id, task_id
            )

            # Save history
            if history_data:
                created_count = self._bulk_create_history(
                    history_data, db_task, changelog
                )

                return created_count, True

            return 0, False

    def _prepare_history_data(
        self, status_history: List[Dict[str, Any]], db_task_id: int, task_id: str
    ) -> List[Dict[str, Any]]:
        """Prepare history data for database insertion."""
        history_data = []
        for entry in status_history:
            # Additional validation to prevent duplicates
            if entry.get("start_date") and entry.get("status"):
                history_entry = {
                    "task_id": db_task_id,
                    "tracker_id": task_id,
                    "status": entry["status"],
                    "status_display": entry["status_display"],
                    "start_date": entry["start_date"],
                    "end_date": entry.get("end_date"),
                }
                history_data.append(history_entry)
        return history_data

    def _bulk_create_history(
        self,
        history_data: List[Dict[str, Any]],
        db_task: TrackerTask,
        changelog: List[Dict[str, Any]],
    ) -> int:
        """Bulk create history entries in database and update last_changelog_id atomically."""
        created_count = 0
        for entry in history_data:
            history_entry = TrackerTaskHistory(**entry)
            self.db.add(history_entry)
            created_count += 1

        # Update last_changelog_id in the same transaction
        if changelog:
            db_task.last_changelog_id = changelog[-1]["id"]
            logger.debug(
                f"Set last_changelog_id to {changelog[-1]['id']} for task {db_task.tracker_id}"
            )

        logger.debug("💾 Сохранение истории задачи в базу данных...")
        self.db.commit()
        logger.debug("✅ История задачи сохранена")
        return created_count

    def _incremental_history_update(
        self,
        task_id: int,
        new_changelog_entries: List[Dict[str, Any]],
        db_task: TrackerTask,
    ) -> int:
        """
        Append new history entries without deleting existing ones.

        This method is used for incremental updates when last_changelog_id exists.
        It only adds new entries and updates the end_date of the previous last entry.

        Args:
            task_id: Database ID of the task
            new_changelog_entries: New changelog entries from API

        Returns:
            Number of new history entries added
        """
        if not new_changelog_entries:
            return 0

        # Extract status changes from new changelog entries
        # Use simple extraction for incremental updates (no initial status handling)
        new_status_changes = tracker_service.extract_status_history(
            new_changelog_entries, f"task_{task_id}"
        )

        if not new_status_changes:
            logger.debug(
                f"No status changes found in {len(new_changelog_entries)} changelog entries for task {task_id}"
            )
            return 0

        logger.debug(
            f"Found {len(new_status_changes)} new status changes for task {task_id}"
        )

        # Get the current last history entry for this task
        last_entry = (
            self.db.query(TrackerTaskHistory)
            .filter(TrackerTaskHistory.task_id == task_id)
            .order_by(TrackerTaskHistory.start_date.desc())
            .first()
        )

        # Update end_date of previous last entry if needed
        if last_entry and last_entry.end_date is None and new_status_changes:
            last_entry.end_date = new_status_changes[0]["start_date"]
            logger.debug(f"Updated end_date of previous last entry for task {task_id}")

        # Prepare new history entries with duplicate check
        added_count = 0
        for entry in new_status_changes:
            # Check if this exact entry already exists (more precise check)
            existing = (
                self.db.query(TrackerTaskHistory)
                .filter(
                    TrackerTaskHistory.task_id == task_id,
                    TrackerTaskHistory.status == entry["status"],
                    TrackerTaskHistory.status_display == entry["status_display"],
                    TrackerTaskHistory.start_date == entry["start_date"],
                )
                .first()
            )

            if not existing:
                # Create new history entry
                history_entry = TrackerTaskHistory(
                    task_id=task_id,
                    tracker_id=new_changelog_entries[0].get("issue", {}).get("id", ""),
                    status=entry["status"],
                    status_display=entry["status_display"],
                    start_date=entry["start_date"],
                    end_date=entry.get("end_date"),
                )
                self.db.add(history_entry)
                added_count += 1
                logger.debug(
                    f"Added new history entry: {entry['status']} at {entry['start_date']}"
                )
            else:
                logger.debug(
                    f"Skipped duplicate history entry: {entry['status']} at {entry['start_date']}"
                )

        if added_count > 0:
            # Update last_changelog_id in the same transaction
            if new_changelog_entries:
                db_task.last_changelog_id = new_changelog_entries[-1]["id"]
                logger.debug(
                    f"Updated last_changelog_id to {new_changelog_entries[-1]['id']} for task {db_task.tracker_id}"
                )

            logger.debug("💾 Сохранение инкрементальной истории в базу данных...")
            self.db.commit()
            logger.debug(
                f"✅ Сохранено {added_count} новых записей истории для задачи {task_id}"
            )

        return added_count

    def _cleanup_duplicate_history(self) -> int:
        """Clean up duplicate history entries using efficient SQL."""
        from sqlalchemy import text

        # Use CTE with ROW_NUMBER to find duplicates, keeping oldest record
        query = text(
            """
            WITH duplicates AS (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY task_id, status, start_date
                           ORDER BY created_at ASC
                       ) as row_num
                FROM tracker_task_history
            )
            DELETE FROM tracker_task_history
            WHERE id IN (
                SELECT id FROM duplicates WHERE row_num > 1
            )
            RETURNING id
        """
        )

        try:
            result = self.db.execute(query)
            deleted_count = result.rowcount
            self.db.commit()

            if deleted_count > 0:
                logger.info(f"✅ Очищено {deleted_count} дубликатов истории")

            return deleted_count

        except Exception as e:
            logger.error(f"Ошибка при очистке дубликатов: {e}")
            self.db.rollback()
            return 0

    def run(
        self,
        filters: Dict[str, Any] = None,
        limit: int = None,
        skip_history: bool = False,
        force_full_history: bool = False,
    ):
        """Run the sync command."""
        try:
            # Debug: log all parameters
            logger.debug(f"🔍 DEBUG: run() вызван с параметрами:")
            logger.debug(f"   filters: {filters}")
            logger.debug(f"   limit: {limit}")
            logger.debug(f"   skip_history: {skip_history}")
            logger.debug(f"   force_full_history: {force_full_history}")

            # Create sync log
            self.sync_log = self.create_sync_log()
            logger.info(f"Started sync operation: {self.sync_log.id}")
            logger.info("Sync mode: filters and limit")
            if skip_history:
                logger.info("History sync disabled")

            # Get tasks to sync
            logger.info(f"🚀 Начинаем синхронизацию...")
            logger.info(f"   📋 Фильтр: {filters}")
            logger.info(f"   🎯 Лимит: {limit} задач")

            task_data = self.get_tasks_to_sync(filters, limit, show_progress=True)
            if not task_data:
                logger.error(f"❌ Не найдено задач для синхронизации")
                self.update_sync_log(
                    status="failed",
                    sync_completed_at=datetime.now(timezone.utc),
                    error_details="No tasks found to sync",
                )
                return False

            logger.info(f"✅ Найдено {len(task_data)} задач для синхронизации")

            self.update_sync_log(tasks_processed=len(task_data))

            # Overall progress bar for the entire sync process
            total_steps = (
                2 if skip_history else 3
            )  # tasks + history + cleanup OR just tasks
            with tqdm(
                total=total_steps, desc="🚀 Общий прогресс", unit="этап"
            ) as main_pbar:
                # Sync tasks with progress indication
                logger.info("🔄 Начинаем синхронизацию задач...")
                tasks_result, tasks_data, tasks_api_errors = self.sync_tasks(task_data)
                main_pbar.update(1)
                logger.debug(f"✅ Синхронизация задач завершена: {tasks_result}")
                self.update_sync_log(
                    tasks_created=tasks_result["created"],
                    tasks_updated=tasks_result["updated"],
                )

                # Sync history (if not skipped)
                history_entries = 0
                tasks_with_history = 0
                history_api_errors = 0
                if skip_history:
                    logger.info("⏭️ Пропускаем синхронизацию истории по запросу")
                    main_pbar.update(1)  # Skip history step
                else:
                    logger.info("📚 Синхронизация истории включена, начинаем...")
                    try:
                        (
                            history_entries,
                            tasks_with_history,
                            history_api_errors,
                        ) = self.sync_task_history(
                            task_data, tasks_data, force_full_history
                        )
                        logger.info(
                            f"📚 Синхронизация истории завершена: {history_entries} записей"
                        )
                        main_pbar.update(1)

                        # Clean up any duplicates that might have been created
                        if history_entries > 0:
                            logger.info("🧹 Очищаем возможные дубликаты в истории...")
                            cleaned_count = self._cleanup_duplicate_history()
                            if cleaned_count > 0:
                                logger.info(
                                    f"🧹 Очищено {cleaned_count} дублирующихся записей"
                                )
                            else:
                                logger.info("✅ Дубликатов не найдено")
                            main_pbar.update(1)
                        else:
                            main_pbar.update(1)  # No cleanup needed
                    except Exception as e:
                        logger.error(f"❌ Ошибка при синхронизации истории: {e}")
                        import traceback

                        logger.error(f"Traceback: {traceback.format_exc()}")
                        history_entries = 0
                        tasks_with_history = 0
                        main_pbar.update(2)  # Skip remaining steps

            # Calculate total API errors
            total_api_errors = tasks_api_errors + history_api_errors

            # Mark sync as completed
            logger.info("💾 Сохранение результатов синхронизации в базу данных...")
            self.update_sync_log(
                status="completed",
                sync_completed_at=datetime.now(timezone.utc),
                errors_count=total_api_errors,
            )
            logger.info("✅ Результаты успешно сохранены")

            # Print final summary to stdout (works even with disabled logging)
            print(f"\n🎉 Синхронизация завершена успешно!")
            print(f"   📝 Создано: {tasks_result['created']} задач")
            print(f"   🔄 Обновлено: {tasks_result['updated']} задач")
            print(f"   📚 Записей истории: {history_entries}")
            print(f"   📋 Задач с историей: {tasks_with_history}")
            if total_api_errors > 0:
                print(f"   ❌ Ошибок API: {total_api_errors}")
            else:
                print(f"   ✅ Ошибок API: 0")

            logger.info(f"🎉 Синхронизация завершена успешно!")
            logger.info(f"   📝 Создано: {tasks_result['created']} задач")
            logger.info(f"   🔄 Обновлено: {tasks_result['updated']} задач")
            logger.info(f"   📚 Записей истории: {history_entries}")
            logger.info(f"   📋 Задач с историей: {tasks_with_history}")
            if total_api_errors > 0:
                logger.info(f"   ❌ Ошибок API: {total_api_errors}")
            else:
                logger.info(f"   ✅ Ошибок API: 0")
            return True

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            if self.sync_log:
                self.update_sync_log(
                    status="failed",
                    sync_completed_at=datetime.now(timezone.utc),
                    error_details=str(e),
                )
            return False


def main():
    """Main entry point for the sync command."""
    import argparse

    # Check for single instance
    try:
        with SingleInstance("sync_tracker"):
            logger.info("Sync tracker instance lock acquired")
            _run_sync()
    except RuntimeError as e:
        logger.error(f"Failed to start sync tracker: {e}")
        sys.exit(1)


def _run_sync():
    """Run the actual sync operation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Sync data from Yandex Tracker with pagination support",
        epilog="""
Note: Yandex Tracker API returns maximum 50 records per page.
The command automatically handles pagination to retrieve the requested number of tasks.
Maximum limit is 10000 tasks per sync operation.
        """,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=f"Maximum number of tasks to sync (default: {settings.DEFAULT_LARGE_LIMIT})",
    )
    parser.add_argument(
        "--filter",
        type=str,
        help="Filter string for task selection (passed directly to tracker)",
    )

    parser.add_argument(
        "--skip-history",
        action="store_true",
        help="Skip syncing task history (faster sync for testing)",
    )
    parser.add_argument(
        "--force-full-history",
        action="store_true",
        help="Force full history sync for all tasks (ignore last_changelog_id)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Move all logic to _run_sync function
    _run_sync_logic(args)


def _run_sync_logic(args):
    """Run the actual sync logic."""
    if args.debug:
        logger.setLevel("DEBUG")

    # Check required environment variables
    if not settings.TRACKER_API_TOKEN:
        logger.error("TRACKER_API_TOKEN environment variable is required")
        sys.exit(1)

    if not settings.TRACKER_ORG_ID:
        logger.error("TRACKER_ORG_ID environment variable is required")
        sys.exit(1)

    # Build filters
    filters = {}
    if args.filter:
        # Pass the filter string directly as a query
        filters["query"] = args.filter

    # Run sync
    logger.info("🚀 Запускаем синхронизацию...")
    logger.debug(
        f"🔍 Параметры: filters={filters}, limit={args.limit}, skip_history={args.skip_history}, force_full_history={args.force_full_history}"
    )

    with TrackerSyncCommand() as sync_cmd:
        success = sync_cmd.run(
            filters=filters,
            limit=args.limit,
            skip_history=args.skip_history,
            force_full_history=args.force_full_history,
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
