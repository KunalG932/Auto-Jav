import requests
import logging
from typing import Optional
import re
import random

LOG = logging.getLogger("AABv2")

NSFW_WORDS = [
    r"\btits\b",
    r"\bnipples\b",
    r"\buncensored\b",
    r"\bpussy\b",
    r"\bsex\b",
    r"\bdick\b",
    r"\bboobs\b",
    r"\bcock\b",
    r"\bass\b",
]

NSFW_REPLACEMENTS = [
    "bouncy peaches🍑",
    "juicy melons🍈",
    "thirsty cherries🍒",
    "slick honey drip💦",
    "naughty lollipop🍭",
    "forbidden fruit🍓",
    "pulsing rocket🍆",
    "cheeky buns🍑🔥",
    "sweet cream swirl🥛😉",
    "spicy sausage🌭🔥",
    "glazed donut🍩💦",
    "sticky popsicle🍭😏",
    "succulent banana🍌💦",
    "wild shake🥤🔥",
    "plump dumplings🥟🍑",
]

def sanitize_input(text: str) -> str:
    sanitized = text
    for word_pattern in NSFW_WORDS:
        replacement = random.choice(NSFW_REPLACEMENTS)
        sanitized = re.sub(word_pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized

def fetch_and_format(content: str, timeout: int = 8) -> Optional[str]:
    if not content or not isinstance(content, str):
        return None

    sanitized_content = sanitize_input(content)

    url = "https://lexica.qewertyy.dev/models"
    payload = {
        "model_id": 5,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a seductive and witty caption creator💋. Given a short title or tags, "
                    "craft exactly ONE teasing, flirty, and daring caption that feels like a performance🎭.\n\n"
                    "Rules:\n"
                    "  - Output ONLY the caption text (no lists, no JSON, no code formatting).\n"
                    "  - One or two short paragraphs max—make it punchy, juicy, and dripping with playful energy🔥.\n"
                    "  - Slide in naughty emojis like 😈🍑🍆💦🔥🍓🍭 naturally, not overloaded.\n"
                    "  - Hide a rating inside the flow with the literal word 'Rating:' (e.g. '➪ Rating: 98/10 💦').\n"
                    "  - Prefer the rating to pop up mid-caption like a cheeky reveal😉.\n"
                    "  - Replace raw explicit words with sexy euphemisms and flirty innuendos✨.\n"
                    "  - Tone: theatrical, horny, outrageous—but always entertaining💃.\n\n"
                    "Strict:\n"
                    "  - Only ONE caption.\n"
                    "  - Do NOT wrap the text in quotes or code blocks.\n"
                    "  - No explanations, no options, no commentary.\n"
                )
            },
            {"role": "user", "content": sanitized_content}
        ]
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        resp.raise_for_status()
    except Exception as e:
        LOG.warning(f"AI caption request failed: {e}")
        return None

    try:
        data = resp.json()
    except Exception as e:
        LOG.warning(f"Failed to parse JSON from AI caption response: {e}")
        return None

    content_field = data.get("content")
    if content_field and isinstance(content_field, str):
        return content_field.strip()

    msg = data.get("message")
    if isinstance(msg, str) and msg.strip():
        return msg.strip()

    LOG.debug(f"AI caption service returned no content: {data}")
    return None

def format_for_post(raw: Optional[str]) -> Optional[str]:
    if not raw or not isinstance(raw, str):
        return None

    s = raw.strip()
    low = s.lower()

    idx = low.find('rating')
    if idx == -1:
        return f"{s}\n\n"

    txt = s[:idx].strip()
    rest = s[idx:].strip()

    rating_line = rest
    if '\n' in rest:
        rating_line, after = rest.split('\n', 1)
        more = after.strip()
    else:
        close_idx = rest.find(']')
        if close_idx != -1:
            rating_line = rest[:close_idx+1].strip()
            more = rest[close_idx+1:].strip()
        else:
            rating_line = rest
            more = ''

    parts = []
    if txt:
        parts.append(txt)
    if rating_line:
        parts.append(rating_line)
    if more:
        parts.append('')
        parts.append(more)

    return "\n".join(parts)
