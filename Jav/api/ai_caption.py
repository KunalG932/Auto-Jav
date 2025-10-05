import requests
import logging
import subprocess
import os
from typing import Optional, Dict, Any
import re
import random
import asyncio

LOG = logging.getLogger("Jav")

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

def call_ai_api(prompt: str, mode: str = "caption", timeout: int = 10) -> Optional[str]:
    if not prompt or not isinstance(prompt, str):
        return None
    sanitized_prompt = sanitize_input(prompt)
    url = "https://lexica.qewertyy.dev/models"
    system_role = "You are a seductive and witty caption creator💋." if mode == "caption" else "You are a creative adult film title generator🎬."
    instructions = (
        "Write one flirty, daring, playful caption. Use emojis like 😈🍑🍆💦🔥 naturally. "
        "Avoid raw words; use euphemisms. Output only text."
        if mode == "caption"
        else "Generate one short, enticing, flirty video title (4–10 words max). No quotes, no punctuation at end, no explicit words, use innuendo."
    )
    payload = {
        "model_id": 5,
        "messages": [
            {"role": "system", "content": f"{system_role} {instructions}"},
            {"role": "user", "content": sanitized_prompt},
        ],
    }
    try:
        r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data.get("content") or data.get("message")
    except Exception as e:
        LOG.warning(f"AI request failed: {e}")
        return None

def get_video_duration(file_path: str) -> Optional[str]:
    if not os.path.exists(file_path):
        return None
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0 or not result.stdout.strip():
            return None
        duration_sec = float(result.stdout.strip())
        if duration_sec <= 0:
            return None
        hours = int(duration_sec // 3600)
        minutes = int((duration_sec % 3600) // 60)
        seconds = int(duration_sec % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes:02d}:{seconds:02d}"
    except Exception:
        return None

def create_enhanced_caption(title: str, item: Dict[str, Any], video_path: Optional[str] = None) -> str:
    duration = "Unknown"
    if video_path and os.path.exists(video_path):
        video_duration = get_video_duration(video_path)
        if video_duration:
            duration = video_duration
    rating = round(random.uniform(7.5, 9.9), 1)
    recommendations = ["RECOMMENDED", "HIGHLY_RECOMMENDED", "ADMIN_RECOMMENDED", "MUST_WATCH", "TOP_PICK", "STAFF_FAVORITE"]
    recommendation = random.choice(recommendations)
    description = ""
    api_description = item.get('description', '').strip()
    if api_description:
        description = api_description
    else:
        try:
            code = item.get('code', '')
            title_text = item.get('title', title)
            actresses = item.get('actresses', [])
            tags = item.get('tags', [])
            actresses_str = ', '.join(actresses[:3]) if isinstance(actresses, list) and actresses else 'performers'
            tags_str = ', '.join(tags[:5]) if isinstance(tags, list) and tags else 'exciting content'
            prompt = f"Title: {title_text}, Code: {code}, Starring: {actresses_str}, Tags: {tags_str}"
            ai_caption = call_ai_api(prompt, "caption", timeout=15)
            description = ai_caption if ai_caption and len(ai_caption.strip()) > 20 else f"🔥 Captivating performance by {actresses_str}, an unforgettable watch! 💯✨"
        except Exception:
            description = "🔥 Captivating performance you can’t miss! 💯✨"
    ai_title_prompt = f"Generate a seductive title for an adult film about: {title}, featuring {item.get('actresses', [])}."
    ai_title = call_ai_api(ai_title_prompt, "title", timeout=10)
    final_title = ai_title.strip() if ai_title else title
    caption_parts = [
        f"**📺 {final_title}**",
        "",
        f"**➪ Episode:-** __01 [{duration}]__",
        f"**➪ Subtitle:-** __English✅__",
        f"**➪ Rating:-** __{rating}/10__",
        f"**#{recommendation}**",
        "",
        f"> {description}",
        "",
        "**ᴘᴏᴡᴇʀᴇᴅ ʙʏ: @The_Wyverns**"
    ]
    return "\n".join(caption_parts)

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
