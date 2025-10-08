
import os
import time
import asyncio
import logging
import subprocess
from typing import Dict, Any, Optional, Tuple
from pyrogram.client import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import errors
from ..config import SETTINGS
from ..services.downloader import download_torrent
from ..services.uploader import upload_file, add_download_button, prepare_caption_content
from ..api.ai_caption import format_for_post, create_enhanced_caption
from ..utils import generate_hash
from ..utils.progress_file import (
    format_download_progress,
    format_encoding_progress,
    format_stage_status,
    should_emit_progress,
)
from ..utils.telegraph import create_telegraph_preview_async
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
        from ..utils import handle_flood_wait
        
        try:
            if not update_msg:
                return
            chat = getattr(update_msg, 'chat', None)
            mid = getattr(update_msg, 'id', None)
            if chat is None or mid is None:
                return
            
            chat_id = chat.id
            message_id = mid
            
            try:
                await handle_flood_wait(
                    bot_client.edit_message_text,
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    operation_name="edit progress message"
                )
            except Exception as e:
                error_msg = str(e).lower()
                if "timed out" in error_msg:
                    LOG.debug(f"Edit message timeout (expected): {e}")
                elif "message is not modified" in error_msg or "message_not_modified" in error_msg:
                    LOG.debug(f"Message already up to date: {e}")
                else:
                    LOG.warning(f"Edit message error: {e}")
        except Exception as outer_e:
            LOG.warning(f"Unexpected error in safe_edit: {outer_e}")
    
    loop = asyncio.get_event_loop()
    last_edit_ts = 0.0
    last_progress_pct = 0.0
    last_stage = ""

    def _progress_cb(stats: Dict[str, float]):
        nonlocal last_edit_ts, last_progress_pct, last_stage
        try:
            now = time.time()
            stage = str(stats.get("stage", "downloading") or "downloading").lower()

            raw_percent = stats.get("progress_pct", 0.0)
            percent = float(raw_percent)

            down_rate = float(stats.get("down_rate_kbs", 0.0))
            peers_value = int(stats.get("peers", 0.0))
            elapsed_value = int(stats.get("elapsed", 0.0))

            force_update = stage != last_stage
            if not should_emit_progress(
                now,
                last_edit_ts,
                last_progress_pct,
                percent,
                min_interval=5.0,
                min_progress=5.0,
                force=force_update,
            ):
                return

            last_edit_ts = now
            if percent is not None:
                last_progress_pct = percent
            last_stage = stage

            text = format_download_progress(
                title,
                percent=percent,
                stage=stage,
                speed=down_rate,
                peers=peers_value,
                elapsed=elapsed_value,
            )
            try:
                asyncio.run_coroutine_threadsafe(safe_edit(text), loop)
            except Exception:
                pass
        except Exception:
            pass

    info = await loop.run_in_executor(None, download_torrent, magnet, _progress_cb, title)
    
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
            await safe_edit(
                format_stage_status(
                    "download",
                    title,
                    "Download complete. Preparing upload…",
                    percent=100.0,
                )
            )
        except Exception:
            pass

        try:
            upload_path = await remux_if_needed(info['file'], safe_edit, title)
            
            if SETTINGS.enable_encoding:
                try:
                    await safe_edit(
                        format_stage_status(
                            "encode",
                            title,
                            f"Starting encoding to 720p ({os.path.basename(upload_path)})",
                            show_bar=False,
                        )
                    )
                    LOG.info(f"Starting FFEncoder encoding for: {upload_path}")
                    
                    from ..services.encode import FFEncoder
                    from ..services.downloader import sanitize_filename
                    
                    sanitized_title = sanitize_filename(title)
                    output_name = f"[TW] {sanitized_title} @The_Wyverns.mp4"
                    
                    last_update_time = 0.0
                    last_encoding_percent = 0.0

                    async def encoding_progress_callback(percent: float, current_sec: float, total_sec: float):
                        nonlocal last_update_time, last_encoding_percent
                        current_time = time.time()

                        if not should_emit_progress(
                            current_time,
                            last_update_time,
                            last_encoding_percent,
                            percent,
                            min_interval=5.0,
                            min_progress=2.0,
                            force=percent >= 99.9,
                        ):
                            return

                        last_update_time = current_time
                        last_encoding_percent = percent

                        status_text = format_encoding_progress(
                            title,
                            percent=percent,
                            current_sec=current_sec,
                            total_sec=total_sec,
                            status=f"Encoding to 720p ({os.path.basename(upload_path)})",
                        )

                        await safe_edit(status_text)
                    
                    encoder = FFEncoder(upload_path, output_name, progress_callback=encoding_progress_callback)
                    
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
                        await safe_edit(
                            format_stage_status(
                                "encode",
                                title,
                                status=(
                                    f"Encoding complete → {os.path.basename(upload_path)}"
                                    f" (Δ {abs(reduction):.1f}%)"
                                ),
                                show_bar=False,
                            )
                        )
                    else:
                        LOG.warning("FFEncoder encoding failed, using original file")
                        await safe_edit(
                            format_stage_status(
                                "encode",
                                title,
                                "Encoding failed, using original file",
                                show_bar=False,
                            )
                        )
                except Exception as e:
                    LOG.error(f"FFEncoder encoding error: {e}", exc_info=True)
                    await safe_edit(
                        format_stage_status(
                            "encode",
                            title,
                            "Encoding failed, using original file",
                            show_bar=False,
                        )
                    )
            else:
                LOG.info("Encoding disabled; proceeding with original file")
                try:
                    await safe_edit(
                        format_stage_status(
                            "encode",
                            title,
                            "Encoding skipped; using original file",
                            show_bar=False,
                        )
                    )
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
                await safe_edit(
                    format_stage_status(
                        "split",
                        title,
                        "File >2 GiB detected; splitting into two parts",
                        show_bar=False,
                    )
                )
                uploaded, part_hashes = await upload_large_file(
                    bot_client, file_client, upload_path, title, item, file_size_bytes, safe_edit
                )
            else:
                LOG.info("File <=2GB, uploading as single file")
                try:
                    await safe_edit(
                        format_stage_status(
                            "upload",
                            title,
                            "Uploading to Telegram…",
                            show_bar=False,
                        )
                    )
                except Exception:
                    pass
                uploaded, file_hash = await upload_single_file(
                    bot_client, file_client, upload_path, title, item, caption
                )

            LOG.info(f"Upload completed: uploaded={uploaded}, file_hash={file_hash}, part_hashes={part_hashes}")
            
            if uploaded:
                LOG.info("Starting post to main channel...")
                try:
                    await safe_edit(
                        format_stage_status(
                            "completed",
                            title,
                            "Upload complete. Posting to main channel…",
                            show_bar=False,
                        )
                    )
                except Exception:
                    pass
                await post_to_main_channel(bot_client, file_client, item, caption, file_hash, part_hashes, upload_path)
                LOG.info(f"✅ Successfully uploaded and posted: {title}")
                
                await cleanup_files(info['file'], upload_path)
                
                await cleanup_directories()
            else:
                LOG.error(f"❌ Upload failed for: {title}")
                try:
                    await safe_edit(
                        format_stage_status(
                            "upload",
                            title,
                            "Upload failed. Cleaning up…",
                            show_bar=False,
                        )
                    )
                except Exception:
                    pass
                await cleanup_files(info['file'], upload_path)
            
        except Exception as upload_error:
            LOG.error(f"❌ Error during upload process for {title}: {upload_error}", exc_info=True)
            uploaded = False
            
    else:
        LOG.error(f"❌ Download failed - no file info returned for: {title}")
        try:
            await bot_client.send_message(
                SETTINGS.production_chat,
                f"❌ **Download Failed**\n\n"
                f"Title: `{title}`\n"
                f"Reason: No peers/seeders available or timeout\n\n"
                f"⚠️ This video has been marked as failed and won't be retried."
            )
        except Exception as notify_error:
            LOG.warning(f"Failed to notify production chat: {notify_error}")
    
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
        await safe_edit(
            format_stage_status(
                "remux",
                title,
                "Remuxing .ts → .mp4",
                show_bar=False,
            )
        )
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
            await safe_edit(
                format_stage_status(
                    "remux",
                    title,
                    f"Remux complete → {os.path.basename(new_path)}",
                    show_bar=False,
                )
            )
        except Exception:
            pass
    else:
        try:
            await safe_edit(
                format_stage_status(
                    "remux",
                    title,
                    "Remux skipped or failed; using original file",
                    show_bar=False,
                )
            )
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
        
        LOG.info("Generating enhanced caption with AI...")
        post_caption = create_enhanced_caption(title, item, video_path)
        LOG.info(f"Caption generated: {post_caption[:100]}...")
        
        telegraph_url = None
        if video_path and os.path.exists(video_path):
            try:
                LOG.info("🎬 Creating Telegraph preview with video screenshots...")
                telegraph_url = await create_telegraph_preview_async(
                    video_path=video_path,
                    title=title,
                    description=f"Preview for {title}",
                    num_screenshots=6
                )
                if telegraph_url:
                    LOG.info(f"✅ Telegraph preview created: {telegraph_url}")
                else:
                    LOG.warning("Failed to create Telegraph preview")
            except Exception as tg_error:
                LOG.error(f"Error creating Telegraph preview: {tg_error}", exc_info=True)

        default_thumb = "AAB/utils/thumb.jpeg"
        thumb_image = None
        
        if os.path.exists(default_thumb):
            thumb_image = default_thumb
            LOG.info(f"✅ Using default thumbnail: {thumb_image}")
        else:
            LOG.warning(f"⚠️ Default thumbnail not found at: {default_thumb}")
        
        if thumb_image:
            try:
                from ..utils import handle_flood_wait
                
                LOG.info(f"📤 Posting to main channel with thumbnail...")
                main_msg = await handle_flood_wait(
                    bot_client.send_photo,
                    SETTINGS.main_channel,
                    thumb_image,
                    caption=post_caption,
                    operation_name="send photo to main channel"
                )
                LOG.info("✅ Successfully posted with thumbnail")
            except Exception as photo_error:
                LOG.error(f"❌ Failed to send photo: {photo_error}")
                LOG.info("🔄 Trying text message instead...")
                main_msg = await bot_client.send_message(SETTINGS.main_channel, post_caption)
        else:
            LOG.warning("⚠️ No thumbnail available, posting text only")
            main_msg = await bot_client.send_message(SETTINGS.main_channel, post_caption)
        
        try:
            if main_msg is not None:
                from ..utils import handle_flood_wait
                
                sticker_id = SETTINGS.sticker_id
                mid = getattr(main_msg, 'id', None)
                
                async def _send_sticker_async(sid, reply_id):
                    try:
                        await handle_flood_wait(
                            bot_client.send_sticker,
                            SETTINGS.main_channel,
                            sid,
                            reply_to_message_id=reply_id,
                            operation_name="send sticker"
                        )
                        LOG.info("✅ Sticker sent successfully")
                    except Exception as e:
                        LOG.warning(f"Failed to send sticker: {e}")
                
                if mid:
                    asyncio.create_task(_send_sticker_async(sticker_id, mid))
        except Exception:
            pass        
        try:
            if main_msg is not None:
                from ..utils import add_download_buttons
                
                await add_download_buttons(
                    bot_client,
                    main_msg,
                    bot_username,
                    file_hash=file_hash,
                    part_hashes=part_hashes if part_hashes and len(part_hashes) >= 2 else None,
                    telegraph_url=telegraph_url
                )
        except Exception as e:
            LOG.warning(f"Failed to add download button(s): {e}")

    except Exception as e:
        LOG.error(f"Failed to post to main channel: {e}")

async def generate_thumbnail(item: Dict[str, Any]) -> Optional[str]:
    from ..utils import download_thumbnail
    
    thumbnail_url = item.get('thumbnail')
    if not thumbnail_url:
        LOG.warning("No thumbnail URL in item")
        return None
    
    filename_prefix = f"{item.get('code', 'thumb')}_main"
    return download_thumbnail(thumbnail_url, filename_prefix=filename_prefix)

async def cleanup_files(original_file: str, processed_file: str):
    from ..utils import cleanup_files as cleanup_util
    
    files_to_cleanup = [original_file]
    if processed_file and processed_file != original_file:
        files_to_cleanup.append(processed_file)
    
    cleanup_util(*files_to_cleanup)

async def cleanup_directories():
    from ..utils import cleanup_directory
    
    directories = ["./downloads", "./encode"]
    
    for directory in directories:
        cleanup_directory(directory)
