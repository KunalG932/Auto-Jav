import random
from deep_translator import GoogleTranslator

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890"


def generate_hash(length: int) -> str:
    return "".join(random.choice(_ALPHABET) for _ in range(length))


def translate_to_english(text: str) -> str:
    if not text or not isinstance(text, str):
        return text or ""
    try:
        translator = GoogleTranslator(source='auto', target='en')
        return translator.translate(text)
    except Exception:
        # If translation fails, return original text
        return text
