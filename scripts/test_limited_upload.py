#!/usr/bin/env python3
"""Test script for limited CSV upload."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from radiator.services.google_sheets_config import GoogleSheetsConfig
from radiator.services.google_sheets_service import GoogleSheetsService
from radiator.services.csv_file_monitor import CSVFileMonitor
from radiator.services.csv_processor import CSVProcessor


def main():
    """Test limited CSV upload."""
    print("Testing limited CSV upload...")
    
    # Load configuration
    config = GoogleSheetsConfig()
    
    # Initialize services
    credentials_path = config.get_absolute_credentials_path()
    sheets_service = GoogleSheetsService(
        credentials_path=credentials_path,
        document_id=config.DOCUMENT_ID,
        sheet_prefix=config.SHEET_PREFIX
    )
    
    file_monitor = CSVFileMonitor()
    csv_processor = CSVProcessor()
    
    # Get first 3 CSV files for testing
    current_files = file_monitor.get_current_csv_files()
    test_files = list(current_files.keys())[:3]
    
    print(f"Testing with {len(test_files)} files:")
    for filename in test_files:
        print(f"  - {filename}")
    
    # Process each file
    processed = 0
    failed = 0
    
    for filename in test_files:
        print(f"\nProcessing: {filename}")
        
        file_path = file_monitor.get_file_path(filename)
        if not file_path:
            print(f"  ❌ File not found")
            failed += 1
            continue
        
        # Validate file
        validation = csv_processor.validate_file(file_path)
        if not validation['valid']:
            print(f"  ❌ Validation failed: {validation['errors']}")
            failed += 1
            continue
        
        # Process CSV
        df = csv_processor.process_csv(file_path)
        if df is None:
            print(f"  ❌ Failed to process CSV")
            failed += 1
            continue
        
        print(f"  📊 Data: {df.shape[0]} rows, {df.shape[1]} columns")
        
        # Upload to Google Sheets
        success = sheets_service.upload_csv_to_sheet(file_path)
        if success:
            print(f"  ✅ Successfully uploaded")
            file_monitor.mark_file_processed(filename)
            processed += 1
        else:
            print(f"  ❌ Failed to upload")
            failed += 1
    
    print(f"\nResults:")
    print(f"  Processed: {processed}")
    print(f"  Failed: {failed}")
    
    return processed > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
