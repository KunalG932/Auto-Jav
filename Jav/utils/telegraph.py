"""
Telegraph utility module for creating video preview pages with screenshots.
"""

import os
import logging
import subprocess
import tempfile
from typing import Optional, List
from html_telegraph_poster import TelegraphPoster

LOG = logging.getLogger("Jav")


def extract_video_screenshots(video_path: str, num_screenshots: int = 6) -> List[str]:
    """
    Extract screenshots from video at regular intervals.
    
    Args:
        video_path: Path to the video file
        num_screenshots: Number of screenshots to extract (default: 6)
        
    Returns:
        List of paths to extracted screenshot files
    """
    screenshots = []
    
    if not os.path.exists(video_path):
        LOG.error(f"Video file not found: {video_path}")
        return screenshots
    
    try:
        # Get video duration
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0 or not result.stdout.strip():
            LOG.error(f"Could not get video duration for: {video_path}")
            return screenshots
        
        duration = float(result.stdout.strip())
        
        if duration <= 0:
            LOG.error(f"Invalid video duration: {duration}")
            return screenshots
        
        # Create temp directory for screenshots
        temp_dir = tempfile.mkdtemp(prefix="video_preview_")
        
        # Calculate interval between screenshots
        # Skip first and last 10% to avoid intros/credits
        start_time = duration * 0.1
        end_time = duration * 0.9
        interval = (end_time - start_time) / (num_screenshots + 1)
        
        for i in range(num_screenshots):
            timestamp = start_time + (i + 1) * interval
            screenshot_path = os.path.join(temp_dir, f"screenshot_{i+1:02d}.jpg")
            
            # Extract screenshot using ffmpeg
            cmd = [
                'ffmpeg',
                '-ss', str(timestamp),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                '-y',
                screenshot_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(screenshot_path):
                screenshots.append(screenshot_path)
                LOG.info(f"Extracted screenshot {i+1}/{num_screenshots} at {timestamp:.1f}s")
            else:
                LOG.warning(f"Failed to extract screenshot at {timestamp:.1f}s")
        
        LOG.info(f"Successfully extracted {len(screenshots)}/{num_screenshots} screenshots")
        
    except subprocess.TimeoutExpired:
        LOG.error("Screenshot extraction timed out")
    except Exception as e:
        LOG.error(f"Error extracting screenshots: {e}", exc_info=True)
    
    return screenshots


def create_telegraph_preview(
    video_path: str,
    title: str,
    description: Optional[str] = None,
    num_screenshots: int = 6
) -> Optional[str]:
    """
    Create a Telegraph page with video preview screenshots.
    
    Args:
        video_path: Path to the video file
        title: Title for the Telegraph page
        description: Optional description text
        num_screenshots: Number of screenshots to include (default: 6)
        
    Returns:
        URL of the created Telegraph page, or None if failed
    """
    try:
        LOG.info(f"Creating Telegraph preview for: {title}")
        
        # Extract screenshots
        screenshots = extract_video_screenshots(video_path, num_screenshots)
        
        if not screenshots:
            LOG.warning("No screenshots extracted, cannot create Telegraph page")
            return None
        
        # Create Telegraph poster
        poster = TelegraphPoster(use_api=True)
        poster.create_api_token('JAV Bot', 'JAV Preview', 'https://t.me/AutoMangaCampus')
        
        # Build HTML content
        html_parts = []
        
        # Add description if provided
        if description:
            html_parts.append(f"<p><strong>{description}</strong></p>")
        
        html_parts.append("<p>Video Preview Screenshots:</p>")
        
        # Upload and add screenshots
        for idx, screenshot_path in enumerate(screenshots, 1):
            try:
                # Upload image to Telegraph
                with open(screenshot_path, 'rb') as img_file:
                    img_data = img_file.read()
                
                # TelegraphPoster handles image upload
                img_tag = f'<img src="{screenshot_path}"/>'
                html_parts.append(img_tag)
                
                LOG.info(f"Added screenshot {idx}/{len(screenshots)} to Telegraph page")
                
            except Exception as e:
                LOG.warning(f"Failed to add screenshot {idx}: {e}")
                continue
        
        if len(html_parts) <= 2:  # Only has description and header, no images
            LOG.error("No images added to Telegraph page")
            return None
        
        # Create the page
        html_content = "\n".join(html_parts)
        
        try:
            telegraph_url = poster.post(
                title=title[:256],  # Telegraph title limit
                author='JAV Bot',
                text=html_content
            )
            
            # Ensure we return a string URL
            if isinstance(telegraph_url, str):
                LOG.info(f"✅ Telegraph preview created: {telegraph_url}")
            else:
                LOG.warning(f"Unexpected Telegraph response type: {type(telegraph_url)}")
                return None
            
            # Cleanup screenshots
            for screenshot in screenshots:
                try:
                    if os.path.exists(screenshot):
                        os.remove(screenshot)
                        
                    # Also try to remove the temp directory
                    temp_dir = os.path.dirname(screenshot)
                    if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                        os.rmdir(temp_dir)
                except Exception as e:
                    LOG.debug(f"Failed to cleanup screenshot: {e}")
            
            return telegraph_url
            
        except Exception as e:
            LOG.error(f"Failed to post to Telegraph: {e}", exc_info=True)
            return None
            
    except Exception as e:
        LOG.error(f"Error creating Telegraph preview: {e}", exc_info=True)
        return None


async def create_telegraph_preview_async(
    video_path: str,
    title: str,
    description: Optional[str] = None,
    num_screenshots: int = 6
) -> Optional[str]:
    """
    Async wrapper for creating Telegraph preview.
    
    Args:
        video_path: Path to the video file
        title: Title for the Telegraph page
        description: Optional description text
        num_screenshots: Number of screenshots to include (default: 6)
        
    Returns:
        URL of the created Telegraph page, or None if failed
    """
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        create_telegraph_preview,
        video_path,
        title,
        description,
        num_screenshots
    )
