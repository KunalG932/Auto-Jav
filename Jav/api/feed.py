import hashlib
import logging
from typing import List, Dict, Any, Optional
import time
import requests
from ..config import SETTINGS

LOG = logging.getLogger("Jav")

def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()

def fetch_jav() -> Optional[List[Dict[str, Any]]]:
    last_err: Optional[Exception] = None
    data: Optional[List[Dict[str, Any]]] = None

    for attempt in range(1, SETTINGS.api_retries + 1):
        try:
            timeout = SETTINGS.api_timeout_sec + (attempt * 30)
            LOG.info(f"Fetching from API (attempt {attempt}/{SETTINGS.api_retries}, timeout={timeout}s)...")
            
            response = requests.get(
                SETTINGS.api_endpoint,
                timeout=timeout,
                headers={'User-Agent': 'Auto-JAV-Bot/2.0'}
            )
            response.raise_for_status()
            data = response.json()
            LOG.info(f"✅ API fetch successful on attempt {attempt}")
            break
        except requests.exceptions.Timeout as e:
            last_err = e
            LOG.warning(f"⏱️ API timeout (try {attempt}/{SETTINGS.api_retries}): Service may be cold starting")
            if attempt < SETTINGS.api_retries:
                backoff = SETTINGS.api_backoff_sec * attempt
                LOG.info(f"Retrying in {backoff}s with exponential backoff...")
                time.sleep(backoff)
            else:
                LOG.error("❌ All retries exhausted - API unavailable")
                return None
        except requests.exceptions.RequestException as e:
            last_err = e
            LOG.error(f"API request error (try {attempt}/{SETTINGS.api_retries}): {e}")
            if attempt < SETTINGS.api_retries:
                backoff = SETTINGS.api_backoff_sec * attempt
                LOG.info(f"Retrying in {backoff}s...")
                time.sleep(backoff)
            else:
                LOG.exception("All retries failed")
                return None
        except Exception as e:
            last_err = e
            LOG.error(f"Unexpected error (try {attempt}/{SETTINGS.api_retries}): {e}")
            if attempt < SETTINGS.api_retries:
                backoff = SETTINGS.api_backoff_sec * attempt
                time.sleep(backoff)
            else:
                LOG.exception("All retries failed")
                return None

    if not isinstance(data, list):
        LOG.error(f"Invalid API response (expected list): {type(data)}")
        return None

    LOG.info(f"Fetched {len(data)} items from API")
    return data

def get_title(item: Dict[str, Any]) -> str:
    return item.get("title") or ""
