"""Service for calculating testing returns from task status history."""

from typing import Dict, List, Optional, Set

from radiator.commands.models.time_to_market_models import StatusHistoryEntry
from radiator.core.database import SessionLocal
from radiator.core.logging import logger
from radiator.models.tracker import TrackerTask


class TestingReturnsService:
    __test__ = False
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

    def calculate_testing_returns_for_cpo_task_batched(
        self, cpo_task_key: str, batch_histories_func
    ) -> tuple[int, int]:
        """
        Calculate testing returns using pre-loaded batch histories.

        Args:
            cpo_task_key: CPO task key
            batch_histories_func: Function to batch load histories by keys

        Returns:
            Tuple of (total_testing_returns, total_external_test_returns)
        """
        try:
            # Get FULLSTACK epics linked to this CPO task
            fullstack_epics = self.get_fullstack_links(cpo_task_key)

            if not fullstack_epics:
                return 0, 0

            # Collect all tasks from all epics
            all_tasks = []
            for epic_key in fullstack_epics:
                epic_tasks = self.get_task_hierarchy(epic_key)
                all_tasks.extend(epic_tasks)

            # Batch check task existence
            existing_tasks = self._batch_check_task_existence(all_tasks)
            existing_task_list = [t for t in all_tasks if t in existing_tasks]

            if not existing_task_list:
                return 0, 0

            # КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Batch load ALL histories at once
            all_histories = batch_histories_func(existing_task_list)

            total_testing_returns = 0
            total_external_returns = 0

            # Process histories from batch result
            for task_key in existing_task_list:
                history = all_histories.get(task_key, [])
                if not history:
                    continue

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

    def batch_load_fullstack_links(
        self, cpo_task_keys: List[str]
    ) -> Dict[str, List[str]]:
        """
        Batch load FULLSTACK links for multiple CPO tasks.

        Args:
            cpo_task_keys: List of CPO task keys

        Returns:
            Dictionary mapping CPO key to list of FULLSTACK keys
        """
        # Check cache first
        uncached_keys = [
            k for k in cpo_task_keys if k not in self._fullstack_links_cache
        ]

        if not uncached_keys:
            return {k: self._fullstack_links_cache[k] for k in cpo_task_keys}

        try:
            # Batch query for all tasks
            tasks = (
                self.db.query(TrackerTask.key, TrackerTask.links)
                .filter(TrackerTask.key.in_(uncached_keys))
                .all()
            )

            # Process links
            for task_key, links in tasks:
                fullstack_keys = []
                if links:
                    for link in links:
                        if link and isinstance(link, dict):
                            if link.get("type", {}).get("id") == "relates" and link.get(
                                "object", {}
                            ).get("key", "").startswith("FULLSTACK"):
                                fullstack_keys.append(link["object"]["key"])

                self._fullstack_links_cache[task_key] = fullstack_keys

            # Return all results
            return {k: self._fullstack_links_cache.get(k, []) for k in cpo_task_keys}

        except Exception as e:
            logger.warning(f"Failed to batch load FULLSTACK links: {e}")
            return {k: [] for k in cpo_task_keys}

    def build_fullstack_hierarchy_batched(
        self, cpo_task_keys: List[str], max_depth: int = 6
    ) -> Dict[str, List[str]]:
        """
        Build FULLSTACK hierarchy for multiple CPO tasks with depth limit.

        Загружает иерархию за несколько проходов:
        1. Получаем все CPO задачи и их прямые FULLSTACK связи
        2. Для каждого уровня глубины ищем дочерние FULLSTACK задачи
        3. Останавливаемся на глубине 6 или когда нет новых задач

        Args:
            cpo_task_keys: List of CPO task keys
            max_depth: Maximum depth for hierarchy traversal (default 6)

        Returns:
            Dict mapping CPO key to list of all related FULLSTACK keys
        """
        logger.info(
            f"Building FULLSTACK hierarchy for {len(cpo_task_keys)} CPO tasks..."
        )

        # Step 1: Batch load direct FULLSTACK links for all CPO tasks
        cpo_to_fullstack = self.batch_load_fullstack_links(cpo_task_keys)

        # Step 2: Initialize state for each CPO task
        # Храним для каждой CPO: все найденные задачи + родители текущего уровня
        cpo_state = {}
        for cpo_key, direct_fullstack_keys in cpo_to_fullstack.items():
            if not direct_fullstack_keys:
                cpo_state[cpo_key] = {"all_tasks": set(), "current_parents": set()}
            else:
                cpo_state[cpo_key] = {
                    "all_tasks": set(direct_fullstack_keys),
                    "current_parents": set(direct_fullstack_keys),
                }

        # Step 3: Iterate through depth levels
        for depth in range(1, max_depth + 1):
            # Собираем всех уникальных родителей от ВСЕХ CPO задач
            all_current_parents = set()
            for state in cpo_state.values():
                all_current_parents.update(state["current_parents"])

            if not all_current_parents:
                break

            logger.info(
                f"Processing depth {depth} with {len(all_current_parents)} unique parents..."
            )

            # ОДИН батчевый запрос для всех родителей
            children_batch = self.get_task_hierarchy_batch(list(all_current_parents))

            # Обновляем каждую CPO задачу ИНДИВИДУАЛЬНО
            for cpo_key, state in cpo_state.items():
                next_parents = set()

                # Для каждого родителя ЭТОЙ конкретной CPO задачи
                for parent in state["current_parents"]:
                    children = children_batch.get(parent, [])
                    for child in children:
                        if child not in state["all_tasks"] and child != parent:
                            state["all_tasks"].add(child)
                            next_parents.add(child)

                state["current_parents"] = next_parents

            # Check if we hit max depth with remaining tasks
            if depth == max_depth and all_current_parents:
                logger.warning(
                    f"Reached max depth {max_depth} with {len(all_current_parents)} "
                    f"remaining tasks. Possible cyclic dependencies."
                )

        # Формируем результат
        result = {
            cpo_key: list(state["all_tasks"]) for cpo_key, state in cpo_state.items()
        }

        logger.info(
            f"Built hierarchy: {len(result)} CPO tasks -> "
            f"{sum(len(v) for v in result.values())} total FULLSTACK tasks"
        )

        return result

    def get_task_hierarchy_batch(self, parent_keys: List[str]) -> Dict[str, List[str]]:
        """
        Batch load task hierarchy for multiple parent tasks.

        Args:
            parent_keys: List of parent task keys

        Returns:
            Dict mapping parent key to list of child task keys
        """
        if not parent_keys:
            return {}

        # DEBUG: Count calls
        if not hasattr(self, "_hierarchy_batch_calls"):
            self._hierarchy_batch_calls = 0
        self._hierarchy_batch_calls += 1
        logger.info(
            f"🔍 get_task_hierarchy_batch call #{self._hierarchy_batch_calls} with {len(parent_keys)} parents"
        )

        try:
            # Batch query for all parent-child relationships using JSONB
            from sqlalchemy import text

            # Create a single query for all parent keys
            parent_keys_str = "', '".join(parent_keys)
            query = text(
                f"""
                SELECT key,
                       jsonb_array_elements(links)->'object'->>'key' as parent_key
                FROM tracker_tasks
                WHERE key LIKE 'FULLSTACK%'
                AND links IS NOT NULL
                AND EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(links) AS link
                    WHERE link->'type'->>'id' = 'subtask'
                    AND link->>'direction' = 'inward'
                    AND link->'object'->>'key' IN ('{parent_keys_str}')
                )
            """
            )

            subtasks = self.db.execute(query).fetchall()

            # Group children by parent
            result = {}
            for child_key, parent_key in subtasks:
                if parent_key and parent_key in parent_keys:
                    if parent_key not in result:
                        result[parent_key] = []
                    result[parent_key].append(child_key)

            # Ensure all parent keys are in result (even if no children)
            for parent_key in parent_keys:
                if parent_key not in result:
                    result[parent_key] = []

            logger.info(
                f"Batch loaded hierarchy for {len(parent_keys)} parents -> {sum(len(v) for v in result.values())} children"
            )
            return result

        except Exception as e:
            logger.warning(f"Failed to batch load task hierarchy: {e}")
            return {key: [] for key in parent_keys}
