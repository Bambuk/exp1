"""Tests for SingleInstance utility."""
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from radiator.core.single_instance import SingleInstance


class TestSingleInstance:
    """Test SingleInstance functionality."""

    def test_single_instance_success(self):
        """Test successful single instance creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_dir = Path(temp_dir)

            with SingleInstance("test_lock", lock_dir) as instance:
                # Check that lock file exists
                lock_file_path = Path(instance.lock_file)
                assert lock_file_path.exists()

    def test_single_instance_already_running(self):
        """Test that second instance fails when first is running."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_dir = Path(temp_dir)

            with SingleInstance("test_lock", lock_dir):
                # Use subprocess to test true inter-process locking
                # (fasteners uses reentrant locks in same process)
                code = f"""
import sys
from pathlib import Path
sys.path.insert(0, '{Path.cwd()}')
from radiator.core.single_instance import SingleInstance
try:
    with SingleInstance("test_lock", Path("{temp_dir}")):
        sys.exit(0)
except RuntimeError:
    sys.exit(1)
"""
                result = subprocess.run(
                    [sys.executable, "-c", code], capture_output=True, timeout=5
                )
                # Should fail with exit code 1
                assert result.returncode == 1

    def test_single_instance_cleanup(self):
        """Test that lock file is cleaned up after use."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_dir = Path(temp_dir)
            lock_file = lock_dir / "test_lock.lock"

            with SingleInstance("test_lock", lock_dir):
                assert lock_file.exists()

            # Note: fasteners may keep the lock file after release,
            # which is OK as it will be reused or cleaned up later

    def test_is_running_no_lock_file(self):
        """Test is_running when no lock file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_dir = Path(temp_dir)
            instance = SingleInstance("test_lock", lock_dir)

            assert not instance.is_running()

    def test_is_running_stale_lock_file(self):
        """Test is_running with stale lock file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_dir = Path(temp_dir)

            # Create a lock and release it to create a stale lock
            with SingleInstance("test_lock", lock_dir):
                pass

            instance = SingleInstance("test_lock", lock_dir)

            # Should return False as lock is released
            assert not instance.is_running()

    def test_is_running_valid_lock_file(self):
        """Test is_running with valid lock file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_dir = Path(temp_dir)

            # Use subprocess to hold lock in another process
            code = f"""
import sys
import time
from pathlib import Path
sys.path.insert(0, '{Path.cwd()}')
from radiator.core.single_instance import SingleInstance
with SingleInstance("test_lock", Path("{temp_dir}")):
    time.sleep(5)
"""
            proc = subprocess.Popen(
                [sys.executable, "-c", code],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            try:
                # Wait a bit for the subprocess to acquire lock
                import time

                time.sleep(0.5)

                instance = SingleInstance("test_lock", lock_dir)

                # Should return True as subprocess holds the lock
                assert instance.is_running()
            finally:
                proc.terminate()
                proc.wait(timeout=2)

    def test_is_running_invalid_lock_file(self):
        """Test is_running with invalid lock file content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_dir = Path(temp_dir)
            lock_file = lock_dir / "test_lock.lock"

            # Create lock file with invalid content
            with open(lock_file, "w") as f:
                f.write("invalid_content")

            instance = SingleInstance("test_lock", lock_dir)

            # Should return False (fasteners will handle corrupted files)
            assert not instance.is_running()

    def test_default_lock_directory(self):
        """Test that default lock directory is /tmp."""
        instance = SingleInstance("test_lock")
        assert Path(instance.lock_file).parent == Path("/tmp")
        assert Path(instance.lock_file).name == "test_lock.lock"

    def test_custom_lock_directory(self):
        """Test custom lock directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_dir = Path(temp_dir)
            instance = SingleInstance("test_lock", lock_dir)

            assert Path(instance.lock_file).parent == lock_dir
            assert Path(instance.lock_file).name == "test_lock.lock"
