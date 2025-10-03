import requests
import logging
import subprocess
import os
from typing import Optional, Dict, Any
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

def get_video_duration(file_path: str) -> Optional[str]:
    
    if not os.path.exists(file_path):
        return None
    
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            duration_sec = float(result.stdout.strip())
            hours = int(duration_sec // 3600)
            minutes = int((duration_sec % 3600) // 60)
            seconds = int(duration_sec % 60)
            
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes:02d}:{seconds:02d}"
    except Exception as e:
        LOG.warning(f"Failed to get video duration: {e}")
    
    return None

def create_enhanced_caption(title: str, item: Dict[str, Any], video_path: Optional[str] = None) -> str:
    
    duration = "Unknown"
    if video_path and os.path.exists(video_path):
        video_duration = get_video_duration(video_path)
        if video_duration:
            duration = video_duration
    
    rating = round(random.uniform(7.5, 9.9), 1)
    
    recommendations = [
        "RECOMMENDED",
        "HIGHLY_RECOMMENDED",
        "ADMIN_RECOMMENDED",
        "MUST_WATCH",
        "TOP_PICK",
        "STAFF_FAVORITE"
    ]
    recommendation = random.choice(recommendations)
    
    description = ""
    
    api_description = item.get('description', '').strip()
    if api_description:
        description = api_description
        LOG.info("Using description from API")
    else:
        try:
            code = item.get('code', '')
            title_text = item.get('title', title)
            
            prompt = f"Title: {title_text}\nCode: {code}\nGenerate a short, enticing 2-3 sentence description."
            
            ai_result = fetch_and_format(prompt, timeout=10)
            if ai_result:
                description = ai_result
                LOG.info("Generated description using AI")
            else:
                description = "🔥 An absolutely captivating experience that will leave you wanting more! Don't miss this masterpiece! 💯"
                LOG.info("Using default fallback description")
        except Exception as e:
            LOG.warning(f"Failed to generate AI description: {e}")
            description = "🔥 An absolutely captivating experience that will leave you wanting more! Don't miss this masterpiece! 💯"
    
    caption_parts = [
        f"📺 {title}",
        f"➪ Episode:- 01 [{duration}]",
        f"➪ Subtitle:- English✅",
        f"➪ Rating:- {rating}/10",
        f"#{recommendation}",
        "",
        description,
        "",
        "ᴘᴏᴡᴇʀᴇᴅ ʙʏ: @The_Wyverns"
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
