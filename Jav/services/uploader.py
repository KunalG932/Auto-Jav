import os
import logging
import asyncio
from typing import Dict, Any, Optional
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram import errors
from ..config import SETTINGS
from ..api.ai_caption import format_for_post

LOG = logging.getLogger("Jav")

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
                      item: Optional[Dict[str, Any]] = None) -> Optional[Message]:
    try:
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            LOG.error(f"upload_file error: Path does not exist -> {abs_path}")
            return None
    except Exception as e:
        LOG.error(f"Error while resolving file path: {e}")
        return None

    if title:
        doc_caption = title
    else:
        doc_caption = os.path.basename(abs_path)

    from ..utils import download_thumbnail_with_fallback
    
    thumbnail_url = item.get('thumbnail') if item else None
    filename_prefix = f"{item.get('code', 'thumb')}_upload" if item and item.get('code') else 'thumb_upload'
    thumb_path = download_thumbnail_with_fallback(
        thumbnail_url,
        SETTINGS,
        filename_prefix=filename_prefix
    )

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
                    except errors.FloodWait as fw:
                        wait_time = int(fw.value) if isinstance(fw.value, (int, float)) else 60
                        LOG.warning(f"FloodWait during upload: sleeping for {wait_time} seconds (attempt {attempt})")
                        await asyncio.sleep(float(wait_time))
                        if attempt < attempts:
                            continue
                        raise
                    except Exception as send_exc:
                        LOG.exception(f"send_document attempt {attempt} failed (client={client_to_use}, target_chat={target_chat}): {send_exc}")
                        raise
                break
            except errors.FloodWait as fw:
                wait_time = int(fw.value) if isinstance(fw.value, (int, float)) else 60
                LOG.warning(f"FloodWait on attempt {attempt}: waiting {wait_time}s before retry")
                await asyncio.sleep(float(wait_time))
                if attempt == attempts:
                    raise
                continue
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
    from ..utils import add_download_buttons
    
    await add_download_buttons(
        bot,
        message,
        bot_username,
        file_hash=file_hash
    )
