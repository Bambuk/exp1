"""Main entry point for Telegram bot."""

import asyncio
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from radiator.telegram_bot.bot import ReportsTelegramBot
from radiator.telegram_bot.config import TelegramBotConfig
from radiator.telegram_bot.file_monitor import FileMonitor


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Telegram bot for sending new report files')
    parser.add_argument('--test', action='store_true', help='Test bot connection only')
    parser.add_argument('--reset', action='store_true', help='Reset file monitoring state')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old files from state')
    parser.add_argument('--config', action='store_true', help='Show current configuration')
    
    args = parser.parse_args()
    
    # Validate configuration
    if not TelegramBotConfig.validate():
        sys.exit(1)
    
    # Show configuration if requested
    if args.config:
        TelegramBotConfig.print_config()
        return
    
    # Create bot instance
    bot = ReportsTelegramBot()
    
    try:
        if args.test:
            # Test connection only
            print("Testing bot connection...")
            success = await bot.test_connection()
            if success:
                print("✅ Bot connection test successful!")
            else:
                print("❌ Bot connection test failed!")
                sys.exit(1)
            return
        
        if args.reset:
            # Reset file monitoring state
            print("Resetting file monitoring state...")
            bot.file_monitor.reset_state()
            print("✅ File monitoring state reset!")
            return
        
        if args.cleanup:
            # Clean up old files from state
            print("Cleaning up old files from state...")
            bot.cleanup()
            print("✅ Cleanup completed!")
            return
        
        # Start monitoring
        print("Starting Telegram bot...")
        await bot.start_monitoring()
        
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        bot.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
