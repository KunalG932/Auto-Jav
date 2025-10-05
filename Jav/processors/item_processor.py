import os
import asyncio
import logging
from typing import Dict, Any, Optional
from pyrogram.client import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from ..config import SETTINGS
from ..db import get_file_by_hash, add_file_record, is_failed_download
from ..api.feed import get_title, sha1
from ..services.uploader import prepare_caption_content, add_download_button
from ..api.ai_caption import fetch_and_format, format_for_post
from ..utils import generate_hash
from .video_processor import process_video_download

LOG = logging.getLogger("Jav")
DOWNLOAD_LOCK = asyncio.Semaphore(1)

async def process_item(bot_client: Optional[Client], file_client: Optional[Client], item: Dict[str, Any]) -> None:
    if bot_client is None:
        LOG.error("process_item called without a running bot client; skipping")
        return

    title = get_title(item) or 'Unknown Title'
    
    # Check if this download has failed before
    if is_failed_download(title):
        LOG.info(f"⏭️ Skipping previously failed download: {title}")
        try:
            await bot_client.send_message(
                SETTINGS.production_chat, 
                f"⚠️ Skipped (previously failed): {title}"
            )
        except Exception:
            pass
        return
    
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
                LOG.info(f"🎬 Starting download process for: {title}")
                uploaded, msg = await process_video_download(
                    bot_client, file_client, item, title, title, magnet
                )
                LOG.info(f"📤 Download process completed: uploaded={uploaded}, title={title}")
                
                # Note: Don't mark as failed here if only upload failed
                # Upload failures could be temporary (network issues, etc.)
                # Only mark download as failed if the actual download fails
                if not uploaded:
                    LOG.warning(f"⚠️ Upload failed for {title}, but download was successful")
                    # Upload failures are logged but not permanently marked as failed
                    # This allows retry on next run if needed
                    
            except Exception as download_error:
                LOG.error(f"Download failed for {title}: {download_error}", exc_info=True)
                # Only mark as permanently failed if download itself failed (no peers, timeout, etc.)
                error_msg = str(download_error).lower()
                if any(keyword in error_msg for keyword in ['no peers', 'timeout', 'metadata', 'stalled']):
                    from ..db import add_failed_download
                    add_failed_download(title, magnet, f"Download error: {str(download_error)[:100]}")
                    LOG.info(f"❌ Marked as permanently failed: {title}")
                else:
                    LOG.warning(f"⚠️ Download error (may retry): {title}")
    else:
        LOG.info(f"No magnet link for {title}, posting with API thumbnail")
        try:
            uploaded = await post_without_file(bot_client, item, title, torrent_links)
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
        LOG.info("Generating AI caption for post without file...")
        payload = prepare_caption_content(item) if item else ''
        loop = asyncio.get_event_loop()
        try:
            ai_caption = await asyncio.wait_for(
                loop.run_in_executor(None, fetch_and_format, payload, 15),
                timeout=20,
            )
            if ai_caption:
                LOG.info(f"AI caption generated: {ai_caption[:100]}...")
        except asyncio.TimeoutError:
            LOG.warning("AI caption generation timed out")
            ai_caption = None
        except Exception as e:
            LOG.warning(f"AI caption generation failed: {e}")
            ai_caption = None
    except Exception as e:
        LOG.error(f"Error in AI caption generation: {e}")
        ai_caption = None

    if ai_caption and isinstance(ai_caption, str) and len(ai_caption.strip()) > 20:
        try:
            formatted = format_for_post(ai_caption)
            post_caption = formatted if formatted else ai_caption
            LOG.info("Using AI-generated caption")
        except Exception as e:
            LOG.warning(f"Failed to format AI caption: {e}")
            post_caption = ai_caption
    else:
        LOG.info("Using default caption (AI caption not available)")
        post_caption = caption

    api_thumbnail_url = item.get('thumbnail')
    thumbnail_file = None
    
    if api_thumbnail_url:
        try:
            import requests
            LOG.info(f"Downloading thumbnail from: {api_thumbnail_url}")
            response = requests.get(api_thumbnail_url, timeout=15)
            response.raise_for_status()
            
            thumb_dir = "./thumbnails"
            os.makedirs(thumb_dir, exist_ok=True)
            
            ext = '.jpg'
            if '.' in api_thumbnail_url:
                url_ext = api_thumbnail_url.split('.')[-1].split('?')[0].lower()
                if url_ext in ['jpg', 'jpeg', 'png', 'webp']:
                    ext = f'.{url_ext}'
            
            code = item.get('code', 'thumb_no_file')
            thumbnail_file = os.path.join(thumb_dir, f"{code}{ext}")
            
            with open(thumbnail_file, 'wb') as f:
                f.write(response.content)
            
            LOG.info(f"Thumbnail downloaded successfully: {thumbnail_file}")
        except Exception as e:
            LOG.warning(f"Failed to download thumbnail: {e}")
            thumbnail_file = None
    
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

    if thumbnail_file and os.path.exists(thumbnail_file):
        try:
            LOG.info(f"Sending photo with thumbnail: {thumbnail_file}")
            if kb:
                main_msg = await bot_client.send_photo(
                    SETTINGS.main_channel, thumbnail_file, caption=post_caption, reply_markup=kb
                )
            else:
                main_msg = await bot_client.send_photo(
                    SETTINGS.main_channel, thumbnail_file, caption=post_caption
                )
            LOG.info("Photo sent successfully with thumbnail")
        except Exception as e:
            LOG.warning(f"Failed to send photo with downloaded thumbnail: {e}, falling back to text")
            if kb:
                main_msg = await bot_client.send_message(SETTINGS.main_channel, post_caption, reply_markup=kb)
            else:
                main_msg = await bot_client.send_message(SETTINGS.main_channel, post_caption)
    else:
        LOG.info("No thumbnail available, sending text message")
        if kb:
            main_msg = await bot_client.send_message(SETTINGS.main_channel, post_caption, reply_markup=kb)
        else:
            main_msg = await bot_client.send_message(SETTINGS.main_channel, post_caption)
    
    try:
        if main_msg is not None:
            sticker_id = "CAACAgUAAx0CfPp_PwABAbRpaN9Edq9LmkFQPK_ea8U4u8I7_2MAAq8YAAKcZulW-3JDFK03uP8eBA"
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
