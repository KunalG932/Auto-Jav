import os
import logging
from pyrogram.client import Client

LOG = logging.getLogger("AABv2")

async def send_logs_to_user(client: Client, user_id: int) -> bool:
    try:
        if os.path.exists('logging_v2.txt'):
            await client.send_document(user_id, 'logging_v2.txt', caption="AABv2 logs")
            return True
        else:
            await client.send_message(user_id, "No log file found.")
            return False
    except Exception as e:
        LOG.error(f"Failed to send logs: {e}")
        return False
