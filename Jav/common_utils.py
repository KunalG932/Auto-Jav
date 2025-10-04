"""
Common utility functions used across the codebase.
Centralizes duplicate code for thumbnail downloads, HTTP headers, etc.
"""
import os
import logging
import requests
from typing import Optional, Dict, Any

LOG = logging.getLogger("Jav")

# Standard User-Agent for HTTP requests
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

def get_http_headers() -> Dict[str, str]:
    """
    Returns standard HTTP headers for requests.
    """
    return {'User-Agent': USER_AGENT}


def download_thumbnail(thumbnail_url: str, code: str, suffix: str = "") -> Optional[str]:
    """
    Download a thumbnail from URL and save it locally.
    
    Args:
        thumbnail_url: URL of the thumbnail to download
        code: Video code (e.g., 'JUY-925') for filename
        suffix: Optional suffix for filename (e.g., 'main', 'upload')
    
    Returns:
        Local file path if successful, None if failed
    """
    if not thumbnail_url:
        LOG.warning("No thumbnail URL provided")
        return None
    
    try:
        LOG.info(f"📥 Downloading thumbnail from: {thumbnail_url}")
        
        response = requests.get(thumbnail_url, timeout=15, headers=get_http_headers())
        response.raise_for_status()
        
        thumb_dir = "./thumbnails"
        os.makedirs(thumb_dir, exist_ok=True)
        
        # Determine file extension
        ext = '.jpg'
        if '.' in thumbnail_url:
            url_ext = thumbnail_url.split('.')[-1].split('?')[0].lower()
            if url_ext in ['jpg', 'jpeg', 'png', 'webp']:
                ext = f'.{url_ext}'
        
        # Create filename
        suffix_part = f"_{suffix}" if suffix else ""
        thumb_path = os.path.join(thumb_dir, f"{code}{suffix_part}{ext}")
        
        # Save thumbnail
        with open(thumb_path, 'wb') as f:
            f.write(response.content)
        
        LOG.info(f"✅ Thumbnail saved: {thumb_path}")
        return thumb_path
        
    except Exception as e:
        LOG.warning(f"❌ Failed to download thumbnail: {e}")
        return None
