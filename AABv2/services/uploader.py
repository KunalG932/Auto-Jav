import os
import logging
import asyncio
from typing import Dict, Any, Optional
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from ..config import SETTINGS
from .ai_caption import fetch_and_format, format_for_post

LOG = logging.getLogger("AABv2")

def build_caption(item: Dict[str, Any]) -> str:
    title = item.get('title') or 'Unknown Title'
    parts = [f"🔸 {title}"]
    
    if code := item.get('code'):
        parts.append(f"🔸 Code: {code}")
    
    if actresses := item.get('actresses'):
        if isinstance(actresses, list) and actresses:
            parts.append(f"🔸 Actresses: {', '.join(actresses)}")
    
    if tags := item.get('tags'):
        if isinstance(tags, list) and tags:
            parts.append(f"🔸 Tags: {', '.join(tags)}")
    
    if release_date := item.get('release_date'):
        parts.append(f"🔸 Release Date: {release_date}")
    
    if description := item.get('description'):
        parts.append(f"\n� {description}")
    
    return "\n".join(parts)

def prepare_caption_content(item: Dict[str, Any]) -> str:
    title = item.get('title') or ''
    chunks = [title]
    
    if code := item.get('code'):
        chunks.append(f"Code: {code}")
    
    if actresses := item.get('actresses'):
        if isinstance(actresses, list) and actresses:
            chunks.append(f"Actresses: {', '.join(actresses)}")
    
    if tags := item.get('tags'):
        if isinstance(tags, list) and tags:
            chunks.append("Tags: " + ", ".join(tags))
    
    if description := item.get('description'):
        chunks.append(f"Description: {description}")
    
    return " | ".join([c for c in chunks if c])


async def upload_file(file_client, file_path: str, title: Optional[str] = None,
                      item: Optional[Dict[str, Any]] = None,
                      send_ai_caption: bool = False) -> Optional[Message]:
    try:
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            LOG.error(f"upload_file error: Path does not exist -> {abs_path}")
            return None
    except Exception as e:
        LOG.error(f"Error while resolving file path: {e}")
        return None

    # No AI caption, use original description from API
    if title:
        doc_caption = title
    else:
        doc_caption = build_caption(item) if item else os.path.basename(abs_path)

    if not title and not doc_caption:
        doc_caption = os.path.basename(abs_path)

    # Download thumbnail from API if available
    thumb_path = None
    if item and item.get('thumbnail'):
        try:
            import requests
            thumbnail_url = item.get('thumbnail')
            if thumbnail_url and isinstance(thumbnail_url, str):
                LOG.info(f"Downloading thumbnail from API: {thumbnail_url}")
                
                response = requests.get(thumbnail_url, timeout=15)
                response.raise_for_status()
                
                thumb_dir = "./thumbnails"
                os.makedirs(thumb_dir, exist_ok=True)
                
                ext = '.jpg'
                if '.' in thumbnail_url:
                    url_ext = thumbnail_url.split('.')[-1].split('?')[0].lower()
                    if url_ext in ['jpg', 'jpeg', 'png', 'webp']:
                        ext = f'.{url_ext}'
                
                code = item.get('code', 'thumb')
                thumb_path = os.path.join(thumb_dir, f"{code}_upload{ext}")
                
                with open(thumb_path, 'wb') as f:
                    f.write(response.content)
                
                LOG.info(f"Thumbnail downloaded: {thumb_path}")
        except Exception as e:
            LOG.warning(f"Failed to download thumbnail from API: {e}")
            thumb_path = None
    
    # Fallback to static thumbnail if API download failed
    if not thumb_path:
        try:
            tp = getattr(SETTINGS, 'thumbnail_path', None)
            if tp:
                tp_abs = os.path.abspath(tp)
                LOG.info(f"Using fallback thumbnail at: {tp_abs}")
                if os.path.exists(tp_abs):
                    thumb_path = tp_abs
                else:
                    LOG.warning(f"Fallback thumbnail not found: {tp_abs}")
        except Exception:
            thumb_path = None

    upload_path = abs_path
    LOG.info("Encoding/size-reduction disabled; proceeding to upload original file")

    attempts = 3
    delay = 3
    msg = None
    target_chat = getattr(SETTINGS, 'files_channel', 0) or getattr(SETTINGS, 'main_channel', None)
    if not target_chat:
        LOG.error("upload_file error: No target chat configured (FILES_CHANNEL or MAIN_CHANNEL)")
        return None

    try:
        try:
            size_mb = os.path.getsize(upload_path) / (1024.0 * 1024.0)
        except Exception:
            size_mb = 0.0
        LOG.info(f"Uploading document: path={upload_path} size={size_mb:.1f} MiB target_chat={target_chat} file_client_present={file_client is not None}")
        client_to_use = file_client
        for attempt in range(1, attempts + 1):
            try:
                if attempt > 1:
                    await asyncio.sleep(delay)
                    delay *= 2
                with open(upload_path, 'rb') as fh:
                    try:
                        if client_to_use is None:
                            raise RuntimeError("No client available to send the document")
                        try:
                            me = await client_to_use.get_me()
                            LOG.info(f"Uploading using client: id={getattr(me, 'id', None)} username={getattr(me, 'username', None)}")
                        except Exception:
                            LOG.debug("Could not fetch client identity before upload")
                        LOG.debug(f"Using client object {client_to_use} to send to chat {target_chat}")
                        msg = await client_to_use.send_document(
                            chat_id=target_chat,
                            document=fh,
                            file_name=os.path.basename(upload_path),
                            caption=doc_caption,
                            force_document=True,
                            thumb=thumb_path,
                        )
                    except Exception as send_exc:
                        LOG.exception(f"send_document attempt {attempt} failed (client={client_to_use}, target_chat={target_chat}): {send_exc}")
                        raise
                break
            except Exception as e:
                LOG.warning(f"upload_file attempt {attempt} failed: {e}")
                msg = None
                if attempt == attempts:
                    raise
                continue
    finally:
        if upload_path != abs_path and os.path.exists(upload_path):
            try:
                os.remove(upload_path)
            except Exception:
                pass

    return msg


async def add_download_button(bot, message: Message, bot_username: str, file_hash: str) -> None:
    try:
        markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="Download Now", url=f"https://t.me/{bot_username}?start={file_hash}")]]
        )
        await message.edit_reply_markup(markup)
    except Exception as e:
        LOG.exception(f"add_download_button error: {e}")
