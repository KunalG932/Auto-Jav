import os
import asyncio
import logging
from typing import Dict, Any, Optional
from pyrogram.client import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from ..config import SETTINGS
from ..db import get_file_by_hash, add_file_record
from ..services.feed import get_title, sha1
from ..services.uploader import build_caption, prepare_caption_content, add_download_button
from ..services.ai_caption import fetch_and_format, format_for_post
from ..utils import generate_hash
from .video_processor import process_video_download

LOG = logging.getLogger("AABv2")
DOWNLOAD_LOCK = asyncio.Semaphore(1)

async def process_item(bot_client: Optional[Client], file_client: Optional[Client], item: Dict[str, Any]) -> None:
    if bot_client is None:
        LOG.error("process_item called without a running bot client; skipping")
        return

    title = get_title(item) or 'Unknown Title'
    caption = build_caption(item)
    
    try:
        item_hash = sha1(title)
        if get_file_by_hash(item_hash):
            LOG.info(f"Item already uploaded (by hash), skipping: {title} -> {item_hash}")
            return
        
        try:
            from ..db import files as files_collection
            if title and files_collection.count_documents({"name": title}, limit=1) > 0:
                LOG.info(f"Item already uploaded (by name), skipping: {title}")
                return
        except Exception:
            pass
    except Exception:
        pass

    try:
        if getattr(SETTINGS, 'files_channel', None) and file_client:
            try:
                query = title if title else None
                if query:
                    found_msgs = [m async for m in file_client.search_messages(chat_id=SETTINGS.files_channel, query=query, limit=50)]
                    if found_msgs:
                        LOG.info(f"Found existing upload in files channel for '{title}', skipping")
                        return
            except Exception as e:
                LOG.debug(f"Files channel search failed/skipped: {e}")
    except Exception:
        pass

    torrent_links = item.get('torrent_links', [])
    magnet = None
    
    if isinstance(torrent_links, list) and torrent_links:
        for link in torrent_links:
            if isinstance(link, dict):
                mag = link.get('magnet')
                if mag and isinstance(mag, str) and mag.startswith('magnet:'):
                    magnet = mag
                    break
    
    uploaded = False
    msg = None
    
    if magnet and isinstance(magnet, str):
        async with DOWNLOAD_LOCK:
            try:
                uploaded, msg = await process_video_download(
                    bot_client, file_client, item, title, caption, magnet
                )
            except Exception as download_error:
                LOG.error(f"Download/upload failed for {title}: {download_error}")
    else:
        LOG.info(f"No magnet link for {title}, posting with API thumbnail")
        try:
            uploaded = await post_without_file(bot_client, item, caption, torrent_links)
        except Exception as e:
            LOG.error(f"Failed to post to main channel without file: {e}")
    
    try:
        if uploaded:
            link = getattr(msg, 'link', None) or f"Successfully processed: {title}"
            await bot_client.send_message(SETTINGS.production_chat, f"✅ {link}")
        else:
            await bot_client.send_message(SETTINGS.production_chat, "❌ No file uploaded")
    except Exception as update_error:
        LOG.error(f"Failed to update production chat: {update_error}")

async def post_without_file(bot_client: Client, item: Dict[str, Any], caption: str, torrent_links: list) -> bool:
    forward_client = bot_client
    bot_user = await forward_client.get_me()
    
    ai_caption = None
    try:
        payload = prepare_caption_content(item) if item else ''
        loop = asyncio.get_event_loop()
        try:
            ai_caption = await asyncio.wait_for(
                loop.run_in_executor(None, fetch_and_format, payload, 8),
                timeout=12,
            )
        except Exception:
            ai_caption = None
    except Exception:
        ai_caption = None

    if ai_caption and isinstance(ai_caption, str):
        try:
            formatted = format_for_post(ai_caption)
            post_caption = formatted if formatted else ai_caption
        except Exception:
            post_caption = ai_caption
    else:
        post_caption = caption

    api_thumbnail = item.get('thumbnail')
    
    buttons = []
    if torrent_links:
        for link in torrent_links:
            if isinstance(link, dict):
                mag = link.get('magnet')
                if mag and isinstance(mag, str):
                    buttons.append([InlineKeyboardButton("📥 Magnet Link", url=mag)])
                    break
    
    source_url = item.get('url')
    if source_url:
        buttons.append([InlineKeyboardButton("🔗 Source", url=source_url)])
    
    kb = InlineKeyboardMarkup(buttons) if buttons else None

    if api_thumbnail:
        try:
            if kb:
                main_msg = await bot_client.send_photo(
                    SETTINGS.main_channel, api_thumbnail, caption=post_caption, reply_markup=kb
                )
            else:
                main_msg = await bot_client.send_photo(
                    SETTINGS.main_channel, api_thumbnail, caption=post_caption
                )
        except Exception as e:
            LOG.warning(f"Failed to send photo with API thumbnail: {e}, falling back to text")
            if kb:
                main_msg = await bot_client.send_message(SETTINGS.main_channel, post_caption, reply_markup=kb)
            else:
                main_msg = await bot_client.send_message(SETTINGS.main_channel, post_caption)
    else:
        if kb:
            main_msg = await bot_client.send_message(SETTINGS.main_channel, post_caption, reply_markup=kb)
        else:
            main_msg = await bot_client.send_message(SETTINGS.main_channel, post_caption)
    
    try:
        if main_msg is not None:
            sticker_id = "CAACAgUAAx0CfPp_PwABAX9taNZsQyInPz500GChLCk3uconkqwAAhESAALeIohXvOSc_GX-md4eBA"
            mid = getattr(main_msg, 'id', None)
            
            async def _send_sticker_async(sid, reply_id):
                try:
                    await bot_client.send_sticker(SETTINGS.main_channel, sid, reply_to_message_id=reply_id)
                except Exception as e:
                    LOG.warning(f"Failed to send sticker: {e}")

            asyncio.create_task(_send_sticker_async(sticker_id, mid))
    except Exception:
        pass

    LOG.info(f"Posted {get_title(item)} to main channel (no file uploaded)")
    return True
