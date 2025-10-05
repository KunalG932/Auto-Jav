"""Utility package for the JAV Bot.

This package contains utility functions and modules including:
- generate_hash: Generate random alphanumeric hashes
- translate_to_english: Translate text to English using Google Translate
- telegraph: Telegraph integration for video previews
"""

import random
from deep_translator import GoogleTranslator
from .telegraph import create_telegraph_preview, create_telegraph_preview_async

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890"


def generate_hash(length: int) -> str:
    """Generate a random alphanumeric hash of specified length."""
    return "".join(random.choice(_ALPHABET) for _ in range(length))


def translate_to_english(text: str) -> str:
    """Translate text to English using Google Translate."""
    if not text or not isinstance(text, str):
        return text or ""
    try:
        translator = GoogleTranslator(source='auto', target='en')
        return translator.translate(text)
    except Exception:
        return text


__all__ = [
    'generate_hash',
    'translate_to_english',
    'create_telegraph_preview',
    'create_telegraph_preview_async',
]
