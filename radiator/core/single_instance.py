"""
Single instance utility for preventing multiple instances of the same process.
"""
import fcntl
import os
import sys
from pathlib import Path
from typing import Optional


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

        self.lock_file = lock_dir / f"{lock_name}.lock"
        self.lock_fd: Optional[int] = None

    def __enter__(self):
        """Acquire the lock."""
        try:
            self.lock_fd = os.open(
                self.lock_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC
            )
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Write PID to lock file
            os.write(self.lock_fd, str(os.getpid()).encode())
            return self
        except (OSError, IOError) as e:
            if self.lock_fd:
                os.close(self.lock_fd)
            raise RuntimeError(
                f"Another instance is already running. Lock file: {self.lock_file}"
            ) from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release the lock."""
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                os.close(self.lock_fd)
                if self.lock_file.exists():
                    self.lock_file.unlink()
            except (OSError, IOError):
                pass  # Ignore errors during cleanup

    def is_running(self) -> bool:
        """
        Check if another instance is running.

        Returns:
            True if another instance is running, False otherwise
        """
        try:
            if not self.lock_file.exists():
                return False

            with open(self.lock_file, "r") as f:
                pid = int(f.read().strip())

            # Check if process is still running
            try:
                os.kill(pid, 0)  # Signal 0 just checks if process exists
                return True
            except OSError:
                # Process doesn't exist, remove stale lock file
                self.lock_file.unlink()
                return False

        except (OSError, ValueError):
            return False
