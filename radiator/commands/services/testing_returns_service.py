"""Service for calculating testing returns from task status history."""

from typing import Dict, List, Optional, Set

from radiator.commands.models.time_to_market_models import StatusHistoryEntry
from radiator.core.database import SessionLocal
from radiator.core.logging import logger
from radiator.models.tracker import TrackerTask


class TestingReturnsService:
    """Service for analyzing testing returns from task status history."""

    def __init__(self, db=None):
        """
        Initialize the service.

        Args:
            db: Database session (optional, will create if not provided)
        """
        self.db = db or SessionLocal()
        # Performance optimization caches
        self._task_hierarchy_cache: Dict[str, List[str]] = {}
        self._task_existence_cache: Set[str] = set()
        self._fullstack_links_cache: Dict[str, List[str]] = {}

    def count_status_returns(
        self, history: List[StatusHistoryEntry], status: str
    ) -> int:
        """
        Count returns to a specific status.

        Returns = number of entries into status - 1 (first entry is not a return).

        Args:
            history: List of status history entries
            status: Status name to count returns for

        Returns:
            Number of returns to the status
        """
        if not history:
            return 0

        try:
            # Sort history by date to ensure correct order
            sorted_history = sorted(history, key=lambda x: x.start_date)

            entries = 0
            prev_status = None

            for entry in sorted_history:
                # Count entry if current status matches and previous status was different
                if entry.status == status and prev_status != status:
                    entries += 1
                prev_status = entry.status

            # Returns = entries - 1 (first entry is not a return)
            return max(0, entries - 1)

        except Exception as e:
            logger.warning(f"Failed to count status returns for '{status}': {e}")
            return 0

    def get_fullstack_links(self, cpo_task_key: str) -> List[str]:
        """
        Get FULLSTACK links from saved task data.

        Args:
            cpo_task_key: CPO task key (e.g., 'CPO-123')

        Returns:
            List of FULLSTACK task keys
        """
        # Check cache first
        if cpo_task_key in self._fullstack_links_cache:
            return self._fullstack_links_cache[cpo_task_key]

        try:
            task = (
                self.db.query(TrackerTask)
                .filter(TrackerTask.key == cpo_task_key)
                .first()
            )

            if not task or not task.links:
                self._fullstack_links_cache[cpo_task_key] = []
                return []

            # Filter FULLSTACK relates (both inward and outward)
            # Outward: CPO -> FULLSTACK (CPO task has outward link to FULLSTACK)
            # Inward: FULLSTACK -> CPO (FULLSTACK task has inward link from CPO)
            fullstack_keys = []
            for link in task.links:
                if link and isinstance(link, dict):  # Check if link is valid
                    if link.get("type", {}).get("id") == "relates" and link.get(
                        "object", {}
                    ).get("key", "").startswith("FULLSTACK"):
                        # Accept both inward and outward directions
                        fullstack_keys.append(link["object"]["key"])

            # Cache the result
            self._fullstack_links_cache[cpo_task_key] = fullstack_keys
            return fullstack_keys

        except Exception as e:
            logger.warning(f"Failed to get FULLSTACK links for {cpo_task_key}: {e}")
            self.db.rollback()
            self._fullstack_links_cache[cpo_task_key] = []
            return []

    def get_task_hierarchy(
        self, parent_key: str, visited: Optional[Set[str]] = None
    ) -> List[str]:
        """
        Recursively get epic + all subtasks using optimized JSONB query.

        OPTIMIZATION: Instead of loading ALL FULLSTACK tasks (10k+),
        we only load tasks that have a link to parent_key.
        This reduces 62,111 queries to ~10-20 queries.

        Args:
            parent_key: Parent task key
            visited: Set of already visited keys (for cycle protection)

        Returns:
            List of task keys including parent and all subtasks
        """
        if visited is None:
            visited = set()

        if parent_key in visited:
            return []  # Cycle protection

        # Check cache first
        if parent_key in self._task_hierarchy_cache:
            return self._task_hierarchy_cache[parent_key]

        visited.add(parent_key)
        result = [parent_key]

        try:
            # ✅ OPTIMIZED: Single query to find subtasks using JSONB operators
            # Only load tasks that actually link to parent_key
            from sqlalchemy import text

            query = text(
                """
                SELECT key, links
                FROM tracker_tasks
                WHERE key LIKE 'FULLSTACK%'
                AND links IS NOT NULL
                AND EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(links) AS link
                    WHERE link->'type'->>'id' = 'subtask'
                    AND link->>'direction' = 'inward'
                    AND link->'object'->>'key' = :parent_key
                )
            """
            )

            subtasks = self.db.execute(query, {"parent_key": parent_key}).fetchall()

            # Recursively process each subtask
            for subtask_key, subtask_links in subtasks:
                if subtask_key not in visited:
                    result.extend(self.get_task_hierarchy(subtask_key, visited))

            # Cache the result
            self._task_hierarchy_cache[parent_key] = result
            return result

        except Exception as e:
            logger.warning(f"Failed to get task hierarchy for {parent_key}: {e}")
            self.db.rollback()
            self._task_hierarchy_cache[parent_key] = [parent_key]
            return [parent_key]

    def calculate_testing_returns_for_task(
        self, task_key: str, history: List[StatusHistoryEntry]
    ) -> tuple[int, int]:
        """
        Calculate testing returns for a single task.

        Args:
            task_key: Task key
            history: Task status history

        Returns:
            Tuple of (testing_returns, external_test_returns)
        """
        testing_returns = self.count_status_returns(history, "Testing")
        external_returns = self.count_status_returns(history, "Внешний тест")

        return testing_returns, external_returns

    def _batch_check_task_existence(self, task_keys: List[str]) -> Set[str]:
        """
        Batch check which tasks exist in the database.

        Args:
            task_keys: List of task keys to check

        Returns:
            Set of existing task keys
        """
        # Filter out already cached keys
        uncached_keys = [
            key for key in task_keys if key not in self._task_existence_cache
        ]

        if not uncached_keys:
            return {key for key in task_keys if key in self._task_existence_cache}

        try:
            # Batch query to check existence
            existing_tasks = (
                self.db.query(TrackerTask.key)
                .filter(TrackerTask.key.in_(uncached_keys))
                .all()
            )

            # Update cache with existing tasks
            existing_keys = {task.key for task in existing_tasks}
            self._task_existence_cache.update(existing_keys)

            # Return all existing keys (cached + newly found)
            return {key for key in task_keys if key in self._task_existence_cache}

        except Exception as e:
            logger.warning(f"Failed to batch check task existence: {e}")
            return set()

    def calculate_testing_returns_for_cpo_task(
        self, cpo_task_key: str, get_task_history_func
    ) -> tuple[int, int]:
        """
        Calculate testing returns for a CPO task including all linked FULLSTACK tasks.

        Args:
            cpo_task_key: CPO task key
            get_task_history_func: Function to get task history by key

        Returns:
            Tuple of (total_testing_returns, total_external_test_returns)
        """
        try:
            # Get FULLSTACK epics linked to this CPO task
            fullstack_epics = self.get_fullstack_links(cpo_task_key)

            if not fullstack_epics:
                return 0, 0

            total_testing_returns = 0
            total_external_returns = 0

            # Collect all tasks from all epics first
            all_tasks = []
            for epic_key in fullstack_epics:
                # Get all tasks in the hierarchy (epic + subtasks)
                epic_tasks = self.get_task_hierarchy(epic_key)
                all_tasks.extend(epic_tasks)

            # Batch check task existence
            existing_tasks = self._batch_check_task_existence(all_tasks)

            # Process only existing tasks
            for task_key in all_tasks:
                if task_key not in existing_tasks:
                    logger.debug(f"Task {task_key} not found in database, skipping")
                    continue

                # Get task history
                history = get_task_history_func(task_key)
                if not history:
                    continue

                # Calculate returns for this task
                (
                    testing_returns,
                    external_returns,
                ) = self.calculate_testing_returns_for_task(task_key, history)

                total_testing_returns += testing_returns
                total_external_returns += external_returns

            return total_testing_returns, total_external_returns

        except Exception as e:
            logger.warning(
                f"Failed to calculate testing returns for {cpo_task_key}: {e}"
            )
            return 0, 0
