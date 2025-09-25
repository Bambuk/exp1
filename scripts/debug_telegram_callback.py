#!/usr/bin/env python3
"""Debug script for Telegram bot callback queries."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from radiator.telegram_bot.config import TelegramBotConfig
from telegram.ext import Application, CallbackQueryHandler
from telegram import Bot


class DebugCallbackHandler:
    """Debug callback query handler."""
    
    def __init__(self):
        self.bot = Bot(token=TelegramBotConfig.BOT_TOKEN)
    
    async def callback_query_handler(self, update, context):
        """Handle callback queries with debug logging."""
        query = update.callback_query
        print(f"🔔 CALLBACK RECEIVED: {query.data}")
        print(f"   Query ID: {query.id}")
        print(f"   From user: {query.from_user.username if query.from_user else 'Unknown'}")
        print(f"   Message ID: {query.message.message_id if query.message else 'Unknown'}")
        
        # Answer the callback query
        await query.answer("✅ Callback received!")
        
        # Handle the callback
        if query.data.startswith("upload_csv:"):
            filename = query.data.split(":", 1)[1]
            print(f"📁 Processing upload request for: {filename}")
            
            # Create marker file
            marker_filename = f".upload_me_{filename}"
            marker_path = Path("reports") / marker_filename
            
            try:
                with open(marker_path, 'w', encoding='utf-8') as f:
                    f.write(f"Upload request for {filename}\n")
                    f.write(f"Created at: 2025-09-25T21:00:00\n")
                
                print(f"✅ Marker file created: {marker_filename}")
                await query.edit_message_text(f"✅ Файл {filename} добавлен в очередь загрузки в Google Sheets")
                
            except Exception as e:
                print(f"❌ Error creating marker: {e}")
                await query.edit_message_text(f"❌ Ошибка создания маркера для {filename}")
        else:
            print(f"❓ Unknown callback data: {query.data}")
            await query.edit_message_text("❌ Неизвестная команда")


async def main():
    """Main function."""
    print("🐛 Debug Telegram bot callback queries")
    print("📱 Send a message to the bot and click the button")
    print("⏹️  Press Ctrl+C to stop")
    
    # Validate configuration
    if not TelegramBotConfig.validate():
        print("❌ Configuration invalid")
        return False
    
    # Create debug handler
    debug_handler = DebugCallbackHandler()
    
    # Create application
    application = Application.builder().token(TelegramBotConfig.BOT_TOKEN).build()
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(debug_handler.callback_query_handler))
    
    # Start the application
    await application.initialize()
    await application.start()
    
    print("✅ Debug bot started with callback support")
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Debug bot stopped")
    finally:
        await application.stop()
        await application.shutdown()
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
