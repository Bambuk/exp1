"""Tests for single instance utility."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from radiator.core.single_instance import SingleInstance


class TestSingleInstance:
    """Test cases for SingleInstance class."""

    def test_single_instance_success(self):
        """Test successful single instance creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_dir = Path(temp_dir)

            with SingleInstance("test_lock", lock_dir) as instance:
                assert instance.lock_file.exists()
                assert instance.lock_fd is not None

                # Check that PID is written to lock file
                with open(instance.lock_file, "r") as f:
                    pid = int(f.read().strip())
                    assert pid == os.getpid()

    def test_single_instance_already_running(self):
        """Test that second instance fails when first is running."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_dir = Path(temp_dir)

            with SingleInstance("test_lock", lock_dir):
                # Try to create second instance - should fail
                with pytest.raises(
                    RuntimeError, match="Another instance is already running"
                ):
                    with SingleInstance("test_lock", lock_dir):
                        pass

    def test_single_instance_cleanup(self):
        """Test that lock file is cleaned up after use."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_dir = Path(temp_dir)
            lock_file = lock_dir / "test_lock.lock"

            with SingleInstance("test_lock", lock_dir):
                assert lock_file.exists()

            # Lock file should be removed after context exit
            assert not lock_file.exists()

    def test_is_running_no_lock_file(self):
        """Test is_running when no lock file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_dir = Path(temp_dir)
            instance = SingleInstance("test_lock", lock_dir)

            assert not instance.is_running()

    def test_is_running_stale_lock_file(self):
        """Test is_running with stale lock file (non-existent PID)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_dir = Path(temp_dir)
            lock_file = lock_dir / "test_lock.lock"

            # Create lock file with non-existent PID
            with open(lock_file, "w") as f:
                f.write("99999")  # Non-existent PID

            instance = SingleInstance("test_lock", lock_dir)

            # Should return False and clean up stale lock file
            assert not instance.is_running()
            assert not lock_file.exists()

    def test_is_running_valid_lock_file(self):
        """Test is_running with valid lock file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_dir = Path(temp_dir)
            lock_file = lock_dir / "test_lock.lock"

            # Create lock file with current PID
            with open(lock_file, "w") as f:
                f.write(str(os.getpid()))

            instance = SingleInstance("test_lock", lock_dir)

            # Should return True
            assert instance.is_running()

    def test_is_running_invalid_lock_file(self):
        """Test is_running with invalid lock file content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_dir = Path(temp_dir)
            lock_file = lock_dir / "test_lock.lock"

            # Create lock file with invalid content
            with open(lock_file, "w") as f:
                f.write("invalid_pid")

            instance = SingleInstance("test_lock", lock_dir)

            # Should return False
            assert not instance.is_running()

    def test_default_lock_directory(self):
        """Test that default lock directory is /tmp."""
        instance = SingleInstance("test_lock")
        assert instance.lock_file.parent == Path("/tmp")
        assert instance.lock_file.name == "test_lock.lock"

    def test_custom_lock_directory(self):
        """Test custom lock directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_dir = Path(temp_dir)
            instance = SingleInstance("test_lock", lock_dir)

            assert instance.lock_file.parent == lock_dir
            assert instance.lock_file.name == "test_lock.lock"
