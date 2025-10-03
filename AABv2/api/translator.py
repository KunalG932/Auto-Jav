import logging
from typing import Any, Dict, List
from ..utils import translate_to_english

LOG = logging.getLogger("AABv2")

def translate_item(item: Dict[str, Any]) -> Dict[str, Any]:
    
    if isinstance(item, dict):
        return {key: translate_item(value) for key, value in item.items()}
    elif isinstance(item, list):
        return [translate_item(elem) for elem in item]
    elif isinstance(item, str):
        return translate_to_english(item)
    else:
        return item

def translate_api_response(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    
    LOG.info(f"Translating {len(results)} items to English")
    return [translate_item(item) for item in results]