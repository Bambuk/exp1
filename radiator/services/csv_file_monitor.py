"""File monitor for CSV files in reports directory."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from .google_sheets_config import GoogleSheetsConfig

logger = logging.getLogger(__name__)


class CSVFileMonitor:
    """Monitor CSV files in reports directory for changes."""

    def __init__(self, reports_dir: Path = None):
        """
        Initialize CSV file monitor.

        Args:
            reports_dir: Directory to monitor (defaults to config value)
        """
        self.reports_dir = reports_dir or GoogleSheetsConfig.REPORTS_DIR
        self.state_file = Path(GoogleSheetsConfig.STATE_FILE)
        self.known_files: Set[str] = set()
        self.file_timestamps: Dict[str, float] = {}
        self.processed_files: Set[str] = set()
        self._load_state()

    def _load_state(self):
        """Load known files state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.known_files = set(data.get("known_files", []))
                    self.file_timestamps = data.get("file_timestamps", {})
                    self.processed_files = set(data.get("processed_files", []))
                    logger.info(
                        f"Loaded state: {len(self.known_files)} known files, {len(self.processed_files)} processed"
                    )
            except Exception as e:
                logger.warning(f"Could not load state file: {e}")
                self.known_files = set()
                self.file_timestamps = {}
                self.processed_files = set()

    def _save_state(self):
        """Save current state to file."""
        try:
            data = {
                "known_files": list(self.known_files),
                "file_timestamps": self.file_timestamps,
                "processed_files": list(self.processed_files),
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("State saved successfully")
        except Exception as e:
            logger.error(f"Could not save state file: {e}")

    def get_current_csv_files(self) -> Dict[str, float]:
        """
        Get current CSV files in reports directory with timestamps.

        Returns:
            Dictionary mapping filename to modification timestamp
        """
        if not self.reports_dir.exists():
            logger.warning(f"Reports directory does not exist: {self.reports_dir}")
            return {}

        current_files = {}
        for file_path in self.reports_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == ".csv":
                # Check file size
                try:
                    file_size = file_path.stat().st_size
                    if file_size > GoogleSheetsConfig.MAX_FILE_SIZE:
                        logger.warning(
                            f"File {file_path.name} is too large ({file_size / (1024*1024):.1f}MB), skipping"
                        )
                        continue

                    file_key = file_path.name
                    current_files[file_key] = file_path.stat().st_mtime
                except OSError as e:
                    logger.warning(f"Could not access file {file_path.name}: {e}")
                    continue

        return current_files

    def get_new_csv_files(self) -> List[str]:
        """
        Get list of new or modified CSV files since last check.

        Returns:
            List of new or modified filenames
        """
        current_files = self.get_current_csv_files()
        new_files = []

        for filename, timestamp in current_files.items():
            is_new = filename not in self.known_files
            is_modified = (
                filename in self.file_timestamps
                and timestamp > self.file_timestamps.get(filename, 0)
            )

            if is_new or is_modified:
                new_files.append(filename)
                self.known_files.add(filename)
                self.file_timestamps[filename] = timestamp
                logger.info(
                    f"Found {'new' if is_new else 'modified'} CSV file: {filename}"
                )

        if new_files:
            self._save_state()

        return new_files

    def get_unprocessed_files(self) -> List[str]:
        """
        Get list of CSV files that haven't been processed yet.

        Returns:
            List of unprocessed filenames
        """
        current_files = self.get_current_csv_files()
        unprocessed = []

        for filename in current_files.keys():
            if filename not in self.processed_files:
                unprocessed.append(filename)

        return unprocessed

    def get_files_with_upload_markers(self) -> List[str]:
        """
        Get list of CSV files that have upload markers (requested for Google Sheets upload).

        Returns:
            List of filenames with upload markers
        """
        if not self.reports_dir.exists():
            return []

        files_with_markers = []

        # Look for marker files
        for file_path in self.reports_dir.iterdir():
            if file_path.is_file() and file_path.name.startswith(".upload_me_"):
                # Extract original filename from marker
                original_filename = file_path.name[11:]  # Remove '.upload_me_' prefix

                # Check if original file still exists
                original_file_path = self.reports_dir / original_filename
                if original_file_path.exists() and original_filename.endswith(".csv"):
                    files_with_markers.append(original_filename)

        return files_with_markers

    def remove_upload_marker(self, filename: str) -> bool:
        """
        Remove upload marker for a specific file.

        Args:
            filename: Name of the file to remove marker for

        Returns:
            True if marker was removed, False otherwise
        """
        marker_filename = f".upload_me_{filename}"
        marker_path = self.reports_dir / marker_filename

        try:
            if marker_path.exists():
                marker_path.unlink()
                logger.info(f"Removed upload marker for {filename}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove marker for {filename}: {e}")
            return False

    def mark_file_processed(self, filename: str):
        """
        Mark file as processed.

        Args:
            filename: Name of the processed file
        """
        self.processed_files.add(filename)
        self._save_state()
        logger.debug(f"Marked file as processed: {filename}")

    def mark_file_failed(self, filename: str, error: str):
        """
        Mark file as failed processing.

        Args:
            filename: Name of the failed file
            error: Error message
        """
        logger.error(f"Failed to process file {filename}: {error}")
        # Don't mark as processed, so it can be retried later

    def get_file_path(self, filename: str) -> Optional[Path]:
        """
        Get full path for a filename.

        Args:
            filename: Name of the file

        Returns:
            Full path to file or None if not found
        """
        file_path = self.reports_dir / filename
        if file_path.exists():
            return file_path
        return None

    def get_file_info(self, filename: str) -> Optional[Dict]:
        """
        Get file information.

        Args:
            filename: Name of the file

        Returns:
            Dictionary with file information or None if not found
        """
        file_path = self.get_file_path(filename)
        if not file_path:
            return None

        try:
            stat = file_path.stat()
            return {
                "path": file_path,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "created": datetime.fromtimestamp(stat.st_ctime),
                "is_processed": filename in self.processed_files,
            }
        except OSError as e:
            logger.error(f"Could not get file info for {filename}: {e}")
            return None

    def cleanup_old_files(self, max_age_days: int = 30):
        """
        Clean up old file records from state.

        Args:
            max_age_days: Maximum age of file records to keep
        """
        try:
            current_files = self.get_current_csv_files()
            current_filenames = set(current_files.keys())

            # Remove files that no longer exist
            files_to_remove = []
            for filename in self.known_files:
                if filename not in current_filenames:
                    files_to_remove.append(filename)

            for filename in files_to_remove:
                self.known_files.discard(filename)
                self.file_timestamps.pop(filename, None)
                self.processed_files.discard(filename)

            if files_to_remove:
                logger.info(f"Cleaned up {len(files_to_remove)} old file records")
                self._save_state()

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def get_stats(self) -> Dict[str, int]:
        """
        Get monitoring statistics.

        Returns:
            Dictionary with statistics
        """
        current_files = self.get_current_csv_files()
        return {
            "total_files": len(current_files),
            "known_files": len(self.known_files),
            "processed_files": len(self.processed_files),
            "unprocessed_files": len(
                [f for f in current_files.keys() if f not in self.processed_files]
            ),
        }
