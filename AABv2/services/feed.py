import hashlib
import logging
from typing import List, Dict, Any, Optional
import time
import requests
from ..config import SETTINGS

LOG = logging.getLogger("AABv2")

def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()

def fetch_jav() -> Optional[List[Dict[str, Any]]]:
    last_err: Optional[Exception] = None
    data: Optional[List[Dict[str, Any]]] = None

    for attempt in range(1, SETTINGS.api_retries + 1):
        try:
            response = requests.get(SETTINGS.api_endpoint, timeout=SETTINGS.api_timeout_sec)
            response.raise_for_status()
            data = response.json()
            break
        except Exception as e:
            last_err = e
            LOG.error(f"API fetch error (try {attempt}/{SETTINGS.api_retries}): {e}")
            if attempt < SETTINGS.api_retries:
                LOG.info(f"Retrying in {SETTINGS.api_backoff_sec}s...")
                time.sleep(SETTINGS.api_backoff_sec)
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
