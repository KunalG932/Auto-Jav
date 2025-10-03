import asyncio
import os
import logging
from typing import Optional
from pyrogram.client import Client
from pyrogram import filters
from pyrogram.handlers.message_handler import MessageHandler
from .config import SETTINGS
from .clients import create_clients
from .db import client as mongo_client, is_working, set_working
from .handlers import alive_command, logs_command, status_command, start_command
from .handlers.commands import set_clients
from .processors import process_item, check_for_new_items
from .api.api_health import warm_up_api

LOG = logging.getLogger("AABv2")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('logging_v2.txt')]
)

bot: Optional[Client] = None
file_client: Optional[Client] = None

async def worker_loop():
    global bot, file_client
    
    while True:
        try:
            if not is_working():
                set_working(True)
                
                try:
                    new_items = check_for_new_items()
                    
                    if new_items:
                        LOG.info(f"Processing {len(new_items)} new items")
                        for item in new_items:
                            await process_item(bot, file_client, item)
                    else:
                        LOG.debug("No new items found")
                        
                except Exception as process_error:
                    LOG.error(f"Error in worker loop processing: {process_error}")
                finally:
                    set_working(False)
            else:
                LOG.debug("Bot is already working, skipping this cycle")
                
        except Exception as loop_error:
            LOG.error(f"Error in worker loop: {loop_error}")
        
        await asyncio.sleep(SETTINGS.check_interval_sec)

async def main():
    global bot, file_client
    
    try:
        mongo_client.admin.command('ping')
        LOG.info("✅ MongoDB connected successfully")
    except Exception as e:
        LOG.critical(f"❌ MongoDB connection failed: {e}")
        return

    try:
        try:
            bot, file_client = create_clients()
            set_clients(bot, file_client)
        except Exception as e:
            LOG.critical(f"Failed to create Telegram clients: {e}")
            return

        LOG.info("Starting Telegram clients...")
        if file_client:
            try:
                await file_client.start()
            except Exception as e:
                LOG.critical(f"Failed to start file_client: {e}")
                return

        try:
            await bot.start()
        except Exception as e:
            LOG.critical(f"Failed to start main bot: {e}")
            return

        try:
            owner_filter = filters.user(list(SETTINGS.owner_ids))
            bot.add_handler(MessageHandler(alive_command, filters.command("alive") & owner_filter))
            bot.add_handler(MessageHandler(logs_command, filters.command("logs") & owner_filter))
            bot.add_handler(MessageHandler(status_command, filters.command("status") & owner_filter))
            bot.add_handler(MessageHandler(start_command, filters.command("start") & filters.private))
            
            if file_client:
                try:
                    file_client.add_handler(MessageHandler(alive_command, filters.command("alive") & owner_filter))
                    file_client.add_handler(MessageHandler(logs_command, filters.command("logs") & owner_filter))
                    file_client.add_handler(MessageHandler(status_command, filters.command("status") & owner_filter))
                    file_client.add_handler(MessageHandler(start_command, filters.command("start") & filters.private))
                    LOG.info("✅ Command handlers registered on file client")
                except Exception as e:
                    LOG.warning(f"Failed to register handlers on file_client: {e}")
            LOG.info("✅ Command handlers registered on main bot")
        except Exception as e:
            LOG.critical(f"Failed to register handlers on bot: {e}")
            return

        LOG.info("✅ Telegram clients started successfully")
        
        set_working(False)
        
        try:
            os.makedirs('./downloads', exist_ok=True)
            LOG.info("✅ Downloads directory ready")
        except Exception as dir_error:
            LOG.warning(f"Failed to create downloads directory: {dir_error}")

        LOG.info("🔥 Warming up API (checking if service is available)...")
        warm_up_api(max_attempts=2)

        LOG.info(f"🚀 AABv2 started successfully! Check interval: {SETTINGS.check_interval_sec}s")
        
        await worker_loop()
        
    except Exception as e:
        LOG.critical(f"❌ Failed to start application: {e}")
    finally:
        try:
            if file_client:
                try:
                    await file_client.stop()
                except Exception:
                    LOG.warning("Error stopping file_client during cleanup")
            if bot:
                try:
                    await bot.stop()
                except Exception:
                    LOG.warning("Error stopping main bot during cleanup")
            LOG.info("✅ Clients stopped gracefully")
        except Exception as cleanup_error:
            LOG.error(f"Error during cleanup: {cleanup_error}")

def run():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        LOG.info("👋 Application stopped by user")
    except Exception as e:
        LOG.critical(f"💥 Application crashed: {e}")
