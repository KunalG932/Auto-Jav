"""
Video encoding module using FFmpeg.

Provides functions to encode videos with quality constraints (max 720p resolution).
All videos are re-encoded to ensure consistent quality and reduce file size.
"""
import os
import subprocess
import logging
from typing import Optional, Dict, Any
from ..config import SETTINGS

LOG = logging.getLogger("AABv2")

def get_video_info(file_path: str) -> Dict[str, Any]:
    """Get video information using ffprobe."""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration,bit_rate',
            '-of', 'json',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            if 'streams' in data and len(data['streams']) > 0:
                stream = data['streams'][0]
                return {
                    'width': int(stream.get('width', 0)),
                    'height': int(stream.get('height', 0)),
                    'duration': float(stream.get('duration', 0)),
                    'bit_rate': int(stream.get('bit_rate', 0))
                }
    except Exception as e:
        LOG.warning(f"Failed to get video info: {e}")
    return {}

def encode_file(input_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """
    Encode video file with 720p max resolution and quality settings.
    
    Args:
        input_path: Path to input video file
        output_path: Optional output path (default: adds _encoded suffix)
        
    Returns:
        Path to encoded file, or None on failure
    """
    if not os.path.exists(input_path):
        LOG.error(f"Input file does not exist: {input_path}")
        return None
    
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_encoded.mp4"
    
    try:
        # Get video info to check current resolution
        info = get_video_info(input_path)
        width = info.get('width', 0)
        height = info.get('height', 0)
        
        LOG.info(f"Encoding video: {input_path} (current: {width}x{height})")
        LOG.info(f"Target: max 720p, CRF={SETTINGS.encode_crf}")
        
        # Build ffmpeg command with 720p limit
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-i', input_path,
            '-c:v', SETTINGS.encode_video_codec,  # Video codec (h264 or h265)
            '-crf', str(SETTINGS.encode_crf),  # Quality (lower = better, 23 is default)
            '-preset', SETTINGS.encode_preset,  # Encoding speed/quality tradeoff
            '-vf', f'scale=\'min({SETTINGS.max_resolution_width},iw)\':-2',  # Scale to max 720p width, maintain aspect ratio
            '-c:a', SETTINGS.encode_audio_codec,  # Audio codec
            '-b:a', SETTINGS.encode_audio_bitrate,  # Audio bitrate
            '-movflags', '+faststart',  # Enable streaming
            '-max_muxing_queue_size', '1024',  # Prevent muxing issues
            output_path
        ]
        
        LOG.info(f"Running ffmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode == 0 and os.path.exists(output_path):
            input_size = os.path.getsize(input_path) / (1024 * 1024)
            output_size = os.path.getsize(output_path) / (1024 * 1024)
            reduction = ((input_size - output_size) / input_size * 100) if input_size > 0 else 0
            
            LOG.info(f"✅ Encoding successful: {output_path}")
            LOG.info(f"Size: {input_size:.1f}MB → {output_size:.1f}MB ({reduction:+.1f}%)")
            return output_path
        else:
            LOG.error(f"FFmpeg encoding failed with code {result.returncode}")
            LOG.error(f"stderr: {result.stderr[:500]}")
            return None
            
    except subprocess.TimeoutExpired:
        LOG.error("FFmpeg encoding timeout (>1 hour)")
        return None
    except FileNotFoundError:
        LOG.error("FFmpeg not found - please install ffmpeg")
        return None
    except Exception as e:
        LOG.error(f"Encoding error: {e}", exc_info=True)
        return None

def encode_with_crf(input_path: str, crf: int = 23, output_path: Optional[str] = None) -> Optional[str]:
    """
    Encode video with specific CRF value (quality setting).
    
    Args:
        input_path: Path to input video file
        crf: Constant Rate Factor (0-51, lower = better quality, 23 = default)
        output_path: Optional output path
        
    Returns:
        Path to encoded file, or None on failure
    """
    # Temporarily override CRF setting
    original_crf = SETTINGS.encode_crf
    object.__setattr__(SETTINGS, 'encode_crf', crf)
    
    try:
        result = encode_file(input_path, output_path)
        return result
    finally:
        # Restore original CRF
        object.__setattr__(SETTINGS, 'encode_crf', original_crf)