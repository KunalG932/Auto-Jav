import asyncio
import os
import logging
from typing import Optional
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from .config import SETTINGS
from .clients import create_clients
from .db import client as mongo_client, is_working, set_working
from .handlers import (
    alive_command, logs_command, status_command, start_command,
    stats_command, broadcast_command, failed_command
)
from .handlers.commands import set_clients
from .processors import process_item, check_for_new_items
from .api.api_health import warm_up_api

# ---------------------------- Logging Setup ----------------------------
LOG = logging.getLogger("Jav")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("logging_v2.txt")]
)

bot: Optional[Client] = None
file_client: Optional[Client] = None


# ---------------------------- Worker Loop ----------------------------
async def worker_loop():
    """Continuously checks for new items and processes them."""
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
                    LOG.exception(f"Error processing items: {process_error}")
                finally:
                    set_working(False)
            else:
                LOG.debug("Worker busy, skipping cycle")
        except Exception as loop_error:
            LOG.exception(f"Worker loop error: {loop_error}")

        await asyncio.sleep(SETTINGS.check_interval_sec)


# ---------------------------- Bot Initialization ----------------------------
async def init_clients():
    """Create and start both main and file clients."""
    try:
        bot, file_client = create_clients()
        set_clients(bot, file_client)
    except Exception as e:
        LOG.critical(f"Failed to create Telegram clients: {e}")
        raise

    LOG.info("Starting Telegram clients...")

    if file_client:
        await file_client.start()
        LOG.info("✅ File client started")

    await bot.start()
    LOG.info("✅ Main bot started")

    return bot, file_client


# ---------------------------- Handler Registration ----------------------------
def register_handlers(bot: Client, file_client: Client):
    """Attach command handlers to both clients."""
    owner_filter = filters.user(list(SETTINGS.owner_ids))

    handlers = [
        (alive_command, "alive"),
        (logs_command, "logs"),
        (status_command, "status"),
        (stats_command, "stats"),
        (broadcast_command, "broadcast"),
        (failed_command, "failed"),
        (start_command, "start", filters.private),
    ]

    for func, cmd, *extra in handlers:
        cmd_filter = filters.command(cmd)
        if extra:
            cmd_filter &= extra[0]
        bot.add_handler(MessageHandler(func, cmd_filter & owner_filter if cmd != "start" else cmd_filter))
        file_client.add_handler(MessageHandler(func, cmd_filter & owner_filter if cmd != "start" else cmd_filter))

    LOG.info("✅ Command handlers registered")


# ---------------------------- Main Entry ----------------------------
async def main():
    global bot, file_client

    # MongoDB connection check
    try:
        mongo_client.admin.command("ping")
        LOG.info("✅ MongoDB connected successfully")
    except Exception as e:
        LOG.critical(f"❌ MongoDB connection failed: {e}")
        return

    # Initialize clients
    bot, file_client = await init_clients()

    # Register handlers
    register_handlers(bot, file_client)

    # Prepare folders
    os.makedirs("./downloads", exist_ok=True)
    LOG.info("✅ Downloads directory ready")

    # Warm-up API
    LOG.info("🔥 Warming up API...")
    warm_up_api(max_attempts=2)

    LOG.info(f"🚀 Jav bot started! Check interval: {SETTINGS.check_interval_sec}s")

    try:
        await worker_loop()
    finally:
        await shutdown_clients()


# ---------------------------- Cleanup ----------------------------
async def shutdown_clients():
    """Gracefully stop both clients."""
    global bot, file_client
    try:
        if file_client:
            await file_client.stop()
        if bot:
            await bot.stop()
        LOG.info("✅ Clients stopped gracefully")
    except Exception as cleanup_error:
        LOG.exception(f"Error during shutdown: {cleanup_error}")


# ---------------------------- Runner ----------------------------
def run():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        LOG.info("👋 Application stopped by user")
    except Exception as e:
        LOG.critical(f"💥 Application crashed: {e}")
