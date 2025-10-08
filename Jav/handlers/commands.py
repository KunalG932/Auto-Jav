import os
import re
import logging
import asyncio
from pyrogram.client import Client
from pyrogram.types import Message
from pyrogram import enums
from .utils import send_logs_to_user
from ..db import is_working, get_last_hash, get_file_by_hash, get_total_users, get_all_user_ids, failed_downloads, remove_failed_download
from ..config import SETTINGS
from ..services.start import start_cmd

LOG = logging.getLogger("Jav")

bot_instance = None
file_client_instance = None

def set_clients(bot, file_client):
    global bot_instance, file_client_instance
    bot_instance = bot
    file_client_instance = file_client

async def alive_command(client: Client, message: Message):
    await message.reply_text("🤖 Jav is alive and running!")

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
    
    status_text = f"⚙️ **Bot Status**\n\n🔄 Working: {'Yes' if working else 'No'}\n🔗 Last Hash: `{last_hash or 'None'}`"
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

            # Use copy_message instead of forward_messages so the forwarded tag is not shown
            copied_msg = await forwarder.copy_message(
                chat_id=chat_id,
                from_chat_id=SETTINGS.files_channel,
                message_id=message_id,
                #protect_content=True,
            )
            LOG.info(f"File copied to user {getattr(message.from_user, 'id', 'unknown')} for hash {file_hash} (no forwarded tag)")
            
            # Send warning message about deletion
            warning_text = (
                ">⚠️ **IMPORTANT WARNING** ⚠️\n\n"
                "🗑️ This file will be **DELETED in 3 MINUTES**!\n\n"
                "📤 **Please FORWARD this file to your Saved Messages NOW**\n\n"
                "⏰ Don't wait - save it immediately!"
            )
            warning_msg = await message.reply_text(warning_text)
            
            # Schedule file and warning deletion after 3 minutes
            async def delete_after_delay():
                await asyncio.sleep(180)  # 3 minutes = 180 seconds
                try:
                    # Delete the copied file message
                    await forwarder.delete_messages(chat_id=chat_id, message_ids=copied_msg.id)
                    LOG.info(f"Deleted file message {copied_msg.id} for user {chat_id}")
                except Exception as del_e:
                    LOG.warning(f"Failed to delete file message: {del_e}")
                
                try:
                    # Delete the warning message
                    await warning_msg.delete()
                    LOG.info(f"Deleted warning message for user {chat_id}")
                except Exception as warn_del_e:
                    LOG.warning(f"Failed to delete warning message: {warn_del_e}")
                
                # Send deletion confirmation with restart button
                from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                
                restart_button = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Get File Again", url=f"https://t.me/{getattr(await forwarder.get_me(), 'username', 'bot')}?start={file_hash}")]
                ])
                
                deletion_text = (
                    ">🗑️ **File Deleted**\n\n"
                    "The file has been removed after 3 minutes.\n\n"
                    "__If you need it again, click the button below:__"
                )
                
                try:
                    await client.send_message(chat_id=chat_id, text=deletion_text, reply_markup=restart_button)
                    LOG.info(f"Sent deletion notification to user {chat_id}")
                except Exception as notif_e:
                    LOG.warning(f"Failed to send deletion notification: {notif_e}")
            
            # Run deletion task in background
            asyncio.create_task(delete_after_delay())
        except Exception as e:
            LOG.exception(f"Failed to forward message {message_id}: {e}")
            await message.reply_text("❌ Failed to send file. Contact admin.")
        
    except Exception as e:
        LOG.error(f"Error in start command: {e}")
        await message.reply_text("❌ An error occurred while processing your request")

async def stats_command(client: Client, message: Message):
    try:
        total_users = get_total_users()
        working = is_working()
        last_hash = get_last_hash()
        
        stats_text = (
            "📊 **Bot Statistics**\n\n"
            f"👥 Total Users: **{total_users}**\n"
            f"⚙️ Worker Status: **{'Working' if working else 'Idle'}**\n"
            f"🔖 Last Hash: `{last_hash or 'None'}`\n\n"
            f"✅ Bot is running smoothly!"
        )
        
        await message.reply_text(stats_text)
        LOG.info(f"Stats command executed by user {message.from_user.id}")
        
    except Exception as e:
        LOG.error(f"Error in stats command: {e}")
        await message.reply_text("❌ Error fetching statistics")

async def broadcast_command(client: Client, message: Message):
    try:
        if not message.reply_to_message:
            await message.reply_text(
                "❌ Please reply to a message with /broadcast to forward it to all users.\n\n"
                "**Usage:** Reply to any message and type `/broadcast`"
            )
            return
        
        user_ids = get_all_user_ids()
        
        if not user_ids:
            await message.reply_text("❌ No users found in database.")
            return
        
        status_msg = await message.reply_text(
            f"📢 Starting broadcast to **{len(user_ids)}** users...\n\n"
            f"⏳ Please wait..."
        )
        
        success_count = 0
        failed_count = 0
        blocked_count = 0
        
        broadcast_msg = message.reply_to_message
        
        for i, user_id in enumerate(user_ids):
            try:
                await broadcast_msg.copy(user_id)
                success_count += 1
                
                if (i + 1) % 50 == 0:
                    await status_msg.edit_text(
                        f"📢 Broadcasting...\n\n"
                        f"✅ Sent: {success_count}\n"
                        f"❌ Failed: {failed_count}\n"
                        f"🚫 Blocked: {blocked_count}\n"
                        f"📊 Progress: {i + 1}/{len(user_ids)}"
                    )
                
                await asyncio.sleep(0.05)
                
            except Exception as e:
                error_msg = str(e).lower()
                if 'blocked' in error_msg or 'user is deactivated' in error_msg:
                    blocked_count += 1
                else:
                    failed_count += 1
                    LOG.warning(f"Failed to broadcast to user {user_id}: {e}")
        
        final_text = (
            "📢 **Broadcast Completed!**\n\n"
            f"✅ Successfully sent: **{success_count}**\n"
            f"❌ Failed: **{failed_count}**\n"
            f"🚫 Blocked bot: **{blocked_count}**\n"
            f"📊 Total users: **{len(user_ids)}**\n\n"
            f"🎉 Broadcast finished!"
        )
        
        await status_msg.edit_text(final_text)
        LOG.info(f"Broadcast completed: {success_count} success, {failed_count} failed, {blocked_count} blocked")
        
    except Exception as e:
        LOG.error(f"Error in broadcast command: {e}")
        await message.reply_text(f"❌ Error during broadcast: {str(e)}")

async def failed_command(client: Client, message: Message):
    try:
        text = (message.text or '').strip().split(maxsplit=2)
        command = text[0] if len(text) > 0 else '/failed'
        action = text[1].lower() if len(text) > 1 else None
        param = text[2] if len(text) > 2 else None
        
        if action == 'clear':
            try:
                result = failed_downloads.delete_many({})
                await message.reply_text(
                    f"🗑️ **Cleared Failed Downloads**\n\n"
                    f"Deleted {result.deleted_count} failed download records.\n"
                    f"These videos can now be downloaded again."
                )
                LOG.info(f"Cleared {result.deleted_count} failed downloads")
                return
            except Exception as e:
                await message.reply_text(f"❌ Error clearing failed downloads: {str(e)}")
                return
        
        if action == 'remove' and param:
            try:
                remove_failed_download(param)
                await message.reply_text(
                    f"✅ **Removed from Failed List**\n\n"
                    f"Title: `{param}`\n\n"
                    f"This video can now be downloaded again."
                )
                return
            except Exception as e:
                await message.reply_text(f"❌ Error removing failed download: {str(e)}")
                return
        
        try:
            failed_list = list(failed_downloads.find({}).sort('failed_at', -1).limit(50))
            
            if not failed_list:
                await message.reply_text(
                    "✅ **No Failed Downloads**\n\n"
                    "There are no failed downloads in the database."
                )
                return
            
            response = f"❌ **Failed Downloads ({len(failed_list)})**\n\n"
            
            for idx, item in enumerate(failed_list[:20], 1):
                title = item.get('title', 'Unknown')
                reason = item.get('reason', 'Unknown reason')
                failed_date = item.get('failed_date', 'Unknown date')
                
                if len(title) > 50:
                    title = title[:47] + "..."
                
                response += f"{idx}. **{title}**\n"
                response += f"   ├ Date: `{failed_date}`\n"
                response += f"   └ Reason: `{reason[:50]}`\n\n"
            
            if len(failed_list) > 20:
                response += f"\n...and {len(failed_list) - 20} more\n\n"
            
            response += (
                "**Commands:**\n"
                "• `/failed` - Show this list\n"
                "• `/failed clear` - Clear all failed downloads\n"
                "• `/failed remove <title>` - Remove specific title\n"
            )
            
            await message.reply_text(response)
            
        except Exception as e:
            await message.reply_text(f"❌ Error fetching failed downloads: {str(e)}")
            LOG.error(f"Error in failed command: {e}")
            
    except Exception as e:
        LOG.error(f"Error in failed command: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")
