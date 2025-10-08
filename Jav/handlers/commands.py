import os
import re
import logging
import asyncio
from pyrogram.client import Client
from pyrogram.types import Message
from pyrogram import filters
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

            copied_msg = await forwarder.copy_message(
                chat_id=chat_id,
                from_chat_id=SETTINGS.files_channel,
                message_id=message_id,
            )
            LOG.info(f"File copied to user {getattr(message.from_user, 'id', 'unknown')} for hash {file_hash} (no forwarded tag)")
            
            warning_text = (
                ">⚠️ **IMPORTANT WARNING** ⚠️\n\n"
                "🗑️ This file will be **DELETED in 3 MINUTES**!\n\n"
                "📤 **Please FORWARD this file to your Saved Messages NOW**\n\n"
                "⏰ Don't wait - save it immediately!"
            )
            warning_msg = await message.reply_text(warning_text)
            
            async def delete_after_delay():
                await asyncio.sleep(180)
                try:
                    await forwarder.delete_messages(chat_id=chat_id, message_ids=copied_msg.id)
                    LOG.info(f"Deleted file message {copied_msg.id} for user {chat_id}")
                except Exception as del_e:
                    LOG.warning(f"Failed to delete file message: {del_e}")
                
                try:
                    await warning_msg.delete()
                    LOG.info(f"Deleted warning message for user {chat_id}")
                except Exception as warn_del_e:
                    LOG.warning(f"Failed to delete warning message: {warn_del_e}")
                
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

async def queue_command(client: Client, message: Message):
    try:
        from ..db import get_queue_size, get_posts_today, pending_queue, get_queue_stats
        from ..config import SETTINGS
        
        queue_size = get_queue_size()
        posts_today = get_posts_today()
        max_posts = SETTINGS.max_posts_per_day
        remaining = max(0, max_posts - posts_today)
        queue_stats = get_queue_stats()
        
        next_items = list(pending_queue.find(
            {'status': 'pending'},
            sort=[('added_at', 1)]
        ).limit(5))
        
        queue_text = (
            f"📊 **Queue & Daily Limit Status**\n\n"
            f"📅 **Today's Posts:** {posts_today}/{max_posts}\n"
            f"⏳ **Remaining Today:** {remaining}\n"
            f"📦 **Queue Size:** {queue_size} pending\n"
            f"✅ **Processed Total:** {queue_stats['processed']}\n\n"
        )
        
        if next_items:
            queue_text += "**📋 Next in Queue:**\n"
            for idx, item in enumerate(next_items, 1):
                item_data = item.get('item_data', {})
                title = item_data.get('title', 'Unknown')[:35]
                queue_text += f"{idx}. {title}...\n"
            
            if queue_size > 5:
                queue_text += f"\n...and {queue_size - 5} more items\n"
        else:
            queue_text += "✅ **Queue is empty**\n"
        
        queue_text += f"\n🔄 Check Interval: Every {SETTINGS.check_interval_sec}s"
        
        await message.reply_text(queue_text)
        LOG.info(f"Queue command executed by user {getattr(message.from_user, 'id', 'unknown')}")
        
    except Exception as e:
        LOG.error(f"Error in queue command: {e}")
        await message.reply_text(f"❌ Error fetching queue status: {str(e)}")

async def resources_command(client: Client, message: Message):
@Client.on_message(filters.command(["clearfolders", "cleanfolders", "deletefolders"]))
async def clear_folders_command(client: Client, message: Message):
    """
    Deletes all files inside 'downloads', 'AAB/utils/thumb', and 'encode' folders.
    Usage: /clearfolders or /cleanfolders or /deletefolders
    """
    try:
        import shutil
        import glob
        deleted = []
        errors = []
        # List of folders to clear
        folders = [
            "downloads",
            "encode"
        ]
        for folder in folders:
            abs_path = os.path.abspath(folder)
            if os.path.exists(abs_path):
                # Remove all files and subfolders inside, but not the folder itself
                for item in os.listdir(abs_path):
                    item_path = os.path.join(abs_path, item)
                    try:
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        deleted.append(item_path)
                    except Exception as e:
                        errors.append(f"{item_path}: {str(e)}")
            else:
                errors.append(f"{abs_path} does not exist.")
        reply = f"✅ Deleted {len(deleted)} items from folders."
        if errors:
            reply += f"\n❌ Errors:\n" + "\n".join(errors)
        await message.reply_text(reply)
    except Exception as e:
        await message.reply_text(f"❌ Error clearing folders: {str(e)}")
    try:
        import psutil
        import shutil
        from datetime import datetime
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024**3)
        memory_total_gb = memory.total / (1024**3)
        memory_percent = memory.percent
        
        disk = shutil.disk_usage('.')
        disk_used_gb = disk.used / (1024**3)
        disk_total_gb = disk.total / (1024**3)
        disk_percent = (disk.used / disk.total) * 100
        disk_free_gb = disk.free / (1024**3)
        
        downloads_size = 0
        downloads_path = './downloads'
        if os.path.exists(downloads_path):
            for dirpath, dirnames, filenames in os.walk(downloads_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        downloads_size += os.path.getsize(filepath)
                    except:
                        pass
        downloads_size_gb = downloads_size / (1024**3)
        
        encode_size = 0
        encode_path = './encode'
        if os.path.exists(encode_path):
            for dirpath, dirnames, filenames in os.walk(encode_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        encode_size += os.path.getsize(filepath)
                    except:
                        pass
        encode_size_gb = encode_size / (1024**3)
        
        from ..db import files, users, pending_queue, failed_downloads
        total_files = files.count_documents({})
        total_users = users.count_documents({})
        queue_size = pending_queue.count_documents({'status': 'pending'})
        failed_count = failed_downloads.count_documents({})
        
        resource_text = (
            f"💻 **System Resources**\n\n"
            f"**🖥️ CPU Usage:** {cpu_percent}%\n"
            f"**🧠 RAM:** {memory_used_gb:.2f}GB / {memory_total_gb:.2f}GB ({memory_percent}%)\n"
            f"**💾 Disk:** {disk_used_gb:.1f}GB / {disk_total_gb:.1f}GB ({disk_percent:.1f}%)\n"
            f"**📁 Free Space:** {disk_free_gb:.1f}GB\n\n"
            f"**📂 Storage Breakdown:**\n"
            f"├ Downloads: {downloads_size_gb:.2f}GB\n"
            f"└ Encode: {encode_size_gb:.2f}GB\n\n"
            f"**📊 Database Stats:**\n"
            f"├ Total Files: {total_files}\n"
            f"├ Total Users: {total_users}\n"
            f"├ Queue Items: {queue_size}\n"
            f"└ Failed Downloads: {failed_count}\n\n"
            f"⏰ Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        await message.reply_text(resource_text)
        LOG.info(f"Resources command executed by user {getattr(message.from_user, 'id', 'unknown')}")
        
    except ImportError:
        await message.reply_text(
            "❌ psutil module not installed.\n\n"
            "Install it with: `pip install psutil`"
        )
    except Exception as e:
        LOG.error(f"Error in resources command: {e}")
        await message.reply_text(f"❌ Error fetching resources: {str(e)}")

@Client.on_message(filters.command(["restart", "reboot"]))
async def restart_command(client: Client, message: Message):
    """
    Restart the bot by stopping all processes and restarting.
    Usage: /restart or /reboot
    """
    try:
        import sys
        import subprocess
        
        await message.reply_text("🔄 Restarting bot... Please wait.")
        LOG.info(f"Restart command executed by user {getattr(message.from_user, 'id', 'unknown')}")
        
        # Stop the bot gracefully
        await client.stop()
        
        # Restart the bot using python3 -m Jav
        python = sys.executable
        os.execl(python, python, "-m", "Jav")
        
    except Exception as e:
        LOG.error(f"Error in restart command: {e}")
        await message.reply_text(f"❌ Error restarting bot: {str(e)}")

