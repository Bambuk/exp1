"""Tests for sync_by_keys script."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.sync_by_keys import (
    build_sync_command,
    read_keys_from_file,
    split_into_batches,
    sync_batch,
    validate_key,
)


class TestReadKeysFromFile:
    """Test reading keys from file."""

    def test_read_keys_ignores_empty_lines(self):
        """Test that empty lines are ignored."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("FULLSTACK-123\n")
            f.write("\n")  # empty line
            f.write("FULLSTACK-124\n")
            f.write("   \n")  # whitespace only
            f.write("FULLSTACK-125\n")
            temp_file = f.name

        try:
            keys = read_keys_from_file(temp_file)
            assert keys == ["FULLSTACK-123", "FULLSTACK-124", "FULLSTACK-125"]
        finally:
            os.unlink(temp_file)

    def test_read_keys_file_not_found(self):
        """Test handling of non-existent file."""
        with pytest.raises(FileNotFoundError):
            read_keys_from_file("non_existent_file.txt")

    def test_read_keys_empty_file(self):
        """Test reading empty file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("")
            temp_file = f.name

        try:
            keys = read_keys_from_file(temp_file)
            assert keys == []
        finally:
            os.unlink(temp_file)


class TestValidateKey:
    """Test key validation."""

    def test_validate_key_correct_format(self):
        """Test correct key formats."""
        assert validate_key("FULLSTACK-123") == True
        assert validate_key("CPO-456") == True
        assert validate_key("A-1") == True
        assert validate_key("TEST-999999") == True

    def test_validate_key_incorrect_format(self):
        """Test incorrect key formats."""
        assert validate_key("invalid-key") == False
        assert validate_key("123-QUEUE") == False
        assert validate_key("FULLSTACK") == False
        assert validate_key("-123") == False
        assert validate_key("FULLSTACK-") == False
        assert validate_key("") == False
        assert validate_key("FULLSTACK-abc") == False


class TestSplitIntoBatches:
    """Test splitting keys into batches."""

    def test_split_500_keys_into_200_batches(self):
        """Test 500 keys split into batches of 200."""
        keys = [f"TEST-{i}" for i in range(500)]
        batches = split_into_batches(keys, 200)

        assert len(batches) == 3
        assert len(batches[0]) == 200
        assert len(batches[1]) == 200
        assert len(batches[2]) == 100

    def test_split_200_keys_into_200_batches(self):
        """Test 200 keys split into batches of 200."""
        keys = [f"TEST-{i}" for i in range(200)]
        batches = split_into_batches(keys, 200)

        assert len(batches) == 1
        assert len(batches[0]) == 200

    def test_split_150_keys_into_200_batches(self):
        """Test 150 keys split into batches of 200."""
        keys = [f"TEST-{i}" for i in range(150)]
        batches = split_into_batches(keys, 200)

        assert len(batches) == 1
        assert len(batches[0]) == 150

    def test_split_empty_list(self):
        """Test splitting empty list."""
        batches = split_into_batches([], 200)
        assert batches == []


class TestBuildSyncCommand:
    """Test building sync command."""

    def test_build_basic_command(self):
        """Test basic command without extra flags."""
        keys = ["A-1", "A-2", "A-3"]
        cmd = build_sync_command(keys, skip_history=False, limit=None)

        expected = [
            "python",
            "-m",
            "radiator.commands.sync_tracker",
            "--filter",
            "Key: A-1, A-2, A-3",
        ]
        assert cmd == expected

    def test_build_command_with_skip_history(self):
        """Test command with --skip-history flag."""
        keys = ["A-1", "A-2"]
        cmd = build_sync_command(keys, skip_history=True, limit=None)

        expected = [
            "python",
            "-m",
            "radiator.commands.sync_tracker",
            "--filter",
            "Key: A-1, A-2",
            "--skip-history",
        ]
        assert cmd == expected

    def test_build_command_with_limit(self):
        """Test command with --limit flag."""
        keys = ["A-1", "A-2"]
        cmd = build_sync_command(keys, skip_history=False, limit=100)

        expected = [
            "python",
            "-m",
            "radiator.commands.sync_tracker",
            "--filter",
            "Key: A-1, A-2",
            "--limit",
            "100",
        ]
        assert cmd == expected

    def test_build_command_with_all_flags(self):
        """Test command with all flags."""
        keys = ["A-1", "A-2"]
        cmd = build_sync_command(keys, skip_history=True, limit=50)

        expected = [
            "python",
            "-m",
            "radiator.commands.sync_tracker",
            "--filter",
            "Key: A-1, A-2",
            "--skip-history",
            "--limit",
            "50",
        ]
        assert cmd == expected


class TestSyncBatch:
    """Test syncing a single batch."""

    @patch("subprocess.run")
    def test_sync_batch_success(self, mock_run):
        """Test successful batch sync."""
        # Mock successful subprocess
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        keys = ["A-1", "A-2"]
        sync_batch(keys, skip_history=False, limit=None)

        # Verify subprocess was called correctly
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "python" in args
        assert "-m" in args
        assert "radiator.commands.sync_tracker" in args
        assert "--filter" in args
        assert "Key: A-1, A-2" in args

    @patch("subprocess.run")
    def test_sync_batch_failure(self, mock_run):
        """Test batch sync failure raises exception."""
        # Mock failed subprocess
        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        keys = ["A-1", "A-2"]

        with pytest.raises(RuntimeError, match="Batch sync failed"):
            sync_batch(keys, skip_history=False, limit=None)

    @patch("subprocess.run")
    def test_sync_batch_with_flags(self, mock_run):
        """Test batch sync with all flags."""
        # Mock successful subprocess
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        keys = ["A-1", "A-2"]
        sync_batch(keys, skip_history=True, limit=100)

        # Verify subprocess was called with all flags
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "--skip-history" in args
        assert "--limit" in args
        assert "100" in args


class TestMainLogic:
    """Test main script logic."""

    @patch("scripts.sync_by_keys.sync_batch")
    @patch("scripts.sync_by_keys.split_into_batches")
    @patch("scripts.sync_by_keys.read_keys_from_file")
    def test_main_stops_on_error(self, mock_read, mock_split, mock_sync):
        """Test that main stops when batch fails."""
        # Setup mocks
        mock_read.return_value = ["A-1", "A-2", "A-3", "A-4"]
        mock_split.return_value = [["A-1", "A-2"], ["A-3", "A-4"]]

        # First batch succeeds, second fails
        def sync_side_effect(keys, skip_history, limit):
            if keys == ["A-1", "A-2"]:
                return  # success
            else:
                raise RuntimeError("Batch sync failed")

        mock_sync.side_effect = sync_side_effect

        # Import and test main function
        from scripts.sync_by_keys import main

        # Mock sys.argv
        with patch("sys.argv", ["sync_by_keys.py", "--file", "test.txt"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with code 1
            assert exc_info.value.code == 1

        # Verify both batches were called (tqdm calls the function for each batch)
        # but the second one should have failed
        assert mock_sync.call_count == 2
        mock_sync.assert_any_call(["A-1", "A-2"], False, None)
        mock_sync.assert_any_call(["A-3", "A-4"], False, None)

    @patch("scripts.sync_by_keys.sync_batch")
    @patch("scripts.sync_by_keys.split_into_batches")
    @patch("scripts.sync_by_keys.read_keys_from_file")
    def test_main_success_all_batches(self, mock_read, mock_split, mock_sync):
        """Test successful processing of all batches."""
        # Setup mocks
        mock_read.return_value = ["A-1", "A-2", "A-3", "A-4"]
        mock_split.return_value = [["A-1", "A-2"], ["A-3", "A-4"]]
        mock_sync.return_value = None  # success

        # Import and test main function
        from scripts.sync_by_keys import main

        # Mock sys.argv
        with patch("sys.argv", ["sync_by_keys.py", "--file", "test.txt"]):
            main()  # Should not raise exception

        # Verify both batches were processed
        assert mock_sync.call_count == 2
        mock_sync.assert_any_call(["A-1", "A-2"], False, None)
        mock_sync.assert_any_call(["A-3", "A-4"], False, None)
