import os
import time
import re
import unicodedata
import logging
import tempfile
from typing import Optional, Dict, Callable, Any
import libtorrent as lt # type: ignore
import requests
from ..config import SETTINGS
from ..utils import translate_to_english

LOG = logging.getLogger("AABv2")

SAVE_PATH = "./downloads"


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """Return a sanitized filename safe for most filesystems (Windows-friendly).

    - Normalize unicode to NFKD and drop non-ascii where possible.
    - Replace path-separators and characters invalid on Windows with '_'.
    - Preserve file extension and limit overall length.
    """
    if not name:
        return "unnamed"

    # Normalize unicode and try to transliterate to closest ASCII
    nfkd = unicodedata.normalize('NFKD', name)
    try:
        ascii_name = nfkd.encode('ascii', 'ignore').decode('ascii')
    except Exception:
        ascii_name = nfkd

    # Split extension (keep last dot as extension separator)
    base, ext = os.path.splitext(ascii_name)

    # Replace invalid characters with underscore
    # Disallow <>:"/\\|?* and control chars
    base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', base)
    # Collapse multiple underscores
    base = re.sub(r'_+', '_', base).strip(' _.-')

    # Fallback name
    if not base:
        base = 'file'

    # Truncate to max_length minus extension
    max_base = max_length - len(ext)
    if max_base < 10:
        max_base = 10
    if len(base) > max_base:
        base = base[:max_base]

    safe = f"{base}{ext}"
    return safe


def download_torrent(link: str, progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None) -> Optional[Dict[str, str]]:
    """
    Download a torrent using a magnet link or torrent file URL.
    Returns dict with keys: 'file' (full path) and 'name'.
    """
    try:
        os.makedirs(SAVE_PATH, exist_ok=True)

        # Setup session
        ses = lt.session()
        ses.listen_on(6881, 6891)
        try:
            ses.start_dht()
            ses.start_lsd()
            ses.start_upnp()
        except Exception as e:
            LOG.warning(f"Peer discovery services could not start: {e}")

        params = {"save_path": SAVE_PATH}
        handle = None

        if link.startswith('magnet:'):
            # Handle magnet link
            handle = lt.add_magnet_uri(ses, link, params)
            LOG.info("Using magnet link")
        else:
            # Handle torrent file URL - download it first
            LOG.info(f"Downloading torrent file from: {link}")
            try:
                response = requests.get(link, timeout=30)
                response.raise_for_status()
                torrent_data = response.content
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.torrent') as tmp_file:
                    tmp_file.write(torrent_data)
                    tmp_path = tmp_file.name
                
                # Add torrent from file
                with open(tmp_path, 'rb') as f:
                    torrent_info = lt.torrent_info(f)
                    params['ti'] = torrent_info
                    handle = ses.add_torrent(params)
                
                # Clean up temp file
                os.unlink(tmp_path)
                LOG.info("Using torrent file")
                
            except Exception as e:
                LOG.error(f"Failed to download torrent file: {e}")
                return None

        if handle is None:
            LOG.error("Failed to create torrent handle")
            return None

        LOG.info("Waiting for torrent metadata...")
        start_time = time.time()
        last_log = 0

        # Wait for metadata (only needed for magnet links)
        while not handle.has_metadata():
            elapsed = time.time() - start_time
            if elapsed - last_log >= 5:
                st = handle.status()
                LOG.info(f"Metadata wait: peers={st.num_peers}, down={st.download_rate/1000:.1f} kB/s, elapsed={int(elapsed)}s")
                if progress_cb:
                    try:
                        progress_cb({
                            "stage": "metadata",
                            "elapsed": float(int(elapsed)),
                            "peers": float(st.num_peers),
                            "down_rate_kbs": float(st.download_rate/1000.0),
                            "progress_pct": 0.0,
                        })
                    except Exception:
                        pass
                last_log = elapsed
            if elapsed >= SETTINGS.torrent_metadata_timeout_sec:
                LOG.error(f"Metadata timeout after {int(elapsed)}s")
                ses.remove_torrent(handle)
                return None
            time.sleep(1)

        torrent_name = handle.name()
        torrent_name = translate_to_english(torrent_name)
        LOG.info(f"Starting download: {torrent_name}")

        # Get torrent info and find the largest video file
        torrent_info = handle.torrent_file()
        files = torrent_info.files()
        
        # Find largest video file
        video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
        largest_file = None
        largest_size = 0
        largest_idx = 0
        
        for i in range(files.num_files()):
            file_path = files.file_path(i)
            file_size = files.file_size(i)
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext in video_extensions and file_size > largest_size:
                largest_file = file_path
                largest_size = file_size
                largest_idx = i
        
        if largest_file:
            LOG.info(f"Largest video file: {largest_file} ({largest_size / (1024*1024):.2f} MB)")
        else:
            LOG.warning(f"No video file found, using torrent name: {torrent_name}")
            largest_file = torrent_name

        last_progress = 0.0
        stall_start: Optional[float] = None

        # Download loop
        while handle.status().state != lt.torrent_status.seeding:
            s = handle.status()
            prog = s.progress
            down_rate = s.download_rate
            up_rate = s.upload_rate

            LOG.info(f"{prog*100:.2f}% down:{down_rate/1000:.1f} kB/s up:{up_rate/1000:.1f} kB/s peers:{s.num_peers}")
            if progress_cb:
                try:
                    progress_cb({
                        "stage": "downloading",
                        "elapsed": float(int(time.time() - start_time)),
                        "peers": float(s.num_peers),
                        "down_rate_kbs": float(down_rate/1000.0),
                        "up_rate_kbs": float(up_rate/1000.0),
                        "progress_pct": float(prog * 100.0),
                    })
                except Exception:
                    pass

            # Stall detection
            if prog > last_progress:
                last_progress = prog
                stall_start = None
            else:
                if down_rate < 1024:  # <1KB/s
                    if stall_start is None:
                        stall_start = time.time()
                    elif time.time() - stall_start >= SETTINGS.torrent_stall_timeout_sec:
                        LOG.error("Download stalled; aborting")
                        ses.remove_torrent(handle)
                        return None
                else:
                    stall_start = None

            time.sleep(SETTINGS.download_update_interval_sec)

        # Sanitize the torrent_name to produce a safe filename on disk
        # Use the actual video file name, not the torrent metadata name
        safe_name = sanitize_filename(largest_file)
        full_path = os.path.join(SAVE_PATH, largest_file)

        # If the name on disk differs from sanitized, attempt to rename/move
        target_path = os.path.join(SAVE_PATH, safe_name)
        try:
            if os.path.exists(full_path) and full_path != target_path:
                # Avoid clobbering an existing path - add index suffix when needed
                if os.path.exists(target_path):
                    base, ext = os.path.splitext(safe_name)
                    idx = 1
                    while True:
                        candidate = f"{base}_{idx}{ext}"
                        candidate_path = os.path.join(SAVE_PATH, candidate)
                        if not os.path.exists(candidate_path):
                            target_path = candidate_path
                            break
                        idx += 1

                os.rename(full_path, target_path)
                full_path = target_path

        except Exception as e:
            LOG.warning(f"Failed to sanitize/rename downloaded path {full_path} -> {target_path}: {e}")

        LOG.info(f"Download completed: {full_path}")
        if progress_cb:
            try:
                progress_cb({
                    "stage": "completed",
                    "elapsed": float(int(time.time() - start_time)),
                    "peers": 0.0,
                    "down_rate_kbs": 0.0,
                    "up_rate_kbs": 0.0,
                    "progress_pct": 100.0,
                })
            except Exception:
                pass
        
        result = {"file": full_path, "name": torrent_name}
        LOG.info(f"Returning download result: {result}")
        return result

    except Exception as e:
        LOG.exception(f"download_torrent error: {e}")
        return None
