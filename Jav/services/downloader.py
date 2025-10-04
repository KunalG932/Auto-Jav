import os
import re
import unicodedata
import logging
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
    progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
    timeout: int = 3600  # 1 hour default timeout
) -> Optional[Dict[str, str]]:
    """
    Download torrent using torrentp with proper monitoring.
    
    Args:
        link: Magnet link or torrent URL
        progress_cb: Optional progress callback
        timeout: Maximum time to wait for download (seconds)
        
    Returns:
        Dict with 'file' and 'name' keys, or None if failed
    """
    start_time = time.time()
    
    try:
        os.makedirs(SAVE_PATH, exist_ok=True)
        
        LOG.info(f"🚀 Starting torrent download with torrentp")
        LOG.info(f"📍 Download path: {SAVE_PATH}")
        LOG.info(f"🔗 Magnet link: {link[:80]}...")
        
        # Get files before download
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
            
            # Log available methods/attributes
            available_attrs = [attr for attr in dir(torrent_downloader) if not attr.startswith('_')]
            LOG.info(f"📋 Available methods: {', '.join(available_attrs)}")
            
        except Exception as e:
            LOG.error(f"❌ Failed to create TorrentDownloader: {e}", exc_info=True)
            return None
        
        LOG.info("⬇️ Starting download (waiting for peers and data)...")
        
        # Monitor download with timeout
        download_started = False
        last_file_count = len(files_before)
        check_interval = 5  # Check every 5 seconds
        last_check = start_time
        
        try:
            # Start the download in a way that we can monitor it
            # torrentp should have a method like start_download() that blocks
            
            # Check if we can access torrent info first
            if hasattr(torrent_downloader, 'torrent_file'):
                LOG.info(f"📦 Torrent info available: {torrent_downloader.torrent_file}")
            
            # Try different approaches based on torrentp version
            if hasattr(torrent_downloader, 'start_download'):
                LOG.info("📊 Calling start_download()...")
                
                # Call start_download - check if it's actually downloading
                # by monitoring file changes
                result = torrent_downloader.start_download()
                
                # Check immediately if anything downloaded
                time.sleep(2)  # Give it a moment to start
                
                # Scan for new files
                files_after = set()
                for root, dirs, files in os.walk(SAVE_PATH):
                    for file in files:
                        files_after.add(os.path.join(root, file))
                
                new_files = files_after - files_before
                
                if len(new_files) == 0:
                    LOG.error("❌ No new files detected after download call!")
                    LOG.error("   This suggests:")
                    LOG.error("   1. No seeders available for this torrent")
                    LOG.error("   2. torrentp failed silently")
                    LOG.error("   3. Invalid magnet link")
                    LOG.error(f"   4. Download path issue: {SAVE_PATH}")
                    
                    # Try to get more info from torrent_downloader
                    if hasattr(torrent_downloader, 'torrent_handle'):
                        try:
                            status = torrent_downloader.torrent_handle.status()
                            LOG.error(f"   Torrent status: {status}")
                        except Exception as e:
                            LOG.error(f"   Could not get torrent status: {e}")
                    
                    return None
                else:
                    LOG.info(f"✅ {len(new_files)} new file(s) detected")
                    download_started = True
                
            else:
                LOG.error("❌ TorrentDownloader has no start_download method!")
                LOG.error(f"   Available methods: {available_attrs}")
                return None
            
            download_time = time.time() - start_time
            LOG.info(f"✅ Download call completed in {download_time:.1f}s")
            
            # If download was too fast, it probably failed
            if download_time < 3 and not download_started:
                LOG.error(f"⚠️ Download suspiciously fast ({download_time:.1f}s)")
                LOG.error("   This usually means no seeders or connection failed")
                return None
                
        except Exception as e:
            LOG.error(f"❌ Download failed: {e}", exc_info=True)
            return None
        
        # Find downloaded video file
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts']
        
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
            if new_files:
                LOG.error("   New files (non-video):")
                for f in list(new_files)[:20]:
                    LOG.error(f"     - {os.path.basename(f)}")
            
            return None
        
        # Get the largest video file (most likely the actual video)
        found_file, found_size = max(all_video_files, key=lambda x: x[1])
        
        # Verify it's a new file
        if found_file not in new_files:
            LOG.warning(f"⚠️ Found video file was not newly downloaded: {os.path.basename(found_file)}")
            LOG.warning("   It may be from a previous download. Checking if it's the largest new file...")
            
            # Filter to only new video files
            new_video_files = [(f, s) for f, s in all_video_files if f in new_files]
            
            if not new_video_files:
                LOG.error("❌ No new video files found")
                return None
            
            found_file, found_size = max(new_video_files, key=lambda x: x[1])
            LOG.info(f"✅ Using largest new video file: {os.path.basename(found_file)}")
        
        # Get torrent name and translate
        torrent_name = os.path.splitext(os.path.basename(found_file))[0]
        torrent_name = translate_to_english(torrent_name)
        
        file_size_mb = found_size / (1024 * 1024)
        LOG.info(f"📁 Selected video: {os.path.basename(found_file)}")
        LOG.info(f"📏 Size: {file_size_mb:.1f} MB")
        LOG.info(f"🏷️ Name: {torrent_name}")
        
        # Verify file is complete (not still downloading)
        if file_size_mb < 1.0:
            LOG.warning(f"⚠️ Video file is very small ({file_size_mb:.2f} MB)")
            LOG.warning("   This might be incomplete or a sample file")
        
        # Call completion callback
        if progress_cb:
            try:
                elapsed = time.time() - start_time
                progress_cb({
                    "stage": "completed",
                    "progress_pct": 100.0,
                    "peers": 0,
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