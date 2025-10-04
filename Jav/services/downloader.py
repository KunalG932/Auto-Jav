import os
import re
import unicodedata
import logging
import asyncio
import time
from typing import Optional, Dict, Callable, Any
from torrentp import TorrentDownloader

from ..config import SETTINGS
from ..utils import translate_to_english

LOG = logging.getLogger("Jav")

SAVE_PATH = os.path.abspath("./downloads")

def sanitize_filename(name: str, max_length: int = 200) -> str:
    """
    Sanitize filename to remove invalid characters and limit length.
    """
    if not name:
        return "unnamed"

    nfkd = unicodedata.normalize('NFKD', name)
    try:
        ascii_name = nfkd.encode('ascii', 'ignore').decode('ascii')
    except Exception:
        ascii_name = nfkd

    base, ext = os.path.splitext(ascii_name)

    base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', base)
    base = re.sub(r'_+', '_', base).strip(' _.-')

    if not base:
        base = 'file'

    max_base = max_length - len(ext)
    if max_base < 10:
        max_base = 10
    if len(base) > max_base:
        base = base[:max_base]

    safe = f"{base}{ext}"
    return safe


def download_torrent(
    link: str,
    progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Optional[Dict[str, str]]:
    """
    Download torrent using torrentp (fast and easy).
    
    Args:
        link: Magnet link or torrent URL
        progress_cb: Optional progress callback
        
    Returns:
        Dict with 'file' and 'name' keys, or None if failed
    """
    start_time = time.time()
    
    try:
        os.makedirs(SAVE_PATH, exist_ok=True)
        
        LOG.info(f"🚀 Starting torrent download with torrentp")
        LOG.info(f"📍 Download path: {SAVE_PATH}")
        
        # Create torrent downloader
        torrent_downloader = TorrentDownloader(link, SAVE_PATH)
        
        LOG.info("⬇️ Downloading torrent (this may take a while)...")
        
        # Start download (this blocks until complete)
        torrent_downloader.start_download()
        
        LOG.info("✅ Download complete!")
        
        # Find downloaded video file
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
        
        # Search for video files in download directory
        found_file = None
        found_size = 0
        
        LOG.info(f"🔍 Searching for video files in: {SAVE_PATH}")
        for root, dirs, files in os.walk(SAVE_PATH):
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in video_extensions:
                    file_path = os.path.join(root, file)
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_size > found_size:
                            found_file = file_path
                            found_size = file_size
                    except Exception as e:
                        LOG.warning(f"Could not get size of {file_path}: {e}")
        
        if not found_file:
            LOG.error("❌ No video file found after download")
            return None
        
        # Get torrent name and translate
        torrent_name = os.path.splitext(os.path.basename(found_file))[0]
        torrent_name = translate_to_english(torrent_name)
        
        file_size_mb = found_size / (1024 * 1024)
        LOG.info(f"📁 Found video: {os.path.basename(found_file)}")
        LOG.info(f"📏 Size: {file_size_mb:.1f} MB")
        LOG.info(f"🏷️ Name: {torrent_name}")
        
        # Call completion callback
        if progress_cb:
            try:
                elapsed = time.time() - start_time
                progress_cb({
                    "stage": "completed",
                    "progress_pct": 100.0,
                    "peers": 0.0,
                    "down_rate_kbs": 0.0,
                    "up_rate_kbs": 0.0,
                    "elapsed": float(elapsed)
                })
            except Exception:
                pass
        
        return {
            'file': found_file,
            'name': torrent_name
        }
        
    except KeyboardInterrupt:
        LOG.info("⚠️ Download cancelled by user")
        return None
        
    except Exception as e:
        LOG.error(f"❌ Download error: {e}", exc_info=True)
        return None
