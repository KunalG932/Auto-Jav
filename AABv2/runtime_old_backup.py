import asyncio
import logging
import os
import time
from typing import List, Dict, Any, Optional
import subprocess
from AABv2.services.start import start_cmd
from .config import SETTINGS
from .clients import create_clients
from .db import (
    client as mongo_client,
    get_last_hash, set_last_hash,
    add_file_record, get_file_by_hash,
    is_working, set_working,
)
from .services.feed import fetch_jav, get_title, sha1
from .services.downloader import download_torrent
from .services.uploader import upload_file, build_caption, add_download_button, prepare_caption_content
from .services.ai_caption import fetch_and_format, format_for_post
from .utils import generate_hash
from pyrogram.client import Client
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.handlers.message_handler import MessageHandler

LOG = logging.getLogger("AABv2")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(), 
        logging.FileHandler('logging_v2.txt')
    ]
)

DOWNLOAD_LOCK = asyncio.Semaphore(1)

bot: Optional[Client] = None
file_client: Optional[Client] = None


async def send_logs_to_user(client: Client, user_id: int) -> bool:
    try:
        if os.path.exists('logging_v2.txt'):
            await client.send_document(
                user_id, 
                'logging_v2.txt', 
                caption="AABv2 logs"
            )
            return True
        else:
            await client.send_message(user_id, "No log file found.")
            return False
    except Exception as e:
        LOG.error(f"Failed to send logs: {e}")
        return False


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
            from .db import files as files_collection
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

    try:
        msg = None
        
        # New API structure: torrent_links is a list of dicts with 'magnet' and 'torrent' keys
        torrent_links = item.get('torrent_links', [])
        magnet = None
        
        if isinstance(torrent_links, list) and torrent_links:
            # Get the first magnet link from torrent_links
            for link in torrent_links:
                if isinstance(link, dict):
                    mag = link.get('magnet')
                    if mag and isinstance(mag, str) and mag.startswith('magnet:'):
                        magnet = mag
                        break
        
        uploaded = False
        
        if magnet and isinstance(magnet, str):
            async with DOWNLOAD_LOCK:
                try:
                    os.makedirs('./downloads', exist_ok=True)
                    
                    update_msg = await bot_client.send_message(
                        SETTINGS.production_chat,
                        f"📥 Downloading: {title}"
                    )

                    async def safe_edit(text: str):
                        try:
                            if not update_msg:
                                return
                            chat = getattr(update_msg, 'chat', None)
                            mid = getattr(update_msg, 'id', None)
                            if chat is None or mid is None:
                                return
                            await bot_client.edit_message_text(
                                chat_id=chat.id,
                                message_id=mid,
                                text=text,
                            )
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
                            text = (
                                f"📥 Downloading: {title}\n"
                                f"Stage: {stage} | {pct:.1f}%\n"
                                f"Speed: {down:.1f} kB/s | Peers: {peers} | Elapsed: {elapsed}s"
                            )
                            try:
                                asyncio.run_coroutine_threadsafe(
                                    safe_edit(text),
                                    loop,
                                )
                            except Exception:
                                pass
                        except Exception:
                            pass

                    info = await loop.run_in_executor(
                        None, download_torrent, magnet, _progress_cb
                    )

                    if info and info.get('file') and os.path.exists(info['file']):
                        try:
                            await safe_edit(f"✅ Download complete: {title}\nStarting upload...")
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
                                res = subprocess.run([
                                    'ffmpeg', '-y', '-i', path, '-c', 'copy', out_path
                                ], capture_output=True)
                                if res.returncode == 0 and os.path.exists(out_path):
                                    LOG.info(f"Remux successful: {out_path}")
                                    return out_path
                                else:
                                    LOG.warning(f"ffmpeg remux failed: {res.returncode} stdout={res.stdout[:200]} stderr={res.stderr[:200]}")
                                    return path
                            except FileNotFoundError:
                                LOG.warning("ffmpeg not found on PATH; skipping remux")
                                return path
                            except Exception as e:
                                LOG.warning(f"Remux error: {e}")
                                return path

                        upload_path = info['file']

                        if os.path.splitext(upload_path)[1].lower() == '.ts':
                            try:
                                try:
                                    await safe_edit(f"🔁 Remuxing .ts → .mp4 for: {title}")
                                except Exception:
                                    pass
                                loop = asyncio.get_event_loop()
                                new_path = await loop.run_in_executor(None, remux_ts_to_mp4, upload_path)
                                if new_path != upload_path:
                                    try:
                                        await safe_edit(f"✅ Remux complete: {os.path.basename(new_path)}")
                                    except Exception:
                                        pass
                                    upload_path = new_path
                                else:
                                    try:
                                        await safe_edit(f"ℹ️ Remux skipped or failed, will use original file")
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                        try:
                            await safe_edit(f"🔄 Encoding/Converting file: {os.path.basename(upload_path)}")
                        except Exception:
                            pass

                        try:
                            LOG.info("Encoding/size-reduction disabled by configuration; proceeding with original file")
                            await safe_edit(f"ℹ️ Encoding skipped: proceeding with original file")
                        except Exception:
                            pass

                        try:
                            try:
                                up_size = os.path.getsize(upload_path) / (1024.0 * 1024.0)
                            except Exception:
                                up_size = 0.0
                            LOG.info(f"Preparing to upload file: {upload_path} ({up_size:.1f} MiB); file_client={'present' if file_client else 'missing'}")
                        except Exception:
                            pass

                        try:
                            file_size_bytes = os.path.getsize(upload_path)
                        except Exception:
                            file_size_bytes = 0

                        part_hashes = []
                        uploaded = False
                        file_hash = None

                        TWO_GB = 2 * 1024 * 1024 * 1024
                        if file_size_bytes > TWO_GB:
                            try:
                                await safe_edit(f"🔀 File >2GiB detected; splitting into 2 parts for upload")
                            except Exception:
                                pass

                            base, ext = os.path.splitext(upload_path)
                            part1 = f"{base}.part1{ext}"
                            part2 = f"{base}.part2{ext}"

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
                        else:
                            upload_msg = await upload_file(file_client or bot_client, upload_path, title=title, item=item)

                            if upload_msg is not None:
                                uploaded = True
                                file_hash = generate_hash(20)
                                add_file_record(title, file_hash, upload_msg.id)

                            thumb_image = None
                            try:
                                def make_blurred_thumbnail(in_path: str, out_path: str, at_sec: int = 1, width: int = 640, blur: int = 10) -> str:
                                    cmd = [
                                        'ffmpeg', '-y', '-ss', str(at_sec), '-i', in_path,
                                        '-frames:v', '1', '-vf', f"scale={width}:-2,boxblur={blur}:1", out_path
                                    ]
                                    LOG.info(f"Creating blurred thumbnail: {' '.join(cmd)}")
                                    res = subprocess.run(cmd, capture_output=True)
                                    if res.returncode == 0 and os.path.exists(out_path):
                                        return out_path
                                    LOG.warning(f"Thumbnail generation failed (rc={res.returncode}) stdout={res.stdout[:200]} stderr={res.stderr[:200]}")
                                    return ''

                                base, _ = os.path.splitext(upload_path)
                                thumb_image = f"{base}.thumb.jpg"
                                source_for_thumb = upload_path

                                try:
                                    def get_duration(p: str) -> float:
                                        try:
                                            res = subprocess.run([
                                                'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', p
                                            ], capture_output=True, text=True, timeout=10)
                                            if res.returncode == 0 and res.stdout:
                                                import json
                                                info = json.loads(res.stdout)
                                                dur = float(info.get('format', {}).get('duration') or 0.0)
                                                return dur
                                        except Exception:
                                            return 0.0
                                        return 0.0

                                    duration = get_duration(source_for_thumb)
                                    at_sec = 1
                                    if duration and duration > 2.0:
                                        at_sec = max(1, int(duration / 2))
                                except Exception:
                                    at_sec = 1

                                thumb_result = await asyncio.get_event_loop().run_in_executor(None, make_blurred_thumbnail, source_for_thumb, thumb_image, at_sec)
                                if not thumb_result:
                                    thumb_image = None
                            except Exception as e:
                                LOG.warning(f"Failed to create thumbnail: {e}")

                            try:
                                forward_client = file_client if file_client else bot_client
                                bot_user = await forward_client.get_me()
                                bot_username = getattr(bot_user, 'username', '') or ''

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

                                # If AI caption is available, post only the AI caption (formatted).
                                # Otherwise fall back to the generated metadata caption.
                                if ai_caption and isinstance(ai_caption, str):
                                    try:
                                        formatted = format_for_post(ai_caption)
                                        post_caption = formatted if formatted else ai_caption
                                    except Exception:
                                        post_caption = ai_caption
                                else:
                                    post_caption = caption

                                if thumb_image and os.path.exists(thumb_image):
                                    main_msg = await bot_client.send_photo(
                                        SETTINGS.main_channel,
                                        thumb_image,
                                        caption=post_caption,
                                    )
                                else:
                                    main_msg = await bot_client.send_message(SETTINGS.main_channel, post_caption)
                                
                                try:
                                    if main_msg is not None:
                                        try:
                                            sticker_id = "CAACAgUAAx0CfPp_PwABAX9taNZsQyInPz500GChLCk3uconkqwAAhESAALeIohXvOSc_GX-md4eBA"
                                            mid = getattr(main_msg, 'id', None)
                                            
                                            async def _send_sticker_async(sid, reply_id):
                                                try:
                                                    await bot_client.send_sticker(SETTINGS.main_channel, sid, reply_to_message_id=reply_id)
                                                except Exception as e:
                                                    LOG.warning(f"Failed to send sticker after main post (background): {e}")

                                            asyncio.create_task(_send_sticker_async(sticker_id, mid))
                                        except Exception as e:
                                            LOG.warning(f"Failed to schedule sticker send after main post: {e}")
                                except Exception:
                                    pass
                                
                                try:
                                    LOG.debug(f"Preparing to attach buttons: file_hash={file_hash} part_hashes={len(part_hashes) if part_hashes else 0}")
                                    LOG.debug(f"main_msg summary: chat={getattr(main_msg, 'chat', None)} id={getattr(main_msg, 'id', None)}")
                                    if main_msg is not None:
                                        if part_hashes and len(part_hashes) >= 2:
                                            try:
                                                kb = InlineKeyboardMarkup(
                                                    [[
                                                        InlineKeyboardButton(text="Part 1", url=f"https://t.me/{bot_username}?start={part_hashes[0]}"),
                                                        InlineKeyboardButton(text="Part 2", url=f"https://t.me/{bot_username}?start={part_hashes[1]}")
                                                    ]]
                                                )
                                                chat_id = getattr(main_msg, 'chat', None)
                                                mid = getattr(main_msg, 'id', None)
                                                LOG.info(f"Attaching two-part buttons: part_hashes={part_hashes} chat_id={chat_id} mid={mid}")
                                                if chat_id is not None and mid is not None:
                                                    await bot_client.edit_message_reply_markup(chat_id=chat_id.id if hasattr(chat_id, 'id') else chat_id, message_id=mid, reply_markup=kb)
                                            except Exception as e:
                                                LOG.warning(f"Failed to set two-part buttons: {e}")
                                        else:
                                            try:
                                                LOG.info(f"Attaching single download button: file_hash={file_hash}")
                                                if file_hash:
                                                    await add_download_button(bot_client, main_msg, bot_username, file_hash)
                                            except Exception as e:
                                                LOG.warning(f"Failed to add single download button: {e}")
                                    else:
                                        LOG.warning("Main channel message is None; skipping download buttons")
                                except Exception as e:
                                    LOG.warning(f"Failed to add download button(s) to main post: {e}")

                            except Exception as e:
                                LOG.error(f"Failed to post to main channel: {e}")
                        
                        try:
                            try:
                                if os.path.exists(info['file']):
                                    os.remove(info['file'])
                                    LOG.info(f"Cleaned up file: {info['file']}")
                            except Exception as cleanup_error:
                                LOG.warning(f"Failed to cleanup file {info['file']}: {cleanup_error}")

                            if upload_path and upload_path != info['file'] and os.path.exists(upload_path):
                                try:
                                    os.remove(upload_path)
                                    LOG.info(f"Cleaned up remuxed file: {upload_path}")
                                except Exception as cleanup_error2:
                                    LOG.warning(f"Failed to cleanup remuxed file {upload_path}: {cleanup_error2}")

                        except Exception as cleanup_error:
                            LOG.warning(f"Failed during cleanup: {cleanup_error}")
                    
                    try:
                        await update_msg.delete()
                    except Exception:
                        pass
                        
                except Exception as download_error:
                    LOG.error(f"Download/upload failed for {title}: {download_error}")
        else:
            # No magnet link available - post with API thumbnail
            LOG.info(f"No magnet link for {title}, posting with API thumbnail")
            try:
                forward_client = file_client if file_client else bot_client
                bot_user = await forward_client.get_me()
                bot_username = getattr(bot_user, 'username', '') or ''

                # Generate AI caption
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

                # Prepare caption
                if ai_caption and isinstance(ai_caption, str):
                    try:
                        formatted = format_for_post(ai_caption)
                        post_caption = formatted if formatted else ai_caption
                    except Exception:
                        post_caption = ai_caption
                else:
                    post_caption = caption

                # Get thumbnail from API
                api_thumbnail = item.get('thumbnail')
                
                # Add magnet link button if available in torrent_links
                buttons = []
                if torrent_links:
                    for link in torrent_links:
                        if isinstance(link, dict):
                            mag = link.get('magnet')
                            if mag and isinstance(mag, str):
                                buttons.append([InlineKeyboardButton("📥 Magnet Link", url=mag)])
                                break
                
                # Add source URL button if available
                source_url = item.get('url')
                if source_url:
                    buttons.append([InlineKeyboardButton("🔗 Source", url=source_url)])
                
                kb = InlineKeyboardMarkup(buttons) if buttons else None

                # Post to main channel
                if api_thumbnail:
                    try:
                        if kb:
                            main_msg = await bot_client.send_photo(
                                SETTINGS.main_channel,
                                api_thumbnail,
                                caption=post_caption,
                                reply_markup=kb
                            )
                        else:
                            main_msg = await bot_client.send_photo(
                                SETTINGS.main_channel,
                                api_thumbnail,
                                caption=post_caption
                            )
                    except Exception as e:
                        LOG.warning(f"Failed to send photo with API thumbnail: {e}, falling back to text")
                        if kb:
                            main_msg = await bot_client.send_message(
                                SETTINGS.main_channel, 
                                post_caption,
                                reply_markup=kb
                            )
                        else:
                            main_msg = await bot_client.send_message(
                                SETTINGS.main_channel, 
                                post_caption
                            )
                else:
                    if kb:
                        main_msg = await bot_client.send_message(
                            SETTINGS.main_channel, 
                            post_caption,
                            reply_markup=kb
                        )
                    else:
                        main_msg = await bot_client.send_message(
                            SETTINGS.main_channel, 
                            post_caption
                        )
                
                # Send sticker
                try:
                    if main_msg is not None:
                        try:
                            sticker_id = "CAACAgUAAx0CfPp_PwABAX9taNZsQyInPz500GChLCk3uconkqwAAhESAALeIohXvOSc_GX-md4eBA"
                            mid = getattr(main_msg, 'id', None)
                            
                            async def _send_sticker_async(sid, reply_id):
                                try:
                                    await bot_client.send_sticker(SETTINGS.main_channel, sid, reply_to_message_id=reply_id)
                                except Exception as e:
                                    LOG.warning(f"Failed to send sticker after main post (background): {e}")

                            asyncio.create_task(_send_sticker_async(sticker_id, mid))
                        except Exception as e:
                            LOG.warning(f"Failed to schedule sticker send after main post: {e}")
                except Exception:
                    pass

                LOG.info(f"Posted {title} to main channel (no file uploaded)")
                
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
            
    except Exception as e:
        LOG.error(f"Failed to process item '{title}': {e}")


def check_for_new_items() -> Optional[List[Dict[str, Any]]]:
    try:
        results = fetch_jav()
        if not results:
            LOG.info("No results from feed")
            return None

        last_hash = get_last_hash()
        LOG.info(f"Current stored last_hash: {last_hash}")

        new_items: List[Dict[str, Any]] = []
        first_hash: Optional[str] = None

        for idx, item in enumerate(results):
            title = get_title(item) or ""
            current_hash = sha1(title)

            if idx == 0:
                first_hash = current_hash

            if last_hash and current_hash == last_hash:
                break

            try:
                if get_file_by_hash(current_hash):
                    LOG.info(f"Skipping already-uploaded item by hash: {title} -> {current_hash}")
                    continue

                try:
                    from .db import files as files_collection
                    if title and files_collection.count_documents({"name": title}, limit=1) > 0:
                        LOG.info(f"Skipping already-uploaded item by name: {title}")
                        continue
                except Exception:
                    pass

            except Exception:
                LOG.warning(f"DB lookup failed while checking item '{title}'; will include it")

            new_items.append(item)

        try:
            LOG.debug(f"Feed returned {len(results)} items. New items count (before reverse): {len(new_items)}")
            if results:
                top_preview = []
                for i, it in enumerate(results[:5]):
                    t = get_title(it) or '<no-title>'
                    top_preview.append(f"{i}:{t} -> {sha1(get_title(it) or '')}")
                LOG.info("Top feed preview: " + " | ".join(top_preview))
        except Exception:
            pass

        if first_hash:
            if last_hash is not None:
                LOG.info(f"Setting last_hash to newest item: {first_hash}")
                set_last_hash(first_hash)
            else:
                LOG.info(f"Not setting last_hash on first run; newest item would be: {first_hash}")

        new_items.reverse()
        LOG.info(f"Found {len(new_items)} new items")
        return new_items if new_items else None

    except Exception as e:
        LOG.error(f"Error checking for new items: {e}")
        return None

async def worker_loop():
    global bot, file_client
    
    while True:
        try:
            if not is_working():
                set_working(True)
                
                try:
                    new_items = check_for_new_items()
                    
                    if new_items:
                        LOG.info(f"Processing {len(new_items)} new items")
                        for item in new_items:
                            await process_item(bot, file_client, item)
                    else:
                        LOG.debug("No new items found")
                        
                except Exception as process_error:
                    LOG.error(f"Error in worker loop processing: {process_error}")
                finally:
                    set_working(False)
            else:
                LOG.debug("Bot is already working, skipping this cycle")
                
        except Exception as loop_error:
            LOG.error(f"Error in worker loop: {loop_error}")
        
        await asyncio.sleep(SETTINGS.check_interval_sec)


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
    
    status_text = f"""
🤖 **AABv2 Status**

**Working**: {'✅ Yes' if working else '❌ No'}
**Last Hash**: `{last_hash or 'None'}`
**Downloads Directory**: {'✅ Exists' if os.path.exists('./downloads') else '❌ Missing'}
**Log File**: {'✅ Exists' if os.path.exists('logging_v2.txt') else '❌ Missing'}
"""
    await message.reply_text(status_text)


async def start_command(client: Client, message: Message):
    try:
        import re
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

        forwarder = file_client if file_client else client
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
            LOG.info(f"File forwarded to user {getattr(message.from_user, 'id', 'unknown')} for hash {file_hash} using {'file_client' if file_client else 'client'}")
        except Exception as e:
            LOG.exception(f"Failed to forward message {message_id} from {SETTINGS.files_channel} to {chat_id}: {e}")
            await message.reply_text("❌ Failed to send file. Contact admin.")
        
    except Exception as e:
        LOG.error(f"Error in start command: {e}")
        await message.reply_text("❌ An error occurred while processing your request")

async def main():
    global bot, file_client
    
    try:
        mongo_client.admin.command('ping')
        LOG.info("✅ MongoDB connected successfully")
    except Exception as e:
        LOG.critical(f"❌ MongoDB connection failed: {e}")
        return

    try:
        try:
            bot, file_client = create_clients()
        except Exception as e:
            LOG.critical(f"Failed to create Telegram clients: {e}")
            return

        LOG.info("Starting Telegram clients...")
        if file_client:
            try:
                await file_client.start()
            except Exception as e:
                LOG.critical(f"Failed to start file_client: {e}")
                return

        try:
            await bot.start()
        except Exception as e:
            LOG.critical(f"Failed to start main bot: {e}")
            return

        try:
            owner_filter = filters.user(list(SETTINGS.owner_ids))
            bot.add_handler(MessageHandler(alive_command, filters.command("alive") & owner_filter))
            bot.add_handler(MessageHandler(logs_command, filters.command("logs") & owner_filter))
            bot.add_handler(MessageHandler(status_command, filters.command("status") & owner_filter))
            bot.add_handler(MessageHandler(start_command, filters.command("start") & filters.private))
            
            if file_client:
                try:
                    file_client.add_handler(MessageHandler(alive_command, filters.command("alive") & owner_filter))
                    file_client.add_handler(MessageHandler(logs_command, filters.command("logs") & owner_filter))
                    file_client.add_handler(MessageHandler(status_command, filters.command("status") & owner_filter))
                    file_client.add_handler(MessageHandler(start_command, filters.command("start") & filters.private))
                    LOG.info("✅ Command handlers registered on file client")
                except Exception as e:
                    LOG.warning(f"Failed to register handlers on file_client: {e}")
            LOG.info("✅ Command handlers registered on main bot")
        except Exception as e:
            LOG.critical(f"Failed to register handlers on bot: {e}")
            return

        LOG.info("✅ Telegram clients started successfully")
        
        set_working(False)
        
        try:
            os.makedirs('./downloads', exist_ok=True)
            LOG.info("✅ Downloads directory ready")
        except Exception as dir_error:
            LOG.warning(f"Failed to create downloads directory: {dir_error}")

        LOG.info(f"🚀 AABv2 started successfully! Check interval: {SETTINGS.check_interval_sec}s")
        
        await worker_loop()
        
    except Exception as e:
        LOG.critical(f"❌ Failed to start application: {e}")
    finally:
        try:
            if file_client:
                try:
                    await file_client.stop()
                except Exception:
                    LOG.warning("Error stopping file_client during cleanup")
            if bot:
                try:
                    await bot.stop()
                except Exception:
                    LOG.warning("Error stopping main bot during cleanup")
            LOG.info("✅ Clients stopped gracefully")
        except Exception as cleanup_error:
            LOG.error(f"Error during cleanup: {cleanup_error}")


def run():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        LOG.info("👋 Application stopped by user")
    except Exception as e:
        LOG.critical(f"💥 Application crashed: {e}")