"""Configuration for Google Sheets CSV uploader."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(".env")


class GoogleSheetsConfig:
    """Configuration class for Google Sheets CSV uploader."""

    # Google Sheets API settings
    CREDENTIALS_PATH: str = os.getenv(
        "GOOGLE_SHEETS_CREDENTIALS_PATH", "sheet-api-key.json"
    )
    DOCUMENT_ID: str = os.getenv(
        "GOOGLE_SHEETS_DOCUMENT_ID", "1lmN2L9UORwOPycpRZNX_TKl93S8WSh71YmKuyYDrL7g"
    )
    SHEET_PREFIX: str = os.getenv("GOOGLE_SHEETS_SHEET_PREFIX", "Report_")

    # File monitoring settings
    @classmethod
    def get_reports_dir(cls) -> Path:
        """Get reports directory from settings."""
        from radiator.core.config import settings

        return Path(settings.REPORTS_DIR)

    POLLING_INTERVAL: int = int(os.getenv("GOOGLE_SHEETS_POLLING_INTERVAL", "30"))

    # CSV processing settings
    MAX_FILE_SIZE: int = int(
        os.getenv("GOOGLE_SHEETS_MAX_FILE_SIZE", str(50 * 1024 * 1024))
    )  # 50MB
    SUPPORTED_ENCODINGS: list = [
        "utf-8",
        "utf-8-sig",
        "windows-1251",
        "cp1251",
        "iso-8859-1",
    ]

    # Google Sheets limits
    MAX_ROWS: int = 1000000
    MAX_COLUMNS: int = 1000
    MAX_SHEET_NAME_LENGTH: int = 100

    # Logging settings
    LOG_LEVEL: str = os.getenv("GOOGLE_SHEETS_LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("GOOGLE_SHEETS_LOG_FILE", "logs/google_sheets_bot.log")

    # State file for tracking processed files
    STATE_FILE: str = os.getenv(
        "GOOGLE_SHEETS_STATE_FILE", "data/.google_sheets_state.json"
    )

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        errors = []

        # Check credentials file
        if not os.path.exists(cls.CREDENTIALS_PATH):
            errors.append(f"Credentials file not found: {cls.CREDENTIALS_PATH}")

        # Check document ID
        if not cls.DOCUMENT_ID:
            errors.append("GOOGLE_SHEETS_DOCUMENT_ID environment variable is required")

        # Check reports directory
        reports_dir = cls.get_reports_dir()
        if not reports_dir.exists():
            errors.append(f"Reports directory does not exist: {reports_dir}")

        # Check polling interval
        if cls.POLLING_INTERVAL <= 0:
            errors.append("POLLING_INTERVAL must be positive")

        # Check file size limit
        if cls.MAX_FILE_SIZE <= 0:
            errors.append("MAX_FILE_SIZE must be positive")

        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  ERROR: {error}")
            return False

        return True

    @classmethod
    def print_config(cls):
        """Print current configuration."""
        print("Google Sheets CSV Uploader Configuration:")
        print(f"  Credentials Path: {cls.CREDENTIALS_PATH}")
        print(f"  Document ID: {cls.DOCUMENT_ID}")
        print(f"  Sheet Prefix: {cls.SHEET_PREFIX}")
        print(f"  Reports Directory: {cls.get_reports_dir()}")
        print(f"  Polling Interval: {cls.POLLING_INTERVAL}s")
        print(f"  Max File Size: {cls.MAX_FILE_SIZE / (1024*1024):.1f}MB")
        print(f"  Max Rows: {cls.MAX_ROWS:,}")
        print(f"  Max Columns: {cls.MAX_COLUMNS}")
        print(f"  Log Level: {cls.LOG_LEVEL}")
        print(f"  Log File: {cls.LOG_FILE}")
        print(f"  State File: {cls.STATE_FILE}")

    @classmethod
    def get_absolute_credentials_path(cls) -> str:
        """Get absolute path to credentials file."""
        if os.path.isabs(cls.CREDENTIALS_PATH):
            return cls.CREDENTIALS_PATH
        return str(Path.cwd() / cls.CREDENTIALS_PATH)

    @classmethod
    def ensure_log_directory(cls):
        """Ensure log directory exists."""
        log_path = Path(cls.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
