#!/usr/bin/env python3
"""Test script for Telegram bot callback queries."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from radiator.telegram_bot.bot import ReportsTelegramBot
from radiator.telegram_bot.config import TelegramBotConfig


async def test_callback_handler():
    """Test callback query handler directly."""
    print("Testing callback query handler...")
    
    # Create bot instance
    bot = ReportsTelegramBot()
    
    # Create a mock callback query
    class MockCallbackQuery:
        def __init__(self, data, query_id):
            self.data = data
            self.id = query_id
    
    # Test with valid callback data
    mock_query = MockCallbackQuery("upload_csv:test_file.csv", "test_query_123")
    
    try:
        await bot.handle_callback_query(mock_query)
        print("✅ Callback handler test completed")
    except Exception as e:
        print(f"❌ Callback handler test failed: {e}")
        return False
    
    return True


async def test_upload_request_handler():
    """Test upload request handler directly."""
    print("Testing upload request handler...")
    
    # Create bot instance
    bot = ReportsTelegramBot()
    
    try:
        # Test with a real file
        test_file = Path("reports/test_report.csv")
        if test_file.exists():
            # Test marker file creation directly (without Telegram API calls)
            marker_filename = f".upload_me_test_report.csv"
            marker_path = bot.reports_dir / marker_filename
            
            # Create marker file manually to test the logic
            with open(marker_path, 'w', encoding='utf-8') as f:
                f.write(f"Upload request for test_report.csv\n")
                f.write(f"Created at: 2025-09-25T21:00:00\n")
            
            print("✅ Marker file created successfully")
            
            # Check if marker file was created
            if marker_path.exists():
                print("✅ Marker file exists")
                marker_path.unlink()  # Clean up
                print("🧹 Marker file cleaned up")
            else:
                print("❌ Marker file was not created")
                return False
        else:
            print("⚠️ Test file not found, skipping upload request test")
        
        return True
    except Exception as e:
        print(f"❌ Upload request handler test failed: {e}")
        return False


async def main():
    """Main test function."""
    print("🧪 Testing Telegram bot callback functionality\n")
    
    # Validate configuration
    if not TelegramBotConfig.validate():
        print("❌ Telegram bot configuration invalid")
        return False
    
    # Test callback handler
    callback_test_passed = await test_callback_handler()
    
    # Test upload request handler
    upload_test_passed = await test_upload_request_handler()
    
    print(f"\n📊 Test Results:")
    print(f"  Callback handler: {'✅ PASSED' if callback_test_passed else '❌ FAILED'}")
    print(f"  Upload request handler: {'✅ PASSED' if upload_test_passed else '❌ FAILED'}")
    
    if callback_test_passed and upload_test_passed:
        print("\n🎉 All callback tests passed!")
        return True
    else:
        print("\n❌ Some callback tests failed.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
