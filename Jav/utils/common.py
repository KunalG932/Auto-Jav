"""
Common utilities for the JAV Bot.

This module contains shared utility functions to eliminate code duplication:
- FloodWait error handling
- Thumbnail download logic
- File cleanup operations
"""

import os
import asyncio
import logging
import requests
from typing import Optional, Callable, Any
from pyrogram import errors

LOG = logging.getLogger("Jav")


async def handle_flood_wait(
    func: Callable,
    *args,
    max_retries: int = 3,
    operation_name: str = "operation",
    **kwargs
) -> Optional[Any]:
    """
    Handle Telegram FloodWait errors with automatic retry.
    
    Args:
        func: Async function to execute
        *args: Positional arguments for the function
        max_retries: Maximum number of retry attempts (default: 3)
        operation_name: Description of the operation for logging
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result from the function, or None if all retries failed
        
    Example:
        result = await handle_flood_wait(
            bot.send_message,
            chat_id=123,
            text="Hello",
            operation_name="send message"
        )
    """
    for attempt in range(1, max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except errors.FloodWait as fw:
            if attempt == max_retries:
                LOG.error(f"FloodWait: Max retries ({max_retries}) reached for {operation_name}")
                raise
            
            wait_time = int(fw.value) if isinstance(fw.value, (int, float)) else 60
            LOG.warning(
                f"FloodWait during {operation_name}: "
                f"sleeping for {wait_time}s (attempt {attempt}/{max_retries})"
            )
            await asyncio.sleep(float(wait_time))
            continue
        except Exception as e:
            LOG.error(f"Error during {operation_name}: {e}")
            raise
    
    return None


def download_thumbnail(
    thumbnail_url: str,
    output_dir: str = "./thumbnails",
    filename_prefix: str = "thumb",
    timeout: int = 15
) -> Optional[str]:
    """
    Download thumbnail from URL and return local file path.
    
    Args:
        thumbnail_url: URL of the thumbnail image
        output_dir: Directory to save the thumbnail (default: ./thumbnails)
        filename_prefix: Prefix for the saved filename (default: thumb)
        timeout: Request timeout in seconds (default: 15)
        
    Returns:
        Path to downloaded thumbnail file, or None if download failed
        
    Example:
        thumb_path = download_thumbnail(
            "https://example.com/image.jpg",
            filename_prefix="video_123"
        )
    """
    if not thumbnail_url or not isinstance(thumbnail_url, str):
        LOG.warning("Invalid thumbnail URL provided")
        return None
    
    try:
        LOG.info(f"Downloading thumbnail from: {thumbnail_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(thumbnail_url, timeout=timeout, headers=headers)
        response.raise_for_status()
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Determine file extension from URL
        ext = '.jpg'
        if '.' in thumbnail_url:
            url_ext = thumbnail_url.split('.')[-1].split('?')[0].lower()
            if url_ext in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                ext = f'.{url_ext}'
        
        # Generate unique filename
        thumbnail_path = os.path.join(output_dir, f"{filename_prefix}{ext}")
        
        # Save thumbnail
        with open(thumbnail_path, 'wb') as f:
            f.write(response.content)
        
        LOG.info(f"✅ Thumbnail downloaded successfully: {thumbnail_path}")
        return thumbnail_path
        
    except requests.exceptions.Timeout:
        LOG.warning(f"Thumbnail download timed out after {timeout}s: {thumbnail_url}")
        return None
    except requests.exceptions.HTTPError as e:
        LOG.warning(f"HTTP error downloading thumbnail: {e.response.status_code if hasattr(e, 'response') else e}")
        return None
    except requests.exceptions.RequestException as e:
        LOG.warning(f"Network error downloading thumbnail: {e}")
        return None
    except Exception as e:
        LOG.error(f"Unexpected error downloading thumbnail: {e}", exc_info=True)
        return None


def cleanup_file(file_path: str, log_success: bool = True) -> bool:
    """
    Delete a single file safely with error handling.
    
    Args:
        file_path: Path to the file to delete
        log_success: Whether to log successful deletion (default: True)
        
    Returns:
        True if file was deleted or doesn't exist, False on error
    """
    if not file_path:
        return True
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            if log_success:
                LOG.info(f"🗑️ Deleted: {file_path}")
            return True
        return True
    except Exception as e:
        LOG.warning(f"Failed to delete {file_path}: {e}")
        return False


def cleanup_files(*file_paths: str, log_success: bool = True) -> int:
    """
    Delete multiple files safely with error handling.
    
    Args:
        *file_paths: Variable number of file paths to delete
        log_success: Whether to log successful deletions (default: True)
        
    Returns:
        Number of files successfully deleted
        
    Example:
        deleted_count = cleanup_files(
            "/path/to/file1.mp4",
            "/path/to/file2.jpg",
            "/path/to/file3.txt"
        )
    """
    deleted_count = 0
    for file_path in file_paths:
        if cleanup_file(file_path, log_success):
            deleted_count += 1
    return deleted_count


def cleanup_directory(
    directory: str,
    remove_directory: bool = False,
    file_extensions: Optional[list] = None
) -> int:
    """
    Clean up all files in a directory, optionally removing the directory itself.
    
    Args:
        directory: Path to the directory to clean
        remove_directory: Whether to remove the directory after cleaning (default: False)
        file_extensions: List of extensions to delete (e.g., ['.mp4', '.mkv']). 
                        If None, all files are deleted.
        
    Returns:
        Number of files successfully deleted
        
    Example:
        # Delete only video files
        cleanup_directory("./downloads", file_extensions=['.mp4', '.mkv', '.avi'])
        
        # Delete all files and the directory
        cleanup_directory("./temp", remove_directory=True)
    """
    if not os.path.exists(directory):
        return 0
    
    deleted_count = 0
    
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            # Skip if not a file
            if not os.path.isfile(file_path):
                # Recursively handle subdirectories
                if os.path.isdir(file_path):
                    import shutil
                    try:
                        shutil.rmtree(file_path)
                        LOG.info(f"🗑️ Deleted directory: {file_path}")
                    except Exception as e:
                        LOG.warning(f"Failed to delete directory {file_path}: {e}")
                continue
            
            # Check file extension if filter is provided
            if file_extensions:
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext not in file_extensions:
                    continue
            
            # Delete the file
            if cleanup_file(file_path, log_success=False):
                deleted_count += 1
        
        if deleted_count > 0:
            LOG.info(f"✅ Cleaned up {deleted_count} files from {directory}")
        
        # Remove directory if requested and empty
        if remove_directory and os.path.exists(directory):
            try:
                if not os.listdir(directory):  # Check if empty
                    os.rmdir(directory)
                    LOG.info(f"🗑️ Removed empty directory: {directory}")
            except Exception as e:
                LOG.warning(f"Failed to remove directory {directory}: {e}")
        
    except Exception as e:
        LOG.error(f"Error cleaning directory {directory}: {e}", exc_info=True)
    
    return deleted_count


def get_fallback_thumbnail(settings) -> Optional[str]:
    """
    Get the fallback/default thumbnail path from settings.
    
    Args:
        settings: Settings object containing thumbnail_path
        
    Returns:
        Absolute path to fallback thumbnail, or None if not found
    """
    try:
        thumbnail_path = getattr(settings, 'thumbnail_path', None)
        if not thumbnail_path:
            return None
        
        abs_path = os.path.abspath(thumbnail_path)
        if os.path.exists(abs_path):
            LOG.debug(f"Using fallback thumbnail: {abs_path}")
            return abs_path
        else:
            LOG.warning(f"Fallback thumbnail not found: {abs_path}")
            return None
    except Exception as e:
        LOG.warning(f"Error getting fallback thumbnail: {e}")
        return None


def download_thumbnail_with_fallback(
    thumbnail_url: Optional[str],
    settings,
    filename_prefix: str = "thumb",
    timeout: int = 15
) -> Optional[str]:
    """
    Download thumbnail from URL with automatic fallback to default thumbnail.
    
    Args:
        thumbnail_url: URL of the thumbnail (can be None)
        settings: Settings object for fallback thumbnail
        filename_prefix: Prefix for downloaded filename
        timeout: Request timeout in seconds
        
    Returns:
        Path to thumbnail (downloaded or fallback), or None if both fail
    """
    # Try to download from URL first
    if thumbnail_url:
        downloaded_thumb = download_thumbnail(
            thumbnail_url,
            filename_prefix=filename_prefix,
            timeout=timeout
        )
        if downloaded_thumb:
            return downloaded_thumb
    
    # Fallback to default thumbnail
    LOG.info("Using fallback thumbnail")
    return get_fallback_thumbnail(settings)


# Export all utility functions
__all__ = [
    'handle_flood_wait',
    'download_thumbnail',
    'cleanup_file',
    'cleanup_files',
    'cleanup_directory',
    'get_fallback_thumbnail',
    'download_thumbnail_with_fallback',
]
