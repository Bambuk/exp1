#!/usr/bin/env python3
"""Test script for full filter functionality in Google Sheets."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from radiator.services.google_sheets_service import GoogleSheetsService
from radiator.services.google_sheets_config import GoogleSheetsConfig


def test_full_filter_functionality():
    """Test the full filter functionality on a sample CSV with more data."""
    print("🧪 Testing Google Sheets full filter functionality...")
    
    # Create test CSV with more data
    test_file = Path("reports/test_full_filter_detailed.csv")
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("Employee,Department,Salary,Experience,Location,Start Date\n")
        f.write("Alice Johnson,Engineering,75000,3,New York,2022-01-15\n")
        f.write("Bob Smith,Marketing,65000,2,San Francisco,2023-03-10\n")
        f.write("Charlie Brown,Engineering,80000,5,Seattle,2021-06-20\n")
        f.write("Diana Prince,HR,60000,4,Chicago,2022-09-05\n")
        f.write("Eve Wilson,Marketing,70000,3,Los Angeles,2022-11-12\n")
        f.write("Frank Miller,Engineering,85000,6,Boston,2020-04-18\n")
        f.write("Grace Lee,Finance,72000,4,Miami,2022-07-25\n")
        f.write("Henry Davis,HR,58000,2,Denver,2023-01-30\n")
        f.write("Ivy Chen,Marketing,68000,3,Austin,2022-12-08\n")
        f.write("Jack Taylor,Engineering,78000,4,Portland,2022-05-14\n")
    
    print(f"✅ Created test CSV with 10 employees: {test_file}")
    
    # Initialize Google Sheets service
    try:
        service = GoogleSheetsService(
            credentials_path=GoogleSheetsConfig.CREDENTIALS_PATH,
            document_id=GoogleSheetsConfig.DOCUMENT_ID
        )
        
        print("✅ Google Sheets service initialized")
        
        # Upload CSV with full filter
        success = service.upload_csv_to_sheet(test_file, "test_full_filter_detailed")
        
        if success:
            print("✅ CSV uploaded successfully with full filter!")
            print("📊 Check your Google Sheets document:")
            print("   - The filter should cover ALL data (11 rows: 1 header + 10 employees)")
            print("   - You should be able to filter by any column")
            print("   - Try filtering by Department (Engineering, Marketing, HR, Finance)")
            print("   - Try filtering by Location or Salary range")
            print("   - The filter should work on ALL rows, not just the header")
        else:
            print("❌ Failed to upload CSV")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Clean up test file
    test_file.unlink()
    print("🧹 Test file cleaned up")
    
    return True


if __name__ == "__main__":
    success = test_full_filter_functionality()
    sys.exit(0 if success else 1)
