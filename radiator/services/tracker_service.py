"""Service for Yandex Tracker API integration."""

import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from radiator.core.config import settings
from radiator.core.logging import logger


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
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {url}, error: {e}")
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
        """Get task changelog with pagination."""
        all_data = []
        url = f"{self.base_url}issues/{task_id}/changelog"
        
        while url:
            try:
                response = self._make_request(url)
                page_data = response.json()
                all_data.extend(page_data)
                
                # Check for next page
                next_url = None
                link_header = response.headers.get("Link", "")
                for part in link_header.split(","):
                    if 'rel="next"' in part:
                        next_url = part.split(";")[0].strip("<> ")
                        break
                url = next_url
                
            except Exception as e:
                logger.error(f"Failed to get changelog for task {task_id}: {e}")
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
        """Get changelogs for multiple tasks in parallel."""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_id = {
                executor.submit(self.get_task_changelog, task_id): task_id 
                for task_id in task_ids
            }
            
            for future in as_completed(future_to_id):
                task_id = future_to_id[future]
                try:
                    changelog_data = future.result()
                    results.append((task_id, changelog_data))
                except Exception as e:
                    logger.error(f"Failed to get changelog for task {task_id}: {e}")
                    results.append((task_id, []))
        
        return results
    
    def extract_task_data(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data from task response."""
        return {
            "tracker_id": str(task.get("id", "")),
            "summary": task.get("summary", "")[:500] if task.get("summary") else None,
            "description": task.get("description", ""),
            "status": task.get("status", {}).get("display", ""),
            "author": task.get("createdBy", {}).get("display", ""),
            "assignee": task.get("assignee", {}).get("display", ""),
            "business_client": self._format_user_list(task.get("businessClient")),
            "team": str(task.get("63515d47fe387b7ce7b9fc55--team", "")),
            "prodteam": str(task.get("63515d47fe387b7ce7b9fc55--prodteam", "")),
            "profit_forecast": str(task.get("63515d47fe387b7ce7b9fc55--profitForecast", ""))
        }
    
    def extract_status_history(self, changelog: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract status history from changelog."""
        status_changes = []
        
        for entry in changelog:
            updated_at = entry.get("updatedAt", "")
            if not updated_at:
                continue
                
            for field in entry.get("fields", []):
                if field.get("field", {}).get("id") != "status":
                    continue
                
                status_name = field.get("to", {}).get("display") or field.get("to", {}).get("key")
                if not status_name:
                    continue
                
                status_changes.append({
                    "status": status_name,
                    "status_display": status_name,
                    "start_date": datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                })
        
        # Sort by date and add end dates
        status_changes.sort(key=lambda x: x["start_date"])
        for i, change in enumerate(status_changes):
            if i + 1 < len(status_changes):
                change["end_date"] = status_changes[i + 1]["start_date"]
        
        return status_changes
    
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
    
    def search_tasks(self, query: str, limit: int = 100) -> List[str]:
        """
        Search for tasks using a query.
        
        Args:
            query: Yandex Tracker search query
            limit: Maximum number of tasks to return
            
        Returns:
            List of task IDs
        """
        try:
            # Use the correct endpoint for searching issues
            url = f"{self.base_url}issues"
            params = {"query": query, "limit": limit}
            
            response = self._make_request(url, method="GET", params=params)
            data = response.json()
            
            # Extract task IDs - handle different response formats
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
            
            logger.info(f"Found {len(task_ids)} tasks via API search")
            return task_ids
            
        except Exception as e:
            logger.error(f"Failed to search tasks: {e}")
            return []
    
    def get_tasks_by_filter(self, filters: Dict[str, Any] = None, limit: int = 100) -> List[str]:
        """
        Get tasks using various filters.
        
        Args:
            filters: Dictionary of filters (status, assignee, team, etc.)
            limit: Maximum number of tasks to return
            
        Returns:
            List of task IDs
        """
        try:
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
    
    def get_recent_tasks(self, days: int = 30, limit: int = 100) -> List[str]:
        """
        Get recently updated tasks.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of tasks to return
            
        Returns:
            List of task IDs
        """
        try:
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
