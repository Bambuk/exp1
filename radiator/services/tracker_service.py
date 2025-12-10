"""Service for Yandex Tracker API integration."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests
from tqdm import tqdm

from radiator.core.config import log_limit_info, settings, with_default_limit_method
from radiator.core.logging import logger

# Constants for status field handling
STATUS_FIELD_ID = "status"
LEGACY_PRODTEAM_FIELD = "63515d47fe387b7ce7b9fc55--prodteam"
FULLSTACK_PRODTEAM_FIELD = "6361307d94f52e42ae308615--prodteam"


class TrackerAPIService:
    """Service for interacting with Yandex Tracker API."""

    def __init__(self):
        self.headers = {
            "Authorization": f"OAuth {settings.TRACKER_API_TOKEN}",
            "X-Org-ID": settings.TRACKER_ORG_ID,
            "Content-Type": "application/json",
        }
        self.base_url = settings.TRACKER_BASE_URL
        self.request_delay = settings.TRACKER_REQUEST_DELAY
        self.max_workers = settings.TRACKER_MAX_WORKERS

    def _make_request(
        self, url: str, method: str = "GET", **kwargs
    ) -> requests.Response:
        """Make HTTP request with error handling and rate limiting."""
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            time.sleep(self.request_delay)  # Rate limiting
            return response
        except (
            requests.exceptions.RequestException,
            requests.exceptions.HTTPError,
        ) as e:
            # Упрощенное логирование ошибок API
            status_code = None
            response_text = None
            response_headers = None

            # Try to get response info from different exception types
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                response_text = e.response.text
                response_headers = dict(e.response.headers)
            elif isinstance(e, requests.exceptions.HTTPError):
                # For HTTPError, the response is stored differently
                status_code = (
                    e.response.status_code
                    if hasattr(e, "response") and e.response
                    else None
                )
                response_text = (
                    e.response.text if hasattr(e, "response") and e.response else None
                )
                response_headers = (
                    dict(e.response.headers)
                    if hasattr(e, "response") and e.response
                    else None
                )

            if status_code == 422:
                logger.error(f"🚫 API Error 422: Неправильный синтаксис запроса")
                logger.error(f"   URL: {url}")
                logger.error(f"   Детали: {e}")
            elif status_code == 403:
                logger.error(f"🚫 API Error 403: Нет доступа (проверьте токен и права)")
                logger.error(f"   URL: {url}")
            elif status_code == 401:
                logger.error(f"🚫 API Error 401: Неавторизован (проверьте токен)")
                logger.error(f"   URL: {url}")
            elif status_code == 429:
                logger.warning(
                    f"⚠️ API Error 429: Превышен лимит запросов, ждем 60 секунд..."
                )
                logger.warning(f"   URL: {url}")
                time.sleep(60)  # Ждем 60 секунд при ошибке 429
                # Попробуем повторить запрос
                try:
                    response = requests.request(
                        method, url, headers=self.headers, **kwargs
                    )
                    response.raise_for_status()
                    time.sleep(self.request_delay)
                    return response
                except Exception as retry_e:
                    logger.error(f"🚫 Повторный запрос также failed: {retry_e}")
                    raise e
            elif status_code == 400:
                logger.error(f"🚫 API Error 400: Bad Request")
                logger.error(f"   URL: {url}")
                logger.error(f"   Full error: {e}")
                if response_text:
                    logger.error(f"   Response text: {response_text}")
                if response_headers:
                    logger.error(f"   Response headers: {response_headers}")
            else:
                logger.error(f"🚫 API Error {status_code or 'Unknown'}: {e}")
                logger.error(f"   URL: {url}")

            # Log full traceback for debugging
            import traceback

            logger.error(f"📍 Request details: method={method}, url={url}")
            if "params" in kwargs:
                logger.error(f"📍 Request params: {kwargs['params']}")
            if "json" in kwargs:
                logger.error(f"📍 Request json: {kwargs['json']}")
            logger.error(f"📍 Stacktrace: {traceback.format_exc()}")

            raise

    def get_task(
        self, task_id: str, expand: List[str] = None, fields: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get task details by ID."""
        try:
            url = f"{self.base_url}issues/{task_id}"
            params = {}
            if expand:
                params["expand"] = ",".join(expand)
            if fields:
                params["fields"] = ",".join(fields)
            response = self._make_request(url, params=params)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None

    def get_task_changelog(self, task_id: str) -> List[Dict[str, Any]]:
        """Get task changelog with pagination support."""
        all_data = []
        page = 1
        per_page = 50  # API default and maximum per page
        next_page_id = (
            None  # Local variable to avoid race conditions in parallel execution
        )

        while True:
            try:
                url = f"{self.base_url}issues/{task_id}/changelog"
                params = {
                    "perPage": per_page,
                    "type": "IssueWorkflow",  # Только изменения статусов
                }

                # Если это не первая страница, добавляем параметр id для следующей страницы
                if page > 1 and next_page_id:
                    params["id"] = next_page_id

                response = self._make_request(url, params=params)
                page_data = response.json()

                if not page_data:
                    break

                all_data.extend(page_data)

                # Check if there's a next page using Link header
                link_header = response.headers.get("Link", "")
                if 'rel="next"' in link_header:
                    # Extract the id parameter from the next page URL
                    import re

                    match = re.search(r"id=([^&]+)", link_header)
                    if match:
                        next_page_id = match.group(1)
                        page += 1
                    else:
                        break
                else:
                    # No next page, we're done
                    break

                # Safety check to prevent infinite loops
                if page > 100:  # Maximum 100 pages
                    break

            except Exception as e:
                import traceback

                error_details = {
                    "task_id": task_id,
                    "page": page,
                    "per_page": per_page,
                    "next_page_id": next_page_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "total_data_so_far": len(all_data),
                }
                logger.error(
                    f"❌ Ошибка получения истории для задачи {task_id} на странице {page}: {type(e).__name__}: {e}"
                )
                logger.error(f"📍 Error details: {error_details}")
                logger.error(f"📍 Stacktrace: {traceback.format_exc()}")
                break

        return all_data

    def get_changelog_from_id(
        self, task_id: str, last_changelog_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get changelog entries after specified ID for incremental sync.

        Uses the 'id' parameter to fetch only new entries added after last_changelog_id.
        This is much more efficient than fetching the full changelog.

        Args:
            task_id: Task ID in Tracker
            last_changelog_id: ID of the last processed changelog entry

        Returns:
            List of new changelog entries (only those added after last_changelog_id)
        """
        all_data = []
        per_page = 50  # API default and maximum per page
        next_page_id = last_changelog_id  # Start from the last known ID

        logger.debug(
            f"Getting incremental changelog for task {task_id} from ID {last_changelog_id}"
        )

        while True:
            try:
                url = f"{self.base_url}issues/{task_id}/changelog"
                params = {
                    "perPage": per_page,
                    "type": "IssueWorkflow",  # Only status changes
                    "id": next_page_id,  # Get entries after this ID
                }

                response = self._make_request(url, params=params)
                page_data = response.json()

                if not page_data:
                    # No more data available
                    break

                all_data.extend(page_data)

                # Check if there's a next page using Link header
                link_header = response.headers.get("Link", "")
                if 'rel="next"' in link_header:
                    # Extract the id parameter from the next page URL
                    import re

                    match = re.search(r"id=([^&]+)", link_header)
                    if match:
                        next_page_id = match.group(1)
                    else:
                        break
                else:
                    # No next page, we're done
                    break

                # Safety check to prevent infinite loops
                if len(all_data) > 1000:  # Reasonable limit for incremental updates
                    logger.warning(
                        f"Stopping incremental changelog fetch at {len(all_data)} entries for task {task_id}"
                    )
                    break

            except Exception as e:
                import traceback

                error_details = {
                    "task_id": task_id,
                    "last_changelog_id": last_changelog_id,
                    "next_page_id": next_page_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "total_data_so_far": len(all_data),
                }
                logger.error(
                    f"❌ Ошибка получения инкрементальной истории для задачи {task_id}: {type(e).__name__}: {e}"
                )
                logger.error(f"📍 Error details: {error_details}")
                logger.error(f"📍 Stacktrace: {traceback.format_exc()}")
                break

        logger.debug(
            f"Retrieved {len(all_data)} new changelog entries for task {task_id}"
        )
        return all_data

    def get_tasks_batch(
        self, task_ids: List[str], expand: List[str] = None
    ) -> List[Tuple[str, Optional[Dict[str, Any]]]]:
        """Get multiple tasks in parallel with progress bar."""

        results = []
        total_tasks = len(task_ids)

        # Pre-allocate results list to maintain order
        results = [None] * total_tasks

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks and store futures with their indices
            future_to_index = {}
            for i, task_id in enumerate(task_ids):
                future = executor.submit(self.get_task, task_id, expand)
                future_to_index[future] = i

            # Use tqdm for real-time progress indication
            with tqdm(
                total=total_tasks, desc="📥 Загрузка задач", unit="задача"
            ) as pbar:
                for future in as_completed(future_to_index):
                    index = future_to_index[future]
                    task_id = task_ids[index]

                    try:
                        task_data = future.result()
                        results[index] = (task_id, task_data)
                        pbar.set_postfix({"task": task_id[:8] + "..."})
                    except Exception as e:
                        import traceback

                        error_details = {
                            "task_id": task_id,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "index": index,
                            "total_tasks": total_tasks,
                        }
                        logger.error(
                            f"❌ Failed to get task {task_id}: {type(e).__name__}: {e}"
                        )
                        logger.error(f"📍 Error details: {error_details}")
                        logger.error(f"📍 Stacktrace: {traceback.format_exc()}")
                        results[index] = (task_id, None)

                    pbar.update(1)

        return results

    def get_changelogs_batch(
        self, task_ids: List[str]
    ) -> List[Tuple[str, List[Dict[str, Any]]]]:
        """Get changelogs for multiple tasks in parallel with progress bar."""

        total_tasks = len(task_ids)

        # Pre-allocate results list to maintain order
        results = [None] * total_tasks

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks and store futures with their indices
            future_to_index = {}
            for i, task_id in enumerate(task_ids):
                future = executor.submit(self.get_task_changelog, task_id)
                future_to_index[future] = i

            # Use tqdm for real-time progress indication
            errors = []
            with tqdm(
                total=total_tasks, desc="📚 Загрузка истории", unit="задача"
            ) as pbar:
                for future in as_completed(future_to_index):
                    index = future_to_index[future]
                    task_id = task_ids[index]

                    try:
                        changelog_data = future.result()
                        results[index] = (task_id, changelog_data)
                        pbar.set_postfix({"task": task_id[:8] + "..."})
                    except Exception as e:
                        import traceback

                        error_details = {
                            "task_id": task_id,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "index": index,
                            "total_tasks": total_tasks,
                        }
                        # Store error for later logging to avoid breaking progress bar
                        error_details["stacktrace"] = traceback.format_exc()
                        errors.append(error_details)
                        results[index] = (task_id, [])

                    pbar.update(1)

            # Log errors after progress bar is complete
            for error in errors:
                logger.error(
                    f"❌ Failed to get changelog for task {error['task_id']}: {error['error_type']}: {error['error_message']}"
                )
                logger.error(f"📍 Error details: {error}")
                logger.error(f"📍 Stacktrace: {error['stacktrace']}")

        return results

    def extract_task_data(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data from task response."""
        if not task or not isinstance(task, dict):
            logger.warning(f"Invalid task data: {task}")
            return {
                "tracker_id": "",
                "key": "",
                "summary": "",
                "description": "",
                "status": "",
                "author": "",
                "assignee": "",
                "business_client": "",
                "customer": "",
                "team": "",
                "prodteam": "",
                "profit_forecast": "",
                "task_updated_at": None,
                "created_at": None,
                "links": [],
                "full_data": task,
            }
        # Parse updatedAt field if available
        task_updated_at = None
        if task.get("updatedAt"):
            try:
                # Handle both "Z" and "+00:00" timezone formats
                updated_at_str = task["updatedAt"].replace("Z", "+00:00")
                task_updated_at = datetime.fromisoformat(updated_at_str)
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Failed to parse updatedAt '{task.get('updatedAt')}': {e}"
                )

        # Parse createdAt field if available
        task_created_at = None
        if task.get("createdAt"):
            try:
                # Handle both "Z" and "+00:00" timezone formats
                created_at_str = task["createdAt"].replace("Z", "+00:00")
                task_created_at = datetime.fromisoformat(created_at_str)
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Failed to parse createdAt '{task.get('createdAt')}': {e}"
                )

        def _choose_prodteam(task_obj: Dict[str, Any]) -> str:
            def norm(val: Any) -> str:
                if val is None:
                    return ""
                try:
                    return str(val).strip()
                except Exception:
                    return ""

            new_val = norm(task_obj.get(FULLSTACK_PRODTEAM_FIELD, ""))
            old_val = norm(task_obj.get(LEGACY_PRODTEAM_FIELD, ""))
            if new_val:
                return new_val
            if old_val:
                return old_val
            return ""

        prodteam_value = _choose_prodteam(task)

        return {
            "tracker_id": str(task.get("id", "")),
            "key": task.get("key", ""),  # Task code like TEST-123
            "summary": task.get("summary", "")[:500] if task.get("summary") else None,
            "description": task.get("description", ""),
            "status": task.get("status", {}).get("display", "")
            if task.get("status")
            else "",
            "author": task.get("createdBy", {}).get("display", "")
            if task.get("createdBy")
            else "",
            "assignee": task.get("assignee", {}).get("display", "")
            if task.get("assignee")
            else "",
            "business_client": self._format_user_list(task.get("businessClient")),
            "customer": self._format_user_list(
                task.get("businessClient")
            ),  # Customer field
            "team": str(task.get("63515d47fe387b7ce7b9fc55--team", "")),
            "prodteam": prodteam_value,
            "profit_forecast": str(
                task.get("63515d47fe387b7ce7b9fc55--profitForecast", "")
            ),
            "task_updated_at": task_updated_at,
            "created_at": task_created_at,
            "links": task.get("links", []),  # Include links from API response
            "full_data": task,  # Store complete task data
        }

    def extract_status_history(
        self, changelog: List[Dict[str, Any]], task_key: str = None
    ) -> List[Dict[str, Any]]:
        """Extract status history from changelog."""
        status_changes = []

        for entry in changelog:
            updated_at = entry.get("updatedAt", "")
            if not updated_at:
                continue

            for field in entry.get("fields", []):
                if field.get("field", {}).get("id") != STATUS_FIELD_ID:
                    continue

                status_name = field.get("to", {}).get("display") or field.get(
                    "to", {}
                ).get("key")
                if not status_name:
                    continue

                status_change = {
                    "status": status_name,
                    "status_display": status_name,
                    "start_date": datetime.fromisoformat(
                        updated_at.replace("Z", "+00:00")
                    ),
                }
                status_changes.append(status_change)

        # Sort by date and add end dates
        status_changes.sort(key=lambda x: x["start_date"])
        for i, change in enumerate(status_changes):
            if i + 1 < len(status_changes):
                change["end_date"] = status_changes[i + 1]["start_date"]

        # Remove duplicates based on status and start_date
        unique_changes = []
        seen = set()
        for change in status_changes:
            # Create a unique key for each status change
            key = (change["status"], change["start_date"])
            if key not in seen:
                seen.add(key)
                unique_changes.append(change)

        # Log status extraction results (removed detailed per-task output)
        # Detailed progress is now shown via progress bar in sync_tracker.py

        return unique_changes

    def extract_status_history_with_initial_status(
        self,
        changelog: List[Dict[str, Any]],
        task_data: Dict[str, Any],
        task_key: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract status history from changelog, properly handling initial status from 'from' field.

        This method solves the problem where tasks created with an initial status but never changed
        would have no history entries, losing the initial status information.

        Args:
            changelog: List of changelog entries from Tracker API
            task_data: Task data containing status and date information
            task_key: Optional task key for logging purposes

        Returns:
            List of status history entries, including initial status from 'from' field
        """
        # Extract status changes from changelog with proper initial status handling
        status_changes = self._extract_status_history_with_from_field(
            changelog, task_data, task_key
        )

        # If no status changes in changelog, add current status as initial
        if not status_changes and task_data.get("status"):
            initial_status = self._create_initial_status_entry(task_data)
            status_changes = [initial_status]

        return status_changes

    def _extract_status_history_with_from_field(
        self,
        changelog: List[Dict[str, Any]],
        task_info: Dict[str, Any],
        task_key: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract status history from changelog, properly handling 'from' field for initial status.

        Args:
            changelog: List of changelog entries from Tracker API
            task_data: Task data containing status and date information
            task_key: Optional task key for logging purposes

        Returns:
            List of status history entries with proper initial status from 'from' field
        """
        status_changes = []
        initial_status_added = False

        # Process each changelog entry
        for entry in changelog:
            if not entry.get("updatedAt"):
                continue

            # Process each field change in the entry
            for field in entry.get("fields", []):
                if not self._is_status_field(field):
                    continue

                # Extract status change information
                status_change = self._extract_status_change_info(
                    field, entry["updatedAt"]
                )
                if not status_change:
                    continue

                # Handle initial status if this is the first change
                if not initial_status_added:
                    initial_entry = self._create_initial_status_entry_from_change(
                        status_change, task_info
                    )
                    if initial_entry:
                        status_changes.append(initial_entry)
                        initial_status_added = True

                # Add the new status
                status_changes.append(status_change)

        # Post-process the status changes
        # 1) Ensure chronological order before setting end dates
        status_changes.sort(key=lambda x: x["start_date"])  # ascending

        # 2) Set end dates based on next start_date
        self._set_end_dates_for_status_changes(status_changes)

        # 3) Normalize any malformed intervals (defensive)
        for ch in status_changes:
            if ch.get("end_date") is not None and ch["end_date"] < ch["start_date"]:
                ch["end_date"] = ch["start_date"]

        # 4) Remove duplicates
        unique_changes = self._remove_duplicate_status_changes(status_changes)

        # Log results
        self._log_status_extraction_results(
            task_key, len(unique_changes), len(changelog)
        )

        return unique_changes

    def _is_status_field(self, field: Dict[str, Any]) -> bool:
        """Check if field is a status field."""
        return field.get("field", {}).get("id") == STATUS_FIELD_ID

    def _extract_status_change_info(
        self, field: Dict[str, Any], updated_at: str
    ) -> Optional[Dict[str, Any]]:
        """Extract status change information from field."""
        to_status = field.get("to", {}).get("display") or field.get("to", {}).get("key")
        if not to_status:
            return None

        change_date = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        return {
            "status": to_status,
            "status_display": to_status,
            "start_date": change_date,
            "end_date": None,  # Will be set later
            "from_status": field.get("from", {}).get("display")
            if field.get("from")
            else None,
        }

    def _create_initial_status_entry_from_change(
        self, status_change: Dict[str, Any], task_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create initial status entry from the first status change."""
        from_status = status_change.get("from_status")
        change_date = status_change["start_date"]

        # Determine initial status
        if from_status:
            # Use 'from' field if available
            initial_status = from_status
        else:
            # Fallback to current status
            initial_status = task_data.get("status", "")
            if not initial_status:
                return None

        # Use task creation date for initial status start date
        # This ensures the initial status starts when the task was created
        initial_start_date = self._determine_initial_status_date(task_data)

        return {
            "status": initial_status,
            "status_display": initial_status,
            "start_date": initial_start_date,  # Use task creation date
            "end_date": change_date,
        }

    def _set_end_dates_for_status_changes(
        self, status_changes: List[Dict[str, Any]]
    ) -> None:
        """Set end dates for all status changes except the last one."""
        for i, change in enumerate(status_changes):
            if i + 1 < len(status_changes):
                change["end_date"] = status_changes[i + 1]["start_date"]

    def _remove_duplicate_status_changes(
        self, status_changes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate status changes based on status and start_date."""
        unique_changes = []
        seen = set()

        for change in status_changes:
            # Remove 'from_status' from the change before adding to result
            change_copy = {k: v for k, v in change.items() if k != "from_status"}

            key = (change_copy["status"], change_copy["start_date"])
            if key not in seen:
                seen.add(key)
                unique_changes.append(change_copy)

        return unique_changes

    def _log_status_extraction_results(
        self, task_key: Optional[str], unique_count: int, total_entries: int
    ) -> None:
        """Log status extraction results."""
        # Detailed progress is now shown via progress bar in sync_tracker.py
        pass

    def _create_initial_status_entry(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create initial status entry for tasks with no changelog entries."""
        start_date = self._determine_initial_status_date(task_data)

        return {
            "status": task_data["status"],
            "status_display": task_data["status"],
            "start_date": start_date,
            "end_date": None,
        }

    def _determine_initial_status_date(self, task_data: Dict[str, Any]) -> datetime:
        """Determine the best date to use for initial status entry."""
        # Priority: created_at > task_updated_at > current time
        if task_data.get("created_at"):
            return task_data["created_at"]
        elif task_data.get("task_updated_at"):
            return task_data["task_updated_at"]
        else:
            # Fallback to current time if no dates available
            return datetime.now(timezone.utc)

    def _format_user_list(self, value: Any) -> str:
        """Format user list from tracker response."""
        if isinstance(value, list):
            names = []
            for v in value:
                if isinstance(v, dict):
                    names.append(v.get("display") or str(v.get("id", "")))
                else:
                    names.append(str(v))
            return ", ".join([n for n in names if n])
        elif isinstance(value, dict):
            return value.get("display") or str(value.get("id", ""))
        else:
            return str(value) if value else ""

    def get_active_tasks(self, limit: int = 100) -> List[str]:
        """
        Get active tasks (not closed/completed).

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of task IDs
        """
        try:
            # Try to get tasks with common active statuses
            # Use a simple approach to avoid complex queries
            query = "Status: Open OR Status: 'In Progress' OR Status: Testing OR Status: Review"
            return self.search_tasks(query=query, limit=limit)

        except Exception as e:
            logger.error(f"Failed to get active tasks: {e}")
            # Fallback: try to get all tasks and filter by status
            try:
                all_tasks = self.search_tasks(query="", limit=limit * 2)
                if all_tasks:
                    logger.info(f"Fallback: found {len(all_tasks)} total tasks")
                    return all_tasks[:limit]
            except:
                pass
            return []

    def get_total_tasks_count(self, query: str = "") -> int:
        """
        Get total count of tasks matching the query.

        Args:
            query: Yandex Tracker search query

        Returns:
            Total count of tasks
        """
        try:
            # Use the same endpoint as search_tasks for consistency
            url = f"{self.base_url}issues/_search"

            # For POST request to _search endpoint
            post_data = {"query": query}

            params = {"perPage": 1, "page": 1}  # We only need headers, not data

            response = self._make_request(
                url, method="POST", json=post_data, params=params
            )

            # Try to get total count from headers first
            total_count = response.headers.get("X-Total-Count")
            if total_count:
                return int(total_count)

            # Try X-Total-Pages header
            total_pages = response.headers.get("X-Total-Pages")
            if total_pages:
                # If we know total pages, we can estimate total count
                # But for now, let's use a fallback approach
                pass

            # Fallback: try to get from response data
            data = response.json()
            if isinstance(data, list):
                return len(data)
            elif isinstance(data, dict):
                issues = data.get("issues", [])
                return len(issues) if isinstance(issues, list) else 0
            return 0

        except Exception as e:
            logger.error(f"Failed to get total tasks count: {e}")
            return 0

    def search_tasks(self, query: str, limit: int = None) -> List[str]:
        """
        Search for tasks using a query with automatic pagination method selection.

        Args:
            query: Yandex Tracker search query
            limit: Maximum number of tasks to return (uses default from config if None)

        Returns:
            List of task IDs
        """
        try:
            # Если limit не указан, проверяем total count для автоопределения
            if limit is None or limit == settings.MAX_UNLIMITED_LIMIT:
                if self.should_use_scroll(query):
                    # API показывает 10000 - может быть больше, используем scroll
                    logger.info(
                        f"X-Total-Count >= 10000, переключаемся на scroll для получения всех задач"
                    )
                    return self._search_tasks_with_scroll(
                        query,
                        limit=999999,  # Очень большой limit для получения всех задач
                        extract_full_data=False,
                        fields=None,
                    )
                else:
                    # Точное количество известно, используем v2
                    total_count = self.get_total_tasks_count(query)
                    logger.info(
                        f"X-Total-Count: {total_count}, используем v2 pagination"
                    )
                    limit = total_count

            log_limit_info(f"Поиск задач с фильтром: {query}", limit)

            # Если limit указан явно, используем старую логику
            if limit > 10000:
                logger.info(f"Используем scroll-пагинацию (v3) для {limit} задач")
                return self._search_tasks_with_scroll(
                    query, limit, extract_full_data=False, fields=None
                )

            # Существующая логика для обычной пагинации v2 (БЕЗ ИЗМЕНЕНИЙ)
            url = f"{self.base_url}issues/_search"
            all_task_ids = []
            page = 1
            per_page = settings.API_PAGE_SIZE

            while True:
                # Prepare request data
                post_data = {"query": query}
                params = {"perPage": per_page, "page": page}

                logger.debug(f"   Страница {page}: запрос {per_page} задач")
                response = self._make_request(
                    url, method="POST", json=post_data, params=params
                )
                data = response.json()

                # Extract task IDs from response
                page_task_ids = self._extract_task_ids_from_response(data)

                # Add tasks to collection
                all_task_ids.extend(page_task_ids)
                logger.debug(
                    f"   Страница {page}: получено {len(page_task_ids)} задач, всего: {len(all_task_ids)}"
                )

                # Check if we should continue pagination
                if not self._should_continue_pagination(
                    all_task_ids, limit, page, page_task_ids, response
                ):
                    if len(all_task_ids) >= limit:
                        logger.info(f"   Достигнут лимит {limit} задач")
                    elif not page_task_ids:
                        logger.debug(f"   Страница {page}: задач не найдено")
                    else:
                        total_pages = response.headers.get("X-Total-Pages")
                        if total_pages:
                            logger.info(
                                f"   Достигнута последняя страница {total_pages}"
                            )
                        else:
                            logger.warning(
                                "Reached maximum page limit, stopping pagination"
                            )
                    break

                page += 1

            # Limit to requested number
            result = all_task_ids[:limit]
            logger.info(
                f"Found {len(result)} tasks via API search (requested: {limit})"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to search tasks: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def search_tasks_with_data(
        self,
        query: str,
        limit: int = None,
        expand: List[str] = None,
        fields: List[str] = None,
        progress_callback: Callable[[int], None] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for tasks using a query with automatic pagination method selection and return full task data.

        Args:
            query: Yandex Tracker search query
            limit: Maximum number of tasks to return (uses default from config if None)
            expand: List of fields to expand (e.g., ['links'])

        Returns:
            List of full task data dictionaries
        """
        try:
            # Если limit не указан или равен MAX_UNLIMITED_LIMIT, проверяем total count для автоопределения
            if limit is None or limit == settings.MAX_UNLIMITED_LIMIT:
                if self.should_use_scroll(query):
                    # API показывает 10000 - может быть больше, используем scroll
                    logger.info(
                        f"X-Total-Count >= 10000, переключаемся на scroll для получения всех задач"
                    )
                    return self._search_tasks_with_scroll(
                        query,
                        limit=999999,  # Очень большой limit для получения всех задач
                        extract_full_data=True,
                        expand=expand,
                        fields=fields,
                    )
                else:
                    # Точное количество известно, используем v2
                    total_count = self.get_total_tasks_count(query)
                    logger.info(
                        f"X-Total-Count: {total_count}, используем v2 pagination"
                    )
                    limit = total_count

            log_limit_info(f"Поиск задач с полными данными: {query}", limit)

            # Если limit указан явно, используем старую логику
            if limit > 10000:
                logger.info(
                    f"Используем scroll-пагинацию (v3) для {limit} задач с данными"
                )
                return self._search_tasks_with_scroll(
                    query,
                    limit,
                    extract_full_data=True,
                    expand=expand,
                    fields=fields,
                    progress_callback=progress_callback,
                )

            # Существующая логика для обычной пагинации v2 (БЕЗ ИЗМЕНЕНИЙ)
            url = f"{self.base_url}issues/_search"
            all_tasks = []
            page = 1
            per_page = settings.API_PAGE_SIZE

            while True:
                # Prepare request data
                post_data = {"query": query}
                params = {"perPage": per_page, "page": page}
                if expand:
                    params["expand"] = ",".join(expand)
                if fields:
                    params["fields"] = ",".join(fields)

                logger.debug(f"   Страница {page}: запрос {per_page} задач")
                response = self._make_request(
                    url, method="POST", json=post_data, params=params
                )

                try:
                    data = response.json()
                except requests.exceptions.JSONDecodeError as e:
                    logger.error(f"❌ Ошибка парсинга JSON на странице {page}: {e}")
                    logger.error(f"   Размер ответа: {len(response.text)} символов")
                    logger.error(f"   Первые 500 символов: {response.text[:500]}")
                    logger.error(f"   Последние 500 символов: {response.text[-500:]}")
                    raise

                # Extract full task data from response
                page_tasks = self._extract_tasks_from_response(data)

                # Add tasks to collection
                all_tasks.extend(page_tasks)
                logger.debug(
                    f"   Страница {page}: получено {len(page_tasks)} задач, всего: {len(all_tasks)}"
                )

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(len(all_tasks))

                # Check if we should continue pagination
                if not self._should_continue_pagination(
                    all_tasks, limit, page, page_tasks, response
                ):
                    if len(all_tasks) >= limit:
                        logger.info(f"   Достигнут лимит {limit} задач")
                    elif not page_tasks:
                        logger.info(f"   Больше задач нет")
                    else:
                        logger.info(f"   Получены все доступные задачи")
                    break

                page += 1

            # Limit results if needed
            if len(all_tasks) > limit:
                all_tasks = all_tasks[:limit]

            logger.info(f"Найдено {len(all_tasks)} задач с полными данными")
            return all_tasks

        except Exception as e:
            logger.error(f"Failed to search tasks with data: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def _extract_tasks_from_response(self, data: Any) -> List[Dict[str, Any]]:
        """Extract full task data from API response data."""
        tasks = []

        if isinstance(data, list):
            # API returned list of issues directly
            for item in data:
                if isinstance(item, dict) and item.get("id"):
                    tasks.append(item)
        elif isinstance(data, dict):
            # API returned dict with issues key
            issues = data.get("issues", [])
            if isinstance(issues, list):
                for item in issues:
                    if isinstance(item, dict) and item.get("id"):
                        tasks.append(item)

        return tasks

    def _extract_task_ids_from_response(self, data: Any) -> List[str]:
        """Extract task IDs from API response data."""
        task_ids = []

        if isinstance(data, list):
            # API returned list of issues directly
            for item in data:
                if isinstance(item, dict) and item.get("id"):
                    task_ids.append(str(item["id"]))
        elif isinstance(data, dict):
            # API returned dict with issues key
            issues = data.get("issues", [])
            if isinstance(issues, list):
                for item in issues:
                    if isinstance(item, dict) and item.get("id"):
                        task_ids.append(str(item["id"]))

        return task_ids

    def _should_continue_pagination(
        self,
        all_task_ids: List[str],
        limit: int,
        page: int,
        page_task_ids: List[str],
        response,
    ) -> bool:
        """
        Check if pagination should continue.

        Args:
            all_task_ids: All collected task IDs so far
            limit: Maximum number of tasks to collect
            page: Current page number
            page_task_ids: Task IDs from current page
            response: HTTP response object

        Returns:
            True if pagination should continue, False otherwise
        """
        # Stop if we have enough tasks
        if len(all_task_ids) >= limit:
            return False

        # Stop if no more tasks on current page
        if not page_task_ids:
            return False

        # Stop if we've reached the last page
        total_pages = response.headers.get("X-Total-Pages")
        if total_pages and page >= int(total_pages):
            return False

        # Safety check to prevent infinite loops
        if page > 200:  # Maximum 200 pages = 10000 tasks
            return False

        return True

    def get_tasks_by_filter(
        self, filters: Dict[str, Any] = None, limit: int = None
    ) -> List[str]:
        """
        Get tasks using various filters.

        Args:
            filters: Dictionary of filters (status, assignee, team, etc.)
            limit: Maximum number of tasks to return (uses default from config if None)

        Returns:
            List of task IDs
        """
        try:
            # Use default limit from config if not provided
            if limit is None:
                limit = settings.DEFAULT_SEARCH_LIMIT

            # Check if we have a direct query string
            if filters and "query" in filters:
                # Use the query string directly as provided
                search_query = filters["query"]
                logger.info(f"Using direct query: {search_query}")
                return self.search_tasks(query=search_query, limit=limit)

            # Build search query from filters using Tracker query syntax
            search_parts = []

            if filters:
                for key, value in filters.items():
                    if value:
                        if key == "status":
                            search_parts.append(f'Status: "{value}"')
                        elif key == "assignee":
                            search_parts.append(f'Assignee: "{value}"')
                        elif key == "team":
                            search_parts.append(f'Team: "{value}"')
                        elif key == "author":
                            search_parts.append(f'Author: "{value}"')
                        elif key == "updated_since":
                            if isinstance(value, datetime):
                                search_parts.append(
                                    f'Updated: >{value.strftime("%Y-%m-%d")}'
                                )
                            else:
                                search_parts.append(f"Updated: >{value}")
                        elif key == "created_since":
                            if isinstance(value, datetime):
                                search_parts.append(
                                    f'Created: >{value.strftime("%Y-%m-%d")}'
                                )
                            else:
                                search_parts.append(f"Created: >{value}")
                        elif key == "key":
                            # Filter by task key (e.g., CPO-*)
                            search_parts.append(f'Key: "{value}"')
                        else:
                            # Generic filter
                            search_parts.append(f'{key}: "{value}"')

            # If no specific filters, get recent tasks
            if not search_parts:
                search_parts.append(
                    "Updated: >2024-01-01"
                )  # Default: tasks updated this year

            search_query = " AND ".join(search_parts)

            return self.search_tasks(query=search_query, limit=limit)

        except Exception as e:
            logger.error(f"Failed to get tasks by filter: {e}")
            return []

    def get_tasks_by_filter_with_data(
        self,
        filters: Dict[str, Any] = None,
        limit: int = None,
        fields: List[str] = None,
        progress_callback: Callable[[int], None] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get tasks with full data using various filters.

        Args:
            filters: Dictionary of filters (status, assignee, team, etc.)
            limit: Maximum number of tasks to return (uses default from config if None)

        Returns:
            List of full task data dictionaries
        """
        try:
            # Use default limit from config if not provided
            if limit is None:
                limit = settings.DEFAULT_SEARCH_LIMIT

            # Check if we have a direct query string
            if filters and "query" in filters:
                # Use the query string directly as provided
                search_query = filters["query"]
                logger.info(f"Using direct query: {search_query}")
                return self.search_tasks_with_data(
                    query=search_query,
                    limit=limit,
                    expand=["links"],
                    fields=fields,
                    progress_callback=progress_callback,
                )

            # Build search query from filters using Tracker query syntax
            search_parts = []

            if filters:
                for key, value in filters.items():
                    if value:
                        if key == "status":
                            search_parts.append(f'Status: "{value}"')
                        elif key == "assignee":
                            search_parts.append(f'Assignee: "{value}"')
                        elif key == "team":
                            search_parts.append(f'Team: "{value}"')
                        elif key == "author":
                            search_parts.append(f'Author: "{value}"')
                        elif key == "updated_since":
                            if isinstance(value, datetime):
                                search_parts.append(
                                    f'Updated: >{value.strftime("%Y-%m-%d")}'
                                )
                            else:
                                search_parts.append(f"Updated: >{value}")
                        elif key == "created_since":
                            if isinstance(value, datetime):
                                search_parts.append(
                                    f'Created: >{value.strftime("%Y-%m-%d")}'
                                )
                            else:
                                search_parts.append(f"Created: >{value}")
                        else:
                            # For custom fields, use the key directly
                            search_parts.append(f"{key}: {value}")

            search_query = " AND ".join(search_parts) if search_parts else ""

            if not search_query:
                logger.warning("No filters provided, returning empty list")
                return []

            logger.info(f"Built search query: {search_query}")
            return self.search_tasks_with_data(
                query=search_query,
                limit=limit,
                expand=["links"],
                fields=fields,
                progress_callback=progress_callback,
            )

        except Exception as e:
            logger.error(f"Failed to get tasks by filter: {e}")
            return []

    def get_recent_tasks(self, days: int = 30, limit: int = None) -> List[str]:
        """
        Get recently updated tasks.

        Args:
            days: Number of days to look back
            limit: Maximum number of tasks to return (uses default from config if None)

        Returns:
            List of task IDs
        """
        try:
            # Use default limit from config if not provided
            if limit is None:
                limit = settings.DEFAULT_SEARCH_LIMIT

            # Use simple query for recent tasks
            updated_since = datetime.now() - timedelta(days=days)
            date_str = updated_since.strftime("%Y-%m-%d")

            # Simple query that should work with Tracker API
            query = f"Updated: >{date_str}"
            return self.search_tasks(query=query, limit=limit)

        except Exception as e:
            logger.error(f"Failed to get recent tasks: {e}")
            return []

    def get_total_tasks_count(self, query: str) -> int:
        """
        Get total count of tasks matching the query from X-Total-Count header.

        Args:
            query: Search query

        Returns:
            Total count of tasks (may be capped at 10000 by API)
        """
        try:
            headers = {
                "Authorization": f"OAuth {settings.TRACKER_API_TOKEN}",
                "X-Org-ID": settings.TRACKER_ORG_ID,
                "Content-Type": "application/json",
            }

            url = f"{settings.TRACKER_BASE_URL}issues/_search"
            post_data = {"query": query}
            params = {"perPage": 1, "page": 1}  # Minimal request just to get count

            response = self._make_request(
                url, method="POST", json=post_data, params=params
            )

            total_count = response.headers.get("X-Total-Count")
            if total_count:
                return int(total_count)
            else:
                logger.warning("No X-Total-Count header found")
                return 0

        except Exception as e:
            logger.error(f"Failed to get total tasks count: {e}")
            raise

    def should_use_scroll(self, query: str) -> bool:
        """
        Определяет, нужно ли использовать scroll pagination.

        Returns True если X-Total-Count == 10000 (может быть больше задач).
        Returns False если X-Total-Count < 10000 (известно точное количество).
        """
        try:
            total_count = self.get_total_tasks_count(query)
            # API возвращает максимум 10000 в X-Total-Count
            # Если именно 10000 - может быть больше, нужен scroll
            return total_count >= 10000
        except Exception as e:
            logger.warning(f"Не удалось определить total count, используем scroll: {e}")
            return True  # В случае ошибки используем scroll как более надежный метод

    def _search_tasks_with_scroll(
        self,
        query: str,
        limit: int,
        extract_full_data: bool = False,
        expand: List[str] = None,
        fields: List[str] = None,
        progress_callback: Callable[[int], None] = None,
    ) -> List[Any]:
        """
        Поиск задач с использованием scroll-пагинации (для >10000 результатов).

        Использует API v3: https://api.tracker.yandex.net/v3/issues/_search

        Args:
            query: Поисковый запрос на языке Яндекс Трекера
            limit: Максимальное количество задач
            extract_full_data: Если True - возвращает полные данные, если False - только ID

        Returns:
            Список задач (ID или полные данные в зависимости от extract_full_data)
        """
        # ВСЕГДА используем v3 для scroll
        url = "https://api.tracker.yandex.net/v3/issues/_search"

        all_results = []
        scroll_id = None
        page = 1

        # Первый запрос с инициализацией scroll
        params = {
            "scrollType": "unsorted",
            "perScroll": 1000,
            "scrollTTLMillis": 60000,  # 1 минута - проверенное рабочее значение
        }
        if expand:
            params["expand"] = ",".join(expand)
        if fields:
            params["fields"] = ",".join(fields)
        post_data = {"query": query}

        logger.info(f"Начинаем scroll-пагинацию (v3) для запроса: {query}")

        while len(all_results) < limit:
            # Для последующих запросов используем scrollId
            if scroll_id:
                params = {"scrollId": scroll_id, "scrollTTLMillis": 60000}
                if expand:
                    params["expand"] = ",".join(expand)
                if fields:
                    params["fields"] = ",".join(fields)

            response = self._make_request(
                url, method="POST", json=post_data, params=params
            )
            data = response.json()

            # Извлекаем результаты
            if extract_full_data:
                page_results = self._extract_tasks_from_response(data)
            else:
                page_results = self._extract_task_ids_from_response(data)

            if not page_results:
                logger.info(f"Scroll завершен: получен пустой ответ")
                break

            all_results.extend(page_results)
            logger.debug(
                f"Scroll страница {page}: получено {len(page_results)}, всего {len(all_results)}"
            )

            # Call progress callback if provided
            if progress_callback:
                progress_callback(len(all_results))

            # Получаем scroll_id для следующей страницы
            scroll_id = response.headers.get("X-Scroll-Id")

            if not scroll_id:
                logger.info(f"Scroll завершен: нет больше scroll ID")
                break

            page += 1

            # Защита от бесконечного цикла
            if page > 1000:  # Максимум 1 млн задач
                logger.warning("Достигнут максимальный лимит страниц (1000)")
                break

        # Ограничиваем результаты до запрошенного лимита
        results = all_results[:limit]
        logger.info(f"Scroll-пагинация завершена: получено {len(results)} задач")

        # TTL сам очистит ресурсы через 60 секунд - ничего не делаем
        return results

    def extract_field_from_full_data(
        self, full_data: Dict[str, Any], field_path: str
    ) -> Any:
        """
        Extract a field from full_data JSONB using dot notation for nested fields.

        Args:
            full_data: JSONB data from database
            field_path: Field path (e.g., "id", "status.display", "assignee.id")

        Returns:
            Field value or None if not found
        """
        if not full_data:
            return None

        # Handle nested field access with dot notation
        keys = field_path.split(".")
        value = full_data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    def extract_multiple_fields_from_full_data(
        self, full_data: Dict[str, Any], field_paths: List[str]
    ) -> Dict[str, Any]:
        """
        Extract multiple fields from full_data JSONB.

        Args:
            full_data: JSONB data from database
            field_paths: List of field paths to extract

        Returns:
            Dictionary with field paths as keys and values
        """
        if not full_data:
            return {path: None for path in field_paths}

        result = {}
        for field_path in field_paths:
            result[field_path] = self.extract_field_from_full_data(
                full_data, field_path
            )

        return result

    def get_task_data_from_full_data(
        self, full_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete task data from full_data JSONB (same as extract_task_data).

        Args:
            full_data: JSONB data from database

        Returns:
            Extracted task data or None if full_data is None/empty
        """
        if not full_data:
            return None

        return self.extract_task_data(full_data)


# Create service instance
tracker_service = TrackerAPIService()
