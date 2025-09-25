"""Service for Yandex Tracker API integration."""

import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from radiator.core.config import settings, with_default_limit_method, log_limit_info
from radiator.core.logging import logger

# Constants for status field handling
STATUS_FIELD_ID = "status"


class TrackerAPIService:
    """Service for interacting with Yandex Tracker API."""
    
    def __init__(self):
        self.headers = {
            "Authorization": f"OAuth {settings.TRACKER_API_TOKEN}",
            "X-Org-ID": settings.TRACKER_ORG_ID,
            "Content-Type": "application/json"
        }
        self.base_url = settings.TRACKER_BASE_URL
        self.request_delay = settings.TRACKER_REQUEST_DELAY
        self.max_workers = settings.TRACKER_MAX_WORKERS
    
    def _make_request(self, url: str, method: str = "GET", **kwargs) -> requests.Response:
        """Make HTTP request with error handling and rate limiting."""
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            time.sleep(self.request_delay)  # Rate limiting
            return response
        except (requests.exceptions.RequestException, requests.exceptions.HTTPError) as e:
            # Упрощенное логирование ошибок API
            status_code = None
            response_text = None
            response_headers = None
            
            # Try to get response info from different exception types
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                response_text = e.response.text
                response_headers = dict(e.response.headers)
            elif isinstance(e, requests.exceptions.HTTPError):
                # For HTTPError, the response is stored differently
                status_code = e.response.status_code if hasattr(e, 'response') and e.response else None
                response_text = e.response.text if hasattr(e, 'response') and e.response else None
                response_headers = dict(e.response.headers) if hasattr(e, 'response') and e.response else None
            
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
            raise
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task details by ID."""
        try:
            url = f"{self.base_url}issues/{task_id}"
            response = self._make_request(url)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None
    
    def get_task_changelog(self, task_id: str) -> List[Dict[str, Any]]:
        """Get task changelog with pagination support."""
        all_data = []
        page = 1
        per_page = 50  # API default and maximum per page
        
        while True:
            try:
                url = f"{self.base_url}issues/{task_id}/changelog"
                params = {
                    "perPage": per_page,
                    "type": "IssueWorkflow"  # Только изменения статусов
                }
                
                # Если это не первая страница, добавляем параметр id для следующей страницы
                if page > 1 and hasattr(self, 'next_page_id'):
                    params["id"] = self.next_page_id
                
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
                    match = re.search(r'id=([^&]+)', link_header)
                    if match:
                        self.next_page_id = match.group(1)
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
                logger.error(f"❌ Ошибка получения истории для задачи {task_id}: {e}")
                break
        
        return all_data
    
    def get_tasks_batch(self, task_ids: List[str]) -> List[Tuple[str, Optional[Dict[str, Any]]]]:
        """Get multiple tasks in parallel."""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_id = {
                executor.submit(self.get_task, task_id): task_id 
                for task_id in task_ids
            }
            
            for future in as_completed(future_to_id):
                task_id = future_to_id[future]
                try:
                    task_data = future.result()
                    results.append((task_id, task_data))
                except Exception as e:
                    logger.error(f"Failed to get task {task_id}: {e}")
                    results.append((task_id, None))
        
        return results
    
    def get_changelogs_batch(self, task_ids: List[str]) -> List[Tuple[str, List[Dict[str, Any]]]]:
        """Get changelogs for multiple tasks in parallel with progress indication."""
        results = []
        total_tasks = len(task_ids)
        
        logger.info(f"🔄 Загружаем историю для {total_tasks} задач (параллельно, {self.max_workers} потоков)")
        
        # Use a callback-based approach to show real-time progress
        completed = 0
        results = [None] * len(task_ids)  # Pre-allocate results list
        
        def task_done_callback(future):
            nonlocal completed
            completed += 1
            # Show progress every 10 tasks or for the last task
            if completed % 10 == 0 or completed == total_tasks:
                logger.info(f"📥 Загружено истории: {completed}/{total_tasks} задач ({completed/total_tasks*100:.1f}%)")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks and store futures
            futures = []
            for i, task_id in enumerate(task_ids):
                future = executor.submit(self.get_task_changelog, task_id)
                future.add_done_callback(task_done_callback)
                futures.append((i, future, task_id))
            
            # Collect results as they complete
            for i, future, task_id in futures:
                try:
                    changelog_data = future.result()
                    results[i] = (task_id, changelog_data)
                except Exception as e:
                    logger.error(f"Failed to get changelog for task {task_id}: {e}")
                    results[i] = (task_id, [])
        
        logger.info(f"✅ История загружена для {len(results)} задач")
        return results
    
    def extract_task_data(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data from task response."""
        # Parse updatedAt field if available
        task_updated_at = None
        if task.get("updatedAt"):
            try:
                # Handle both "Z" and "+00:00" timezone formats
                updated_at_str = task["updatedAt"].replace("Z", "+00:00")
                task_updated_at = datetime.fromisoformat(updated_at_str)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse updatedAt '{task.get('updatedAt')}': {e}")
        
        # Parse createdAt field if available
        task_created_at = None
        if task.get("createdAt"):
            try:
                # Handle both "Z" and "+00:00" timezone formats
                created_at_str = task["createdAt"].replace("Z", "+00:00")
                task_created_at = datetime.fromisoformat(created_at_str)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse createdAt '{task.get('createdAt')}': {e}")
        
        return {
            "tracker_id": str(task.get("id", "")),
            "key": task.get("key", ""),  # Task code like TEST-123
            "summary": task.get("summary", "")[:500] if task.get("summary") else None,
            "description": task.get("description", ""),
            "status": task.get("status", {}).get("display", ""),
            "author": task.get("createdBy", {}).get("display", ""),
            "assignee": task.get("assignee", {}).get("display", ""),
            "business_client": self._format_user_list(task.get("businessClient")),
            "team": str(task.get("63515d47fe387b7ce7b9fc55--team", "")),
            "prodteam": str(task.get("63515d47fe387b7ce7b9fc55--prodteam", "")),
            "profit_forecast": str(task.get("63515d47fe387b7ce7b9fc55--profitForecast", "")),
            "task_updated_at": task_updated_at,
            "created_at": task_created_at
        }
    
    def extract_status_history(self, changelog: List[Dict[str, Any]], task_key: str = None) -> List[Dict[str, Any]]:
        """Extract status history from changelog."""
        status_changes = []
        
        for entry in changelog:
            updated_at = entry.get("updatedAt", "")
            if not updated_at:
                continue
                
            for field in entry.get("fields", []):
                if field.get("field", {}).get("id") != STATUS_FIELD_ID:
                    continue
                
                status_name = field.get("to", {}).get("display") or field.get("to", {}).get("key")
                if not status_name:
                    continue
                
                status_change = {
                    "status": status_name,
                    "status_display": status_name,
                    "start_date": datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
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
        
        # Выводим только итоговую информацию по задаче
        if task_key:
            print(f"📊 {task_key}: {len(unique_changes)} изменений статуса (из {len(changelog)} записей)")
        else:
            print(f"📊 Найдено {len(unique_changes)} изменений статуса (из {len(changelog)} записей)")
        
        return unique_changes
    
    def extract_status_history_with_initial_status(self, changelog: List[Dict[str, Any]], task_data: Dict[str, Any], task_key: str = None) -> List[Dict[str, Any]]:
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
        status_changes = self._extract_status_history_with_from_field(changelog, task_data, task_key)
        
        # If no status changes in changelog, add current status as initial
        if not status_changes and task_data.get("status"):
            initial_status = self._create_initial_status_entry(task_data)
            status_changes = [initial_status]
        
        return status_changes
    
    def _extract_status_history_with_from_field(self, changelog: List[Dict[str, Any]], task_info: Dict[str, Any], task_key: str = None) -> List[Dict[str, Any]]:
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
                status_change = self._extract_status_change_info(field, entry["updatedAt"])
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
        self._set_end_dates_for_status_changes(status_changes)
        unique_changes = self._remove_duplicate_status_changes(status_changes)
        
        # Log results
        self._log_status_extraction_results(task_key, len(unique_changes), len(changelog))
        
        return unique_changes
    
    def _is_status_field(self, field: Dict[str, Any]) -> bool:
        """Check if field is a status field."""
        return field.get("field", {}).get("id") == STATUS_FIELD_ID
    
    def _extract_status_change_info(self, field: Dict[str, Any], updated_at: str) -> Optional[Dict[str, Any]]:
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
            "from_status": field.get("from", {}).get("display") if field.get("from") else None
        }
    
    def _create_initial_status_entry_from_change(self, status_change: Dict[str, Any], task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
            "end_date": change_date
        }
    
    def _set_end_dates_for_status_changes(self, status_changes: List[Dict[str, Any]]) -> None:
        """Set end dates for all status changes except the last one."""
        for i, change in enumerate(status_changes):
            if i + 1 < len(status_changes):
                change["end_date"] = status_changes[i + 1]["start_date"]
    
    def _remove_duplicate_status_changes(self, status_changes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
    
    def _log_status_extraction_results(self, task_key: Optional[str], unique_count: int, total_entries: int) -> None:
        """Log status extraction results."""
        if task_key:
            print(f"📊 {task_key}: {unique_count} изменений статуса (из {total_entries} записей)")
        else:
            print(f"📊 Найдено {unique_count} изменений статуса (из {total_entries} записей)")
    
    def _create_initial_status_entry(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create initial status entry for tasks with no changelog entries."""
        start_date = self._determine_initial_status_date(task_data)
        
        return {
            "status": task_data["status"],
            "status_display": task_data["status"],
            "start_date": start_date,
            "end_date": None
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
                all_tasks = self.search_tasks(query="", limit=limit*2)
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
            post_data = {
                "query": query
            }
            
            params = {
                "perPage": 1,  # We only need headers, not data
                "page": 1
            }
            
            response = self._make_request(url, method="POST", json=post_data, params=params)
            
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
        Search for tasks using a query with simplified pagination.
        
        Args:
            query: Yandex Tracker search query
            limit: Maximum number of tasks to return (uses default from config if None)
            
        Returns:
            List of task IDs
        """
        try:
            # Use default limit from config if not provided
            if limit is None:
                limit = settings.DEFAULT_SEARCH_LIMIT
            
            log_limit_info(f"Поиск задач с фильтром: {query}", limit)
            
            url = f"{self.base_url}issues/_search"
            all_task_ids = []
            page = 1
            per_page = settings.API_PAGE_SIZE
            
            while True:
                # Prepare request data
                post_data = {"query": query}
                params = {"perPage": per_page, "page": page}
                
                logger.debug(f"   Страница {page}: запрос {per_page} задач")
                response = self._make_request(url, method="POST", json=post_data, params=params)
                data = response.json()
                
                # Extract task IDs from response
                page_task_ids = self._extract_task_ids_from_response(data)
                
                # Add tasks to collection
                all_task_ids.extend(page_task_ids)
                logger.debug(f"   Страница {page}: получено {len(page_task_ids)} задач, всего: {len(all_task_ids)}")
                
                # Check if we should continue pagination
                if not self._should_continue_pagination(all_task_ids, limit, page, page_task_ids, response):
                    if len(all_task_ids) >= limit:
                        logger.info(f"   Достигнут лимит {limit} задач")
                    elif not page_task_ids:
                        logger.debug(f"   Страница {page}: задач не найдено")
                    else:
                        total_pages = response.headers.get("X-Total-Pages")
                        if total_pages:
                            logger.info(f"   Достигнута последняя страница {total_pages}")
                        else:
                            logger.warning("Reached maximum page limit, stopping pagination")
                    break
                
                page += 1
            
            # Limit to requested number
            result = all_task_ids[:limit]
            logger.info(f"Found {len(result)} tasks via API search (requested: {limit})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to search tasks: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
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
    
    def _should_continue_pagination(self, all_task_ids: List[str], limit: int, page: int, 
                                   page_task_ids: List[str], response) -> bool:
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
    
    def get_tasks_by_filter(self, filters: Dict[str, Any] = None, limit: int = None) -> List[str]:
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
                                search_parts.append(f'Updated: >{value.strftime("%Y-%m-%d")}')
                            else:
                                search_parts.append(f'Updated: >{value}')
                        elif key == "created_since":
                            if isinstance(value, datetime):
                                search_parts.append(f'Created: >{value.strftime("%Y-%m-%d")}')
                            else:
                                search_parts.append(f'Created: >{value}')
                        elif key == "key":
                            # Filter by task key (e.g., CPO-*)
                            search_parts.append(f'Key: "{value}"')
                        else:
                            # Generic filter
                            search_parts.append(f'{key}: "{value}"')
            
            # If no specific filters, get recent tasks
            if not search_parts:
                search_parts.append("Updated: >2024-01-01")  # Default: tasks updated this year
            
            search_query = " AND ".join(search_parts)
            
            return self.search_tasks(query=search_query, limit=limit)
            
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


# Create service instance
tracker_service = TrackerAPIService()
