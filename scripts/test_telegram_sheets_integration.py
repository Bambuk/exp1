#!/usr/bin/env python3
"""Test script for Telegram bot and Google Sheets integration."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from radiator.services.csv_file_monitor import CSVFileMonitor


def test_marker_system():
    """Test the marker file system."""
    print("Testing marker file system...")
    
    # Initialize file monitor
    file_monitor = CSVFileMonitor()
    
    # Create a test marker file
    test_filename = "test_report.csv"
    marker_filename = f".upload_me_{test_filename}"
    marker_path = file_monitor.reports_dir / marker_filename
    
    try:
        # Create marker file
        with open(marker_path, 'w', encoding='utf-8') as f:
            f.write(f"Upload request for {test_filename}\n")
            f.write(f"Created at: 2025-09-25T21:00:00\n")
        
        print(f"✅ Created marker file: {marker_filename}")
        
        # Test getting files with markers
        files_with_markers = file_monitor.get_files_with_upload_markers()
        print(f"📋 Files with markers: {files_with_markers}")
        
        if test_filename in files_with_markers:
            print("✅ Marker detection working correctly")
        else:
            print("❌ Marker detection failed")
            return False
        
        # Test removing marker
        success = file_monitor.remove_upload_marker(test_filename)
        if success:
            print("✅ Marker removal working correctly")
        else:
            print("❌ Marker removal failed")
            return False
        
        # Verify marker is removed
        files_with_markers_after = file_monitor.get_files_with_upload_markers()
        if test_filename not in files_with_markers_after:
            print("✅ Marker successfully removed")
        else:
            print("❌ Marker still present after removal")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error during marker test: {e}")
        return False
    finally:
        # Cleanup
        if marker_path.exists():
            marker_path.unlink()
            print("🧹 Cleaned up test marker file")


def test_google_sheets_integration():
    """Test Google Sheets integration with markers."""
    print("\nTesting Google Sheets integration...")
    
    try:
        from radiator.services.google_sheets_config import GoogleSheetsConfig
        from radiator.services.google_sheets_service import GoogleSheetsService
        from radiator.services.csv_processor import CSVProcessor
        
        # Initialize services
        config = GoogleSheetsConfig()
        if not config.validate():
            print("❌ Google Sheets configuration invalid")
            return False
        
        credentials_path = config.get_absolute_credentials_path()
        sheets_service = GoogleSheetsService(
            credentials_path=credentials_path,
            document_id=config.DOCUMENT_ID,
            sheet_prefix=config.SHEET_PREFIX
        )
        
        # Test connection
        if not sheets_service.test_connection():
            print("❌ Google Sheets connection failed")
            return False
        
        print("✅ Google Sheets connection successful")
        
        # Test CSV processor
        csv_processor = CSVProcessor()
        test_file = Path("reports/test_report.csv")
        
        if test_file.exists():
            validation = csv_processor.validate_file(test_file)
            if validation['valid']:
                print("✅ CSV processor working correctly")
            else:
                print(f"❌ CSV validation failed: {validation['errors']}")
                return False
        else:
            print("⚠️ Test CSV file not found, skipping CSV processor test")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during Google Sheets integration test: {e}")
        return False


def main():
    """Main test function."""
    print("🧪 Testing Telegram bot and Google Sheets integration\n")
    
    # Test marker system
    marker_test_passed = test_marker_system()
    
    # Test Google Sheets integration
    sheets_test_passed = test_google_sheets_integration()
    
    print(f"\n📊 Test Results:")
    print(f"  Marker system: {'✅ PASSED' if marker_test_passed else '❌ FAILED'}")
    print(f"  Google Sheets: {'✅ PASSED' if sheets_test_passed else '❌ FAILED'}")
    
    if marker_test_passed and sheets_test_passed:
        print("\n🎉 All tests passed! Integration is ready to use.")
        return True
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
