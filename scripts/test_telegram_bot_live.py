#!/usr/bin/env python3
"""Live test script for Telegram bot with callback support."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from radiator.telegram_bot.main import TelegramBotWithCallbacks
from radiator.telegram_bot.config import TelegramBotConfig


async def main():
    """Main test function."""
    print("🧪 Testing Telegram bot with callback support live...")
    
    # Validate configuration
    if not TelegramBotConfig.validate():
        print("❌ Telegram bot configuration invalid")
        return False
    
    print("✅ Configuration valid")
    print("🤖 Starting bot with callback support...")
    print("📱 Send a message to the bot to test callback queries")
    print("⏹️  Press Ctrl+C to stop")
    
    try:
        # Create and start bot with callbacks
        bot_with_callbacks = TelegramBotWithCallbacks()
        await bot_with_callbacks.start_monitoring_with_callbacks()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
