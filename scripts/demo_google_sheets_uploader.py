#!/usr/bin/env python3
"""Demo script for Google Sheets CSV Uploader."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from radiator.services.google_sheets_config import GoogleSheetsConfig
from radiator.services.google_sheets_service import GoogleSheetsService
from radiator.services.csv_file_monitor import CSVFileMonitor


def main():
    """Demo the Google Sheets CSV Uploader."""
    print("🚀 Google Sheets CSV Uploader Demo")
    print("=" * 50)
    
    # Load configuration
    config = GoogleSheetsConfig()
    print(f"📋 Configuration loaded")
    print(f"   Document ID: {config.DOCUMENT_ID}")
    print(f"   Reports Directory: {config.REPORTS_DIR}")
    print(f"   Sheet Prefix: {config.SHEET_PREFIX}")
    
    # Initialize services
    print(f"\n🔧 Initializing services...")
    credentials_path = config.get_absolute_credentials_path()
    sheets_service = GoogleSheetsService(
        credentials_path=credentials_path,
        document_id=config.DOCUMENT_ID,
        sheet_prefix=config.SHEET_PREFIX
    )
    
    file_monitor = CSVFileMonitor()
    
    # Test connection
    print(f"🔗 Testing connection to Google Sheets...")
    if sheets_service.test_connection():
        print(f"   ✅ Connected successfully")
    else:
        print(f"   ❌ Connection failed")
        return False
    
    # Show statistics
    print(f"\n📊 Current statistics:")
    stats = file_monitor.get_stats()
    print(f"   Total files: {stats['total_files']}")
    print(f"   Known files: {stats['known_files']}")
    print(f"   Processed files: {stats['processed_files']}")
    print(f"   Unprocessed files: {stats['unprocessed_files']}")
    
    # Show some example files
    print(f"\n📁 Example files in reports directory:")
    current_files = file_monitor.get_current_csv_files()
    example_files = list(current_files.keys())[:5]
    for filename in example_files:
        file_info = file_monitor.get_file_info(filename)
        if file_info:
            size_mb = file_info['size'] / (1024 * 1024)
            print(f"   📄 {filename} ({size_mb:.1f}MB)")
    
    print(f"\n✨ Demo completed successfully!")
    print(f"\n💡 To start monitoring, run:")
    print(f"   python3 scripts/google_sheets_csv_uploader.py --monitor")
    print(f"\n💡 To process all files, run:")
    print(f"   python3 scripts/google_sheets_csv_uploader.py --process-all")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
