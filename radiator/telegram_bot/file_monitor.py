"""File monitoring for reports directory."""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set

from .config import TelegramBotConfig

logger = logging.getLogger(__name__)


class FileMonitor:
    """Monitor files in reports directory for changes."""

    def __init__(self, reports_dir: Path = None):
        self.reports_dir = reports_dir or TelegramBotConfig.get_reports_dir()
        self.state_file = Path("data/.telegram_bot_state.json")
        self.known_files: Set[str] = set()
        self.file_timestamps: Dict[str, float] = {}
        self._load_state()
        # Clean up any upload marker files that might be in the state
        self.cleanup_upload_markers_from_state()

    def _load_state(self):
        """Load known files state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.known_files = set(data.get("known_files", []))
                    self.file_timestamps = data.get("file_timestamps", {})
            except Exception as e:
                print(f"Warning: Could not load state file: {e}")
                self.known_files = set()
                self.file_timestamps = {}

    def _save_state(self):
        """Save current state to file."""
        try:
            data = {
                "known_files": list(self.known_files),
                "file_timestamps": self.file_timestamps,
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save state file: {e}")

    def get_current_files(self) -> Dict[str, float]:
        """Get current files in reports directory with timestamps."""
        if not self.reports_dir.exists():
            return {}

        current_files = {}
        for file_path in self.reports_dir.iterdir():
            if file_path.is_file():
                # Skip upload marker files
                if file_path.name.startswith(".upload_me_"):
                    continue

                extension = file_path.suffix.lower()
                if extension in TelegramBotConfig.MONITORED_EXTENSIONS:
                    file_key = file_path.name
                    current_files[file_key] = file_path.stat().st_mtime

        return current_files

    def get_new_files(self) -> Set[str]:
        """Get list of new files since last check."""
        current_files = self.get_current_files()
        new_files = set()

        for filename, timestamp in current_files.items():
            if filename not in self.known_files:
                new_files.add(filename)
                self.known_files.add(filename)
                self.file_timestamps[filename] = timestamp
            elif timestamp > self.file_timestamps.get(filename, 0):
                # File was modified
                new_files.add(filename)
                self.file_timestamps[filename] = timestamp

        if new_files:
            self._save_state()

        return new_files

    def get_file_path(self, filename: str) -> Optional[Path]:
        """Get full path for a filename."""
        file_path = self.reports_dir / filename
        if file_path.exists():
            return file_path
        return None

    def cleanup_upload_markers_from_state(self):
        """Remove upload marker files from known_files state."""
        original_count = len(self.known_files)
        self.known_files = {
            filename
            for filename in self.known_files
            if not filename.startswith(".upload_me_")
        }
        removed_count = original_count - len(self.known_files)

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} upload marker files from state")
            self._save_state()

    def get_file_info(self, filename: str) -> Optional[Dict]:
        """Get file information."""
        file_path = self.get_file_path(filename)
        if not file_path:
            return None

        try:
            stat = file_path.stat()
            return {
                "name": filename,
                "path": file_path,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "extension": file_path.suffix.lower(),
            }
        except Exception as e:
            print(f"Error getting file info for {filename}: {e}")
            return None

    def cleanup_old_files(self, max_age_days: int = 30):
        """Remove old files from known files list."""
        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        old_files = []

        for filename, timestamp in self.file_timestamps.items():
            if timestamp < cutoff_time:
                old_files.append(filename)

        for filename in old_files:
            self.known_files.discard(filename)
            self.file_timestamps.pop(filename, None)

        if old_files:
            print(f"Cleaned up {len(old_files)} old files from state")
            self._save_state()

    def reset_state(self):
        """Reset monitoring state."""
        self.known_files.clear()
        self.file_timestamps.clear()
        if self.state_file.exists():
            self.state_file.unlink()
        print("File monitor state reset")
