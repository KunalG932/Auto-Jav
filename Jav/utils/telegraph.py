
import os
import logging
import subprocess
import tempfile
import requests
from typing import Optional, List
from html_telegraph_poster import TelegraphPoster

LOG = logging.getLogger("Jav")

def upload_image_to_host(image_path: str) -> Optional[str]:
    try:
        with open(image_path, 'rb') as img_file:
            files = {'file': img_file}
            response = requests.post('https://envs.sh', files=files, timeout=30)
            response.raise_for_status()
            
            image_url = response.text.strip()
            
            if image_url and image_url.startswith('http'):
                LOG.debug(f"Uploaded image to: {image_url}")
                return image_url
            else:
                LOG.warning(f"Invalid response from image host: {response.text}")
                return None
                
    except Exception as e:
        LOG.error(f"Failed to upload image to host: {e}")
        return None

def extract_video_screenshots(video_path: str, num_screenshots: int = 6) -> List[str]:
    screenshots = []
    
    if not os.path.exists(video_path):
        LOG.error(f"Video file not found: {video_path}")
        return screenshots
    
    try:
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
        
        temp_dir = tempfile.mkdtemp(prefix="video_preview_")
        
        start_time = duration * 0.1
        end_time = duration * 0.9
        interval = (end_time - start_time) / (num_screenshots + 1)
        
        for i in range(num_screenshots):
            timestamp = start_time + (i + 1) * interval
            screenshot_path = os.path.join(temp_dir, f"screenshot_{i+1:02d}.jpg")
            
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
    try:
        LOG.info(f"Creating Telegraph preview for: {title}")
        
        screenshots = extract_video_screenshots(video_path, num_screenshots)
        
        if not screenshots:
            LOG.warning("No screenshots extracted, cannot create Telegraph page")
            return None
        
        poster = TelegraphPoster(use_api=True)
        poster.create_api_token('JAV Bot', 'JAV Preview', 'https://t.me/AutoMangaCampus')
        
        html_parts = []
        
        if description:
            html_parts.append(f"<p><strong>{description}</strong></p>")
        
        html_parts.append("<p>📸 Video Preview Screenshots:</p>")
        
        uploaded_count = 0
        for idx, screenshot_path in enumerate(screenshots, 1):
            try:
                LOG.info(f"Uploading screenshot {idx}/{len(screenshots)} to image host...")
                
                image_url = upload_image_to_host(screenshot_path)
                
                if image_url:
                    img_tag = f'<img src="{image_url}"/>'
                    html_parts.append(img_tag)
                    uploaded_count += 1
                    LOG.info(f"✅ Added screenshot {idx}/{len(screenshots)} with URL: {image_url}")
                else:
                    LOG.warning(f"Failed to upload screenshot {idx}, skipping")
                
            except Exception as e:
                LOG.warning(f"Failed to process screenshot {idx}: {e}")
                continue
        
        if uploaded_count == 0:
            LOG.error("No images uploaded successfully, cannot create Telegraph page")
            return None
        
        LOG.info(f"Successfully uploaded {uploaded_count}/{len(screenshots)} screenshots")
        
        html_content = "\n".join(html_parts)
        
        try:
            LOG.debug(f"Posting to Telegraph with content length: {len(html_content)}")
            
            telegraph_response = poster.post(
                title=title[:256],
                author='JAV Bot',
                text=html_content
            )
            
            LOG.debug(f"Telegraph response type: {type(telegraph_response)}, value: {telegraph_response}")
            
            telegraph_url = None
            if isinstance(telegraph_response, str):
                telegraph_url = telegraph_response
                LOG.debug("Got string URL directly")
            elif isinstance(telegraph_response, dict):
                if 'result' in telegraph_response and isinstance(telegraph_response['result'], dict):
                    result = telegraph_response['result']
                    telegraph_url = result.get('url') or result.get('path')
                else:
                    telegraph_url = (
                        telegraph_response.get('url') or 
                        telegraph_response.get('path') or
                        telegraph_response.get('link')
                    )
                    
                if telegraph_url and not telegraph_url.startswith('http'):
                    telegraph_url = f"https://telegra.ph/{telegraph_url.lstrip('/')}"
                    
                LOG.debug(f"Extracted URL from dict: {telegraph_url}")
            
            if telegraph_url and isinstance(telegraph_url, str):
                LOG.info(f"✅ Telegraph preview created: {telegraph_url}")
            else:
                LOG.error(f"Could not extract URL from Telegraph response. Type: {type(telegraph_response)}, Keys: {telegraph_response.keys() if isinstance(telegraph_response, dict) else 'N/A'}")
                return None
            
            for screenshot in screenshots:
                try:
                    if os.path.exists(screenshot):
                        os.remove(screenshot)
                        
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
