import logging
import requests
from typing import Optional
from ..config import SETTINGS

LOG = logging.getLogger("AABv2")

def ping_api() -> bool:
    """
    Ping the API to wake it up if it's cold starting (e.g., Render free tier).
    Returns True if API is reachable, False otherwise.
    """
    try:
        LOG.info("🏓 Pinging API to check availability...")
        response = requests.get(
            SETTINGS.api_endpoint,
            timeout=150,
            headers={'User-Agent': 'Auto-JAV-Bot/2.0'}
        )
        
        if response.status_code == 200:
            LOG.info("✅ API is alive and responding!")
            return True
        else:
            LOG.warning(f"⚠️ API returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        LOG.warning("⏱️ API ping timeout - service may be cold starting, will retry later")
        return False
    except Exception as e:
        LOG.error(f"❌ API ping failed: {e}")
        return False

def warm_up_api(max_attempts: int = 3) -> bool:
    """
    Warm up the API with multiple attempts if needed.
    Useful for cold-start scenarios on free hosting tiers.
    """
    import time
    
    for attempt in range(1, max_attempts + 1):
        LOG.info(f"🔥 Warming up API (attempt {attempt}/{max_attempts})...")
        
        if ping_api():
            return True
        
        if attempt < max_attempts:
            wait_time = 45 * attempt
            LOG.info(f"Waiting {wait_time}s before next attempt...")
            time.sleep(wait_time)
    
    LOG.warning("⚠️ API warm-up incomplete, but will proceed anyway")
    return False
