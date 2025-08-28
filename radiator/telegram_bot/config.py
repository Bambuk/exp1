"""Configuration for Telegram bot."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(".env")

class TelegramBotConfig:
    """Configuration class for Telegram bot."""
    
    # Telegram Bot Token (required)
    BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # User ID to send files to (required)
    USER_ID: Optional[int] = None
    
    # Reports directory to monitor
    REPORTS_DIR: Path = Path("reports")
    
    # File extensions to monitor
    MONITORED_EXTENSIONS: set = {".csv", ".png", ".jpg", ".jpeg", ".pdf"}
    
    # Polling interval in seconds
    POLLING_INTERVAL: int = 30
    
    # Maximum file size to send (in bytes, 50MB default)
    MAX_FILE_SIZE: int = 50 * 1024 * 1024
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.BOT_TOKEN:
            print("ERROR: TELEGRAM_BOT_TOKEN environment variable is required")
            return False
        
        try:
            cls.USER_ID = int(os.getenv("TELEGRAM_USER_ID", ""))
        except (ValueError, TypeError):
            print("ERROR: TELEGRAM_USER_ID environment variable must be a valid integer")
            return False
        
        if not cls.USER_ID:
            print("ERROR: TELEGRAM_USER_ID environment variable is required")
            return False
        
        return True
    
    @classmethod
    def print_config(cls):
        """Print current configuration."""
        print("Telegram Bot Configuration:")
        print(f"  Bot Token: {'*' * len(cls.BOT_TOKEN) if cls.BOT_TOKEN else 'NOT SET'}")
        print(f"  User ID: {cls.USER_ID}")
        print(f"  Reports Directory: {cls.REPORTS_DIR}")
        print(f"  Monitored Extensions: {', '.join(cls.MONITORED_EXTENSIONS)}")
        print(f"  Polling Interval: {cls.POLLING_INTERVAL}s")
        print(f"  Max File Size: {cls.MAX_FILE_SIZE / (1024*1024):.1f}MB")
