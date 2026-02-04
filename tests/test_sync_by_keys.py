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
    clear_progress,
    get_progress_file_path,
    load_progress,
    read_keys_from_file,
    save_progress,
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
            "--force-full-history",
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
            "--force-full-history",
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
            "--force-full-history",
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
            "--force-full-history",
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
        assert "--force-full-history" in args

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
        def sync_side_effect(keys, skip_history, limit, force_full_history):
            if keys == ["A-1", "A-2"]:
                return  # success
            else:
                raise RuntimeError("Batch sync failed")

        mock_sync.side_effect = sync_side_effect

        # Import and test main function
        from scripts.sync_by_keys import main

        # Mock sys.argv and clear progress
        with patch("scripts.sync_by_keys.load_progress") as mock_load:
            mock_load.return_value = None  # no saved progress
            with patch("sys.argv", ["sync_by_keys.py", "--file", "test.txt"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()

                # Should exit with code 1
                assert exc_info.value.code == 1

            # Verify both batches were called (tqdm calls the function for each batch)
            # but the second one should have failed
            assert mock_sync.call_count == 2
            # Note: force_full_history defaults to True
            mock_sync.assert_any_call(["A-1", "A-2"], False, None, True)
            mock_sync.assert_any_call(["A-3", "A-4"], False, None, True)

    @patch("scripts.sync_by_keys.sync_batch")
    @patch("scripts.sync_by_keys.split_into_batches")
    @patch("scripts.sync_by_keys.read_keys_from_file")
    def test_main_success_all_batches(self, mock_read, mock_split, mock_sync):
        """Test successful processing of all batches."""
        # Setup mocks
        mock_read.return_value = ["A-1", "A-2", "A-3", "A-4"]
        mock_split.return_value = [["A-1", "A-2"], ["A-3", "A-4"]]
        mock_sync.return_value = None  # success

        # Mock no saved progress
        with patch("scripts.sync_by_keys.load_progress") as mock_load:
            mock_load.return_value = None  # no saved progress

            # Import and test main function
            from scripts.sync_by_keys import main

            # Mock sys.argv
            with patch("sys.argv", ["sync_by_keys.py", "--file", "test.txt"]):
                main()  # Should not raise exception

            # Verify both batches were processed
            assert mock_sync.call_count == 2
            # Note: force_full_history defaults to True
            mock_sync.assert_any_call(["A-1", "A-2"], False, None, True)
            mock_sync.assert_any_call(["A-3", "A-4"], False, None, True)


class TestProgressFunctions:
    """Test progress tracking functions."""

    def test_get_progress_file_path(self):
        """Test progress file path generation."""
        # Test with relative path
        path = get_progress_file_path("data/input/keys.txt")
        assert str(path).startswith("data/.progress/keys.txt.")
        assert str(path).endswith(".progress")

        # Test with absolute path
        abs_path = Path("/home/user/data/input/keys.txt").absolute()
        path = get_progress_file_path(str(abs_path))
        assert str(path).startswith("data/.progress/keys.txt.")
        assert str(path).endswith(".progress")

    def test_save_and_load_progress(self):
        """Test saving and loading progress."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            temp_file = f.name

        try:
            # Save progress
            save_progress(temp_file, 5, 10)

            # Load progress
            progress = load_progress(temp_file)
            assert progress == (5, 10)

            # Test non-existent file
            progress = load_progress("non_existent_file.txt")
            assert progress is None

        finally:
            # Clean up progress file
            progress_file = get_progress_file_path(temp_file)
            if progress_file.exists():
                progress_file.unlink()

    def test_clear_progress(self):
        """Test clearing progress."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            temp_file = f.name

        try:
            # Save progress first
            save_progress(temp_file, 3, 8)
            progress_file = get_progress_file_path(temp_file)
            assert progress_file.exists()

            # Clear progress
            clear_progress(temp_file)
            assert not progress_file.exists()

            # Clear non-existent progress (should not fail)
            clear_progress("non_existent_file.txt")

        finally:
            # Clean up if needed
            progress_file = get_progress_file_path(temp_file)
            if progress_file.exists():
                progress_file.unlink()


class TestMainWithProgress:
    """Test main function with progress tracking."""

    @patch("scripts.sync_by_keys.sync_batch")
    @patch("scripts.sync_by_keys.split_into_batches")
    @patch("scripts.sync_by_keys.read_keys_from_file")
    def test_main_continues_from_saved_progress(self, mock_read, mock_split, mock_sync):
        """Test that main continues from saved progress."""
        # Setup mocks
        mock_read.return_value = ["A-1", "A-2", "A-3", "A-4", "A-5", "A-6"]
        mock_split.return_value = [["A-1", "A-2"], ["A-3", "A-4"], ["A-5", "A-6"]]
        mock_sync.return_value = None  # success

        # Mock saved progress: completed 1 batch out of 3
        with patch("scripts.sync_by_keys.load_progress") as mock_load:
            mock_load.return_value = (1, 3)  # completed batch 1, total 3

            # Import and test main function
            from scripts.sync_by_keys import main

            # Mock sys.argv
            with patch("sys.argv", ["sync_by_keys.py", "--file", "test.txt"]):
                main()

            # Should start from batch 2 (index 1)
            assert mock_sync.call_count == 2  # batches 2 and 3
            # Note: force_full_history defaults to True
            mock_sync.assert_any_call(["A-3", "A-4"], False, None, True)
            mock_sync.assert_any_call(["A-5", "A-6"], False, None, True)

    @patch("scripts.sync_by_keys.sync_batch")
    @patch("scripts.sync_by_keys.split_into_batches")
    @patch("scripts.sync_by_keys.read_keys_from_file")
    def test_main_resets_progress_with_flag(self, mock_read, mock_split, mock_sync):
        """Test that --reset-progress flag resets progress."""
        # Setup mocks
        mock_read.return_value = ["A-1", "A-2", "A-3", "A-4"]
        mock_split.return_value = [["A-1", "A-2"], ["A-3", "A-4"]]
        mock_sync.return_value = None  # success

        # Mock saved progress exists
        with patch("scripts.sync_by_keys.load_progress") as mock_load, patch(
            "scripts.sync_by_keys.clear_progress"
        ) as mock_clear:
            mock_load.return_value = (1, 2)  # completed batch 1

            # Import and test main function
            from scripts.sync_by_keys import main

            # Mock sys.argv with --reset-progress
            with patch(
                "sys.argv",
                ["sync_by_keys.py", "--file", "test.txt", "--reset-progress"],
            ):
                main()

            # Should clear progress and start from beginning (called twice: reset + success)
            assert mock_clear.call_count == 2
            mock_clear.assert_any_call("test.txt")
            assert mock_sync.call_count == 2  # both batches
            # Note: force_full_history defaults to True
            mock_sync.assert_any_call(["A-1", "A-2"], False, None, True)
            mock_sync.assert_any_call(["A-3", "A-4"], False, None, True)

    @patch("scripts.sync_by_keys.sync_batch")
    @patch("scripts.sync_by_keys.split_into_batches")
    @patch("scripts.sync_by_keys.read_keys_from_file")
    def test_progress_cleared_on_success(self, mock_read, mock_split, mock_sync):
        """Test that progress is cleared on successful completion."""
        # Setup mocks
        mock_read.return_value = ["A-1", "A-2"]
        mock_split.return_value = [["A-1", "A-2"]]
        mock_sync.return_value = None  # success

        # Import and test main function
        from scripts.sync_by_keys import main

        with patch("scripts.sync_by_keys.clear_progress") as mock_clear:
            # Mock sys.argv
            with patch("sys.argv", ["sync_by_keys.py", "--file", "test.txt"]):
                main()

            # Should clear progress on success
            mock_clear.assert_called_once_with("test.txt")

    @patch("scripts.sync_by_keys.sync_batch")
    @patch("scripts.sync_by_keys.split_into_batches")
    @patch("scripts.sync_by_keys.read_keys_from_file")
    def test_batch_count_changed_resets_progress(
        self, mock_read, mock_split, mock_sync
    ):
        """Test that changed batch count resets progress."""
        # Setup mocks
        mock_read.return_value = ["A-1", "A-2", "A-3", "A-4", "A-5", "A-6"]
        mock_split.return_value = [
            ["A-1", "A-2"],
            ["A-3", "A-4"],
            ["A-5", "A-6"],
        ]  # 3 batches

        # Mock saved progress with different batch count
        with patch("scripts.sync_by_keys.load_progress") as mock_load:
            mock_load.return_value = (2, 2)  # saved: 2 batches, current: 3 batches

            # Import and test main function
            from scripts.sync_by_keys import main

            # Mock sys.argv
            with patch("sys.argv", ["sync_by_keys.py", "--file", "test.txt"]):
                main()

            # Should start from beginning due to batch count mismatch
            assert mock_sync.call_count == 3  # all 3 batches
            # Note: force_full_history defaults to True
            mock_sync.assert_any_call(["A-1", "A-2"], False, None, True)
            mock_sync.assert_any_call(["A-3", "A-4"], False, None, True)
            mock_sync.assert_any_call(["A-5", "A-6"], False, None, True)
