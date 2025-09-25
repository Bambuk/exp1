#!/usr/bin/env python3
"""Test script for Google Sheets connection."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from radiator.services.google_sheets_config import GoogleSheetsConfig
from radiator.services.google_sheets_service import GoogleSheetsService


def main():
    """Test Google Sheets connection."""
    print("Testing Google Sheets connection...")
    
    # Load configuration
    config = GoogleSheetsConfig()
    
    # Validate configuration
    if not config.validate():
        print("❌ Configuration validation failed")
        return False
    
    print("✅ Configuration is valid")
    config.print_config()
    
    # Initialize service
    try:
        credentials_path = config.get_absolute_credentials_path()
        service = GoogleSheetsService(
            credentials_path=credentials_path,
            document_id=config.DOCUMENT_ID,
            sheet_prefix=config.SHEET_PREFIX
        )
        print("✅ Google Sheets service initialized")
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        return False
    
    # Test connection
    if service.test_connection():
        print("✅ Connection to Google Sheets successful")
        return True
    else:
        print("❌ Connection to Google Sheets failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
