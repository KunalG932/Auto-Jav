import logging
from pyrogram.client import Client
from .config import SETTINGS

LOG = logging.getLogger("Jav")

def create_clients():
    if not SETTINGS.api_id or not SETTINGS.api_hash:
        raise RuntimeError("API_ID and API_HASH must be set in environment/.env")
    if not SETTINGS.main_bot_token:
        raise RuntimeError("MAIN_BOT_TOKEN must be set in environment/.env")

    bot = Client(
        "Jav_MainBot",
        api_id=SETTINGS.api_id,
        api_hash=SETTINGS.api_hash,
        bot_token=SETTINGS.main_bot_token,
    )

    file_client = None
    if SETTINGS.client_bot_token:
        file_client = Client(
            "Jav_FileBot",
            api_id=SETTINGS.api_id,
            api_hash=SETTINGS.api_hash,
            bot_token=SETTINGS.client_bot_token,
        )

    return bot, file_client
