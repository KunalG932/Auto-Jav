import os
import re
import logging
from pyrogram.client import Client
from pyrogram.types import Message
from .utils import send_logs_to_user
from ..db import is_working, get_last_hash, get_file_by_hash
from ..config import SETTINGS
from ..services.start import start_cmd

LOG = logging.getLogger("AABv2")

bot_instance = None
file_client_instance = None

def set_clients(bot, file_client):
    global bot_instance, file_client_instance
    bot_instance = bot
    file_client_instance = file_client

async def alive_command(client: Client, message: Message):
    await message.reply_text("🤖 AABv2 is alive and running!")

async def logs_command(client: Client, message: Message):
    user_id = getattr(message.from_user, 'id', None)
    if user_id is None:
        await message.reply_text("❌ Could not determine your user id")
        return
    success = await send_logs_to_user(client, user_id)
    if success:
        await message.reply_text("📄 Logs sent to your PM")
    else:
        await message.reply_text("❌ Failed to send logs")

async def status_command(client: Client, message: Message):
    working = is_working()
    last_hash = get_last_hash()
    
    status_text = f
    await message.reply_text(status_text)

async def start_command(client: Client, message: Message):
    try:
        text = (message.text or '').strip()
        m = re.match(r'^/start(?:@[^\s]+)?(?:[ _=]?)(.*)$', text)
        payload = (m.group(1).strip() if m else '') if text else ''

        if not payload:
            await start_cmd(client, message)
            return

        file_hash = payload.split()[0]

        if not file_hash:
            await message.reply_text("❌ Invalid hash format")
            return
        LOG.info(f"/start payload parsed file_hash='{file_hash}' from text='{text}'")
        
        file_record = get_file_by_hash(file_hash)
        LOG.info(f"DB lookup for hash {file_hash} -> {file_record}")

        if not file_record:
            await message.reply_text("❌ File not found or invalid hash")
            return

        message_id = file_record.get('message_id')
        if not message_id:
            await message.reply_text("❌ Stored record missing message id for this file")
            LOG.error(f"File record for hash {file_hash} missing message_id: {file_record}")
            return

        forwarder = file_client_instance if file_client_instance else client
        chat_id = getattr(message.chat, 'id', None)
        try:
            if chat_id is None:
                await message.reply_text("❌ Could not determine destination chat id")
                return

            await forwarder.forward_messages(
                chat_id=chat_id,
                from_chat_id=SETTINGS.files_channel,
                message_ids=message_id,
                protect_content=True,
            )
            LOG.info(f"File forwarded to user {getattr(message.from_user, 'id', 'unknown')} for hash {file_hash}")
        except Exception as e:
            LOG.exception(f"Failed to forward message {message_id}: {e}")
            await message.reply_text("❌ Failed to send file. Contact admin.")
        
    except Exception as e:
        LOG.error(f"Error in start command: {e}")
        await message.reply_text("❌ An error occurred while processing your request")
