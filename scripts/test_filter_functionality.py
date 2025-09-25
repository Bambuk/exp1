#!/usr/bin/env python3
"""Test script for Google Sheets filter functionality."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from radiator.services.google_sheets_service import GoogleSheetsService
from radiator.services.google_sheets_config import GoogleSheetsConfig


def test_filter_functionality():
    """Test the filter functionality on a sample CSV."""
    print("🧪 Testing Google Sheets filter functionality...")
    
    # Create test CSV with more data
    test_file = Path("reports/test_filter_detailed.csv")
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("Product,Category,Price,Stock,Rating,Date\n")
        f.write("Laptop,Electronics,999.99,50,4.5,2025-01-01\n")
        f.write("Phone,Electronics,699.99,100,4.2,2025-01-02\n")
        f.write("Book,Education,19.99,200,4.8,2025-01-03\n")
        f.write("Chair,Furniture,149.99,75,4.0,2025-01-04\n")
        f.write("Table,Furniture,299.99,25,4.3,2025-01-05\n")
        f.write("Headphones,Electronics,199.99,150,4.6,2025-01-06\n")
        f.write("Desk,Furniture,399.99,30,4.1,2025-01-07\n")
        f.write("Monitor,Electronics,299.99,40,4.4,2025-01-08\n")
    
    print(f"✅ Created test CSV: {test_file}")
    
    # Initialize Google Sheets service
    try:
        service = GoogleSheetsService(
            credentials_path=GoogleSheetsConfig.CREDENTIALS_PATH,
            document_id=GoogleSheetsConfig.DOCUMENT_ID
        )
        
        print("✅ Google Sheets service initialized")
        
        # Upload CSV with filter
        success = service.upload_csv_to_sheet(test_file, "test_filter_detailed")
        
        if success:
            print("✅ CSV uploaded successfully with filter!")
            print("📊 Check your Google Sheets document - the first row should have filter dropdowns")
            print("🔍 You should be able to filter by Product, Category, Price, Stock, Rating, or Date")
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
    success = test_filter_functionality()
    sys.exit(0 if success else 1)
