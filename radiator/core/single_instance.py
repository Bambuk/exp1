"""
Single instance utility for preventing multiple instances of the same process.
"""
from pathlib import Path
from typing import Optional

import fasteners


class SingleInstance:
    """Ensures only one instance of a process is running."""

    def __init__(self, lock_name: str, lock_dir: Optional[Path] = None):
        """
        Initialize single instance lock.

        Args:
            lock_name: Name for the lock file
            lock_dir: Directory for lock files (default: /tmp)
        """
        if lock_dir is None:
            lock_dir = Path("/tmp")

        self.lock_file = str(lock_dir / f"{lock_name}.lock")
        self.lock = fasteners.InterProcessLock(self.lock_file)

    def __enter__(self):
        """Acquire the lock."""
        # Try to acquire lock (non-blocking)
        if not self.lock.acquire(blocking=False):
            raise RuntimeError(
                f"Another instance is already running. Lock file: {self.lock_file}"
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release the lock."""
        self.lock.release()

    def is_running(self) -> bool:
        """
        Check if another instance is running.

        Returns:
            True if another instance is running, False otherwise
        """
        # Try to acquire lock temporarily
        if self.lock.acquire(blocking=False):
            # We got the lock, so no one else is running
            self.lock.release()
            return False
        return True
