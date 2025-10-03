import hashlib
import logging
from typing import List, Dict, Any, Optional
import time
import requests
from ..config import SETTINGS
from ..utils import translate_to_english

LOG = logging.getLogger("Jav")

def translate_item_fields(item: Dict[str, Any]) -> Dict[str, Any]:
    """Translate specific fields in item to English if they contain non-English text."""
    try:
        if 'title' in item and item['title']:
            translated_title = translate_to_english(str(item['title']))
            if translated_title and translated_title != str(item['title']):
                LOG.info(f"Translated title: {item['title'][:50]} -> {translated_title[:50]}")
                item['title'] = translated_title
        
        if 'description' in item and item['description']:
            translated_desc = translate_to_english(str(item['description']))
            if translated_desc and translated_desc != str(item['description']):
                LOG.info("Translated description")
                item['description'] = translated_desc
        
        if 'tags' in item and isinstance(item['tags'], list):
            translated_tags = []
            for tag in item['tags']:
                if isinstance(tag, str) and tag:
                    translated_tag = translate_to_english(tag)
                    translated_tags.append(translated_tag if translated_tag else tag)
                else:
                    translated_tags.append(tag)
            item['tags'] = translated_tags
    except Exception as e:
        LOG.warning(f"Translation error for item fields: {e}")
    
    return item

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

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
    
    # Translate items to English
    try:
        translated_data = []
        for item in data:
            translated_item = translate_item_fields(item)
            translated_data.append(translated_item)
        LOG.info(f"Translated {len(translated_data)} items")
        return translated_data
    except Exception as e:
        LOG.warning(f"Translation process failed, returning untranslated data: {e}")
        return data

def get_title(item: Dict[str, Any]) -> str:
    return item.get("title") or ""
