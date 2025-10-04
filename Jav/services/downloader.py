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
        LOG.info(f"🔗 Magnet link: {link[:80]}...")
        
        # Check files before download
        files_before = set()
        try:
            for root, dirs, files in os.walk(SAVE_PATH):
                for file in files:
                    files_before.add(os.path.join(root, file))
            LOG.info(f"📊 Files before download: {len(files_before)}")
        except Exception as e:
            LOG.warning(f"Could not scan directory before download: {e}")
        
        # Create torrent downloader
        try:
            torrent_downloader = TorrentDownloader(link, SAVE_PATH)
            LOG.info("✅ TorrentDownloader instance created")
        except Exception as e:
            LOG.error(f"❌ Failed to create TorrentDownloader: {e}", exc_info=True)
            return None
        
        LOG.info("⬇️ Downloading torrent (this may take a while)...")
        
        # Start download (this blocks until complete)
        try:
            # Check if torrentp has progress/status methods
            LOG.info("📊 Starting download with torrentp...")
            
            # Call start_download with timeout awareness
            download_start = time.time()
            
            # Try to call start_download - it should block until complete
            result = torrent_downloader.start_download()
            
            download_time = time.time() - start_time
            
            LOG.info(f"✅ Download complete! (took {download_time:.1f}s)")
            LOG.info(f"🔍 Download result: {result}")
            
            # If download was suspiciously fast (< 2 seconds), warn
            if download_time < 2:
                LOG.warning(f"⚠️ Download completed very quickly ({download_time:.1f}s) - this may indicate an issue")
                LOG.warning(f"   This could mean: no seeders, cached file, or torrentp error")
                LOG.warning(f"   Checking if torrentp actually downloaded anything...")
                
        except AttributeError as e:
            LOG.error(f"❌ torrentp API error: {e}", exc_info=True)
            LOG.error(f"   Available methods: {dir(torrent_downloader)}")
            return None
        except Exception as e:
            LOG.error(f"❌ Download failed: {e}", exc_info=True)
            return None
        
        # Find downloaded video file
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts']
        
        # Search for video files in download directory
        found_file = None
        found_size = 0
        
        LOG.info(f"🔍 Searching for video files in: {SAVE_PATH}")
        
        # Get all files after download
        files_after = set()
        all_video_files = []
        
        for root, dirs, files in os.walk(SAVE_PATH):
            for file in files:
                file_path = os.path.join(root, file)
                files_after.add(file_path)
                
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in video_extensions:
                    try:
                        file_size = os.path.getsize(file_path)
                        all_video_files.append((file_path, file_size))
                        LOG.info(f"  📹 Found: {file} ({file_size / (1024*1024):.1f} MB)")
                    except Exception as e:
                        LOG.warning(f"Could not get size of {file_path}: {e}")
        
        # Identify newly downloaded files
        new_files = files_after - files_before
        LOG.info(f"📊 New files downloaded: {len(new_files)}")
        
        if not all_video_files:
            LOG.error("❌ No video file found after download")
            LOG.error(f"   Total files in directory: {len(files_after)}")
            LOG.error(f"   New files: {len(new_files)}")
            
            # List what files are there
            if files_after:
                LOG.error("   Files found:")
                for f in list(files_after)[:10]:  # Show first 10
                    LOG.error(f"     - {os.path.basename(f)}")
            
            return None
        
        # Get the largest video file (most likely the actual video)
        found_file, found_size = max(all_video_files, key=lambda x: x[1])
        
        # Get torrent name and translate
        torrent_name = os.path.splitext(os.path.basename(found_file))[0]
        torrent_name = translate_to_english(torrent_name)
        
        file_size_mb = found_size / (1024 * 1024)
        LOG.info(f"📁 Selected video: {os.path.basename(found_file)}")
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
