import os
import time
import asyncio
import logging
import subprocess
from typing import Dict, Any, Optional, Tuple
from pyrogram.client import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from ..config import SETTINGS
from ..services.downloader import download_torrent
from ..services.uploader import upload_file, add_download_button, prepare_caption_content
from ..api.ai_caption import fetch_and_format, format_for_post, create_enhanced_caption
from ..utils import generate_hash
from ..db import add_file_record

LOG = logging.getLogger("Jav")

async def process_video_download(
    bot_client: Client,
    file_client: Optional[Client],
    item: Dict[str, Any],
    title: str,
    caption: str,
    magnet: str
) -> Tuple[bool, Optional[Message]]:
    uploaded = False
    msg = None
    
    os.makedirs('./downloads', exist_ok=True)
    
    update_msg = await bot_client.send_message(SETTINGS.production_chat, f"📥 Downloading: {title}")

    async def safe_edit(text: str):
        try:
            if not update_msg:
                return
            chat = getattr(update_msg, 'chat', None)
            mid = getattr(update_msg, 'id', None)
            if chat is None or mid is None:
                return
            await bot_client.edit_message_text(chat_id=chat.id, message_id=mid, text=text)
        except Exception:
            pass
    
    loop = asyncio.get_event_loop()
    last_edit_ts = 0.0

    def _progress_cb(stats: Dict[str, float]):
        nonlocal last_edit_ts
        try:
            now = time.time()
            if stats.get("stage") != "completed" and (now - last_edit_ts) < 3:
                return
            last_edit_ts = now
            stage = stats.get("stage", "downloading")
            pct = stats.get("progress_pct", 0.0)
            down = stats.get("down_rate_kbs", 0.0)
            peers = int(stats.get("peers", 0.0))
            elapsed = int(stats.get("elapsed", 0.0))
            text = f"📥 Downloading: {title}\nStage: {stage} | {pct:.1f}%\nSpeed: {down:.1f} kB/s | Peers: {peers} | Elapsed: {elapsed}s"
            try:
                asyncio.run_coroutine_threadsafe(safe_edit(text), loop)
            except Exception:
                pass
        except Exception:
            pass

    info = await loop.run_in_executor(None, download_torrent, magnet, _progress_cb)
    
    LOG.info(f"Download executor returned: info={info}")
    if info:
        LOG.info(f"Info type: {type(info)}, keys: {info.keys() if isinstance(info, dict) else 'N/A'}")
        file_path = info.get('file') if isinstance(info, dict) else None
        LOG.info(f"File path: {file_path}")
        if file_path:
            LOG.info(f"File exists: {os.path.exists(file_path)}")

    if info and info.get('file') and os.path.exists(info['file']):
        LOG.info(f"✅ Download successful, starting post-processing for: {info['file']}")
        try:
            await safe_edit(f"✅ Download complete: {title}\nStarting upload...")
        except Exception:
            pass

        try:
            upload_path = await remux_if_needed(info['file'], safe_edit, title)
            
            if SETTINGS.enable_encoding:
                try:
                    await safe_edit(f"🔄 Encoding to 720p: {os.path.basename(upload_path)}")
                    LOG.info(f"Starting FFEncoder encoding for: {upload_path}")
                    
                    from ..services.encode import FFEncoder
                    
                    file_name = os.path.basename(upload_path)
                    base_name, ext = os.path.splitext(file_name)
                    output_name = f"{base_name}_encoded.mkv"
                    
                    encoder = FFEncoder(upload_path, output_name)
                    
                    encoded_path = await encoder.start_encode()
                    
                    if encoded_path and os.path.exists(encoded_path):
                        LOG.info(f"✅ FFEncoder encoding successful: {encoded_path}")
                        
                        original_size = os.path.getsize(upload_path) / (1024 * 1024)
                        encoded_size = os.path.getsize(encoded_path) / (1024 * 1024)
                        reduction = ((original_size - encoded_size) / original_size * 100) if original_size > 0 else 0
                        
                        LOG.info(f"Size: {original_size:.1f}MB → {encoded_size:.1f}MB ({reduction:+.1f}%)")
                        
                        try:
                            if upload_path != info['file']:
                                os.remove(upload_path)
                                LOG.info(f"Cleaned up original file: {upload_path}")
                        except Exception as e:
                            LOG.warning(f"Failed to cleanup original file: {e}")
                        
                        upload_path = encoded_path
                        await safe_edit(f"✅ Encoded to 720p: {os.path.basename(upload_path)}\nSize reduced by {abs(reduction):.1f}%")
                    else:
                        LOG.warning("FFEncoder encoding failed, using original file")
                        await safe_edit("⚠️ Encoding failed, using original file")
                except Exception as e:
                    LOG.error(f"FFEncoder encoding error: {e}", exc_info=True)
                    await safe_edit("⚠️ Encoding failed, using original file")
            else:
                LOG.info("Encoding disabled; proceeding with original file")
                try:
                    await safe_edit("ℹ️ Encoding skipped: proceeding with original file")
                except Exception:
                    pass

            try:
                up_size = os.path.getsize(upload_path) / (1024.0 * 1024.0)
                LOG.info(f"Preparing to upload file: {upload_path} ({up_size:.1f} MiB)")
            except Exception:
                pass

            try:
                file_size_bytes = os.path.getsize(upload_path)
            except Exception:
                file_size_bytes = 0

            part_hashes = []
            file_hash = None
            TWO_GB = 2 * 1024 * 1024 * 1024

            LOG.info(f"File size: {file_size_bytes} bytes ({file_size_bytes/(1024**3):.2f} GB)")
            
            if file_size_bytes > TWO_GB:
                LOG.info("File >2GB, will split into parts")
                await safe_edit(f"🔀 File >2GiB detected; splitting into 2 parts for upload")
                uploaded, part_hashes = await upload_large_file(
                    bot_client, file_client, upload_path, title, item, file_size_bytes, safe_edit
                )
            else:
                LOG.info("File <=2GB, uploading as single file")
                uploaded, file_hash = await upload_single_file(
                    bot_client, file_client, upload_path, title, item, caption
                )

            LOG.info(f"Upload completed: uploaded={uploaded}, file_hash={file_hash}, part_hashes={part_hashes}")
            
            if uploaded:
                LOG.info("Starting post to main channel...")
                await post_to_main_channel(bot_client, file_client, item, caption, file_hash, part_hashes, upload_path)
                LOG.info(f"✅ Successfully uploaded and posted: {title}")
            else:
                LOG.error(f"❌ Upload failed for: {title}")
            
            await cleanup_files(info['file'], upload_path)
            
        except Exception as upload_error:
            LOG.error(f"❌ Error during upload process for {title}: {upload_error}", exc_info=True)
            uploaded = False
            
    else:
        LOG.error(f"❌ Download failed - no file info returned for: {title}")
    
    try:
        await update_msg.delete()
    except Exception:
        pass
    
    LOG.info(f"Returning from process_video_download: uploaded={uploaded}")
    return uploaded, msg

async def remux_if_needed(file_path: str, safe_edit, title: str) -> str:
    if os.path.splitext(file_path)[1].lower() != '.ts':
        return file_path
    
    try:
        await safe_edit(f"🔁 Remuxing .ts → .mp4 for: {title}")
    except Exception:
        pass
    
    def remux_ts_to_mp4(path: str) -> str:
        try:
            base, ext = os.path.splitext(path)
            if ext.lower() == '.mp4':
                return path
            if ext.lower() != '.ts':
                return path
            out_path = base + '.mp4'
            LOG.info(f"Remuxing {path} -> {out_path} using ffmpeg")
            res = subprocess.run(['ffmpeg', '-y', '-i', path, '-c', 'copy', out_path], capture_output=True)
            if res.returncode == 0 and os.path.exists(out_path):
                LOG.info(f"Remux successful: {out_path}")
                return out_path
            else:
                LOG.warning(f"ffmpeg remux failed: {res.returncode}")
                return path
        except FileNotFoundError:
            LOG.warning("ffmpeg not found; skipping remux")
            return path
        except Exception as e:
            LOG.warning(f"Remux error: {e}")
            return path

    loop = asyncio.get_event_loop()
    new_path = await loop.run_in_executor(None, remux_ts_to_mp4, file_path)
    
    if new_path != file_path:
        try:
            await safe_edit(f"✅ Remux complete: {os.path.basename(new_path)}")
        except Exception:
            pass
    else:
        try:
            await safe_edit("ℹ️ Remux skipped or failed, will use original file")
        except Exception:
            pass
    
    return new_path

async def upload_large_file(
    bot_client: Client,
    file_client: Optional[Client],
    upload_path: str,
    title: str,
    item: Dict[str, Any],
    file_size_bytes: int,
    safe_edit
) -> Tuple[bool, list]:
    base, ext = os.path.splitext(upload_path)
    part1 = f"{base}.part1{ext}"
    part2 = f"{base}.part2{ext}"
    part_hashes = []
    uploaded = False

    try:
        half = file_size_bytes // 2
        with open(upload_path, 'rb') as fsrc:
            with open(part1, 'wb') as p1:
                p1.write(fsrc.read(half))
            with open(part2, 'wb') as p2:
                p2.write(fsrc.read())

        msg1 = await upload_file(file_client or bot_client, part1, title=f"{title} - Part 1", item=item)
        if msg1 is not None:
            uploaded = True
            h1 = generate_hash(20)
            add_file_record(f"{title} - Part 1", h1, msg1.id)
            part_hashes.append(h1)

        msg2 = await upload_file(file_client or bot_client, part2, title=f"{title} - Part 2", item=item)
        if msg2 is not None:
            uploaded = True
            h2 = generate_hash(20)
            add_file_record(f"{title} - Part 2", h2, msg2.id)
            part_hashes.append(h2)

    except Exception as e:
        LOG.warning(f"Failed to split/upload parts: {e}")
    finally:
        try:
            if os.path.exists(part1):
                os.remove(part1)
        except Exception:
            pass
        try:
            if os.path.exists(part2):
                os.remove(part2)
        except Exception:
            pass
    
    return uploaded, part_hashes

async def upload_single_file(
    bot_client: Client,
    file_client: Optional[Client],
    upload_path: str,
    title: str,
    item: Dict[str, Any],
    caption: str
) -> Tuple[bool, Optional[str]]:
    upload_msg = await upload_file(file_client or bot_client, upload_path, title=title, item=item)

    if upload_msg is not None:
        file_hash = generate_hash(20)
        add_file_record(title, file_hash, upload_msg.id)
        return True, file_hash
    
    return False, None

async def post_to_main_channel(
    bot_client: Client,
    file_client: Optional[Client],
    item: Dict[str, Any],
    caption: str,
    file_hash: Optional[str],
    part_hashes: list,
    video_path: Optional[str] = None
):
    try:
        forward_client = file_client if file_client else bot_client
        bot_user = await forward_client.get_me()
        bot_username = getattr(bot_user, 'username', '') or ''

        title = item.get('title', 'Video')
        post_caption = create_enhanced_caption(title, item, video_path)

        thumb_image = await generate_thumbnail(item)

        if thumb_image and os.path.exists(thumb_image):
            main_msg = await bot_client.send_photo(SETTINGS.main_channel, thumb_image, caption=post_caption)
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
        
        try:
            if main_msg is not None:
                if part_hashes and len(part_hashes) >= 2:
                    kb = InlineKeyboardMarkup([[
                        InlineKeyboardButton(text="Part 1", url=f"https://t.me/{bot_username}?start={part_hashes[0]}"),
                        InlineKeyboardButton(text="Part 2", url=f"https://t.me/{bot_username}?start={part_hashes[1]}")
                    ]])
                    chat_id = getattr(main_msg, 'chat', None)
                    mid = getattr(main_msg, 'id', None)
                    if chat_id is not None and mid is not None:
                        await bot_client.edit_message_reply_markup(
                            chat_id=chat_id.id if hasattr(chat_id, 'id') else chat_id,
                            message_id=mid,
                            reply_markup=kb
                        )
                else:
                    if file_hash:
                        await add_download_button(bot_client, main_msg, bot_username, file_hash)
        except Exception as e:
            LOG.warning(f"Failed to add download button(s): {e}")

    except Exception as e:
        LOG.error(f"Failed to post to main channel: {e}")

async def generate_thumbnail(item: Dict[str, Any]) -> Optional[str]:
    
    thumbnail_url = item.get('thumbnail')
    if not thumbnail_url:
        LOG.warning("No thumbnail URL in item")
        return None
    
    try:
        import requests
        import tempfile
        
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
        thumb_path = os.path.join(thumb_dir, f"{code}{ext}")
        
        with open(thumb_path, 'wb') as f:
            f.write(response.content)
        
        LOG.info(f"Downloaded thumbnail: {thumb_path}")
        return thumb_path
        
    except Exception as e:
        LOG.error(f"Failed to download thumbnail from {thumbnail_url}: {e}")
        return None

async def cleanup_files(original_file: str, processed_file: str):
    try:
        if os.path.exists(original_file):
            os.remove(original_file)
            LOG.info(f"Cleaned up file: {original_file}")
    except Exception as cleanup_error:
        LOG.warning(f"Failed to cleanup file {original_file}: {cleanup_error}")

    if processed_file and processed_file != original_file and os.path.exists(processed_file):
        try:
            os.remove(processed_file)
            LOG.info(f"Cleaned up remuxed file: {processed_file}")
        except Exception as cleanup_error2:
            LOG.warning(f"Failed to cleanup remuxed file {processed_file}: {cleanup_error2}")
