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

def fetch_and_format(content: str, timeout: int = 8, max_retries: int = 2) -> Optional[str]:
    """Fetch AI-generated caption with retry logic and enhanced error handling."""
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

    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
            resp.raise_for_status()
            
            try:
                data = resp.json()
            except Exception as e:
                LOG.warning(f"Failed to parse JSON from AI caption response (attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    continue
                return None

            content_field = data.get("content")
            if content_field and isinstance(content_field, str):
                return content_field.strip()
            
            msg = data.get("message")
            if isinstance(msg, str) and msg.strip():
                return msg.strip()
                
            LOG.debug(f"AI caption service returned no content (attempt {attempt + 1}): {data}")
            
        except requests.exceptions.Timeout:
            LOG.warning(f"AI caption request timeout (attempt {attempt + 1}/{max_retries + 1})")
            if attempt < max_retries:
                continue
        except requests.exceptions.RequestException as e:
            LOG.warning(f"AI caption request failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
            if attempt < max_retries:
                continue
        except Exception as e:
            LOG.error(f"Unexpected error in AI caption generation: {e}")
            return None
    
    return None

    msg = data.get("message")
    if isinstance(msg, str) and msg.strip():
        return msg.strip()

    LOG.debug(f"AI caption service returned no content: {data}")
    return None

def get_video_duration(file_path: str) -> Optional[str]:
    """Extract video duration using ffprobe with enhanced error handling."""
    if not os.path.exists(file_path):
        LOG.warning(f"Video file not found: {file_path}")
        return None
    
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode != 0:
            LOG.warning(f"ffprobe failed with return code {result.returncode}: {result.stderr}")
            return None
            
        if result.stdout.strip():
            try:
                duration_sec = float(result.stdout.strip())
                
                if duration_sec <= 0:
                    LOG.warning(f"Invalid duration value: {duration_sec}")
                    return None
                    
                hours = int(duration_sec // 3600)
                minutes = int((duration_sec % 3600) // 60)
                seconds = int(duration_sec % 60)
                
                if hours > 0:
                    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    return f"{minutes:02d}:{seconds:02d}"
            except ValueError as ve:
                LOG.warning(f"Could not parse duration value: {result.stdout.strip()}, error: {ve}")
                return None
    except subprocess.TimeoutExpired:
        LOG.warning(f"ffprobe timeout for file: {file_path}")
    except FileNotFoundError:
        LOG.error("ffprobe not found. Please install ffmpeg.")
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
            actresses = item.get('actresses', [])
            tags = item.get('tags', [])
            
            actresses_str = ', '.join(actresses[:3]) if isinstance(actresses, list) and actresses else 'performers'
            tags_str = ', '.join(tags[:5]) if isinstance(tags, list) and tags else 'exciting content'
            
            prompt = f"Create a seductive 2-3 sentence description for this adult video: Title: {title_text}, Code: {code}, Starring: {actresses_str}, Tags: {tags_str}. Make it enticing and flirty with emojis."
            
            ai_result = fetch_and_format(prompt, timeout=15)
            if ai_result and len(ai_result.strip()) > 20:
                description = ai_result
                LOG.info("Generated description using AI")
            else:
                description = f"🔥 An absolutely captivating experience featuring {actresses_str} that will leave you wanting more! Don't miss this masterpiece! 💯✨"
                LOG.info("Using enhanced fallback description")
        except Exception as e:
            LOG.warning(f"Failed to generate AI description: {e}")
            description = "🔥 An absolutely captivating experience that will leave you wanting more! Don't miss this masterpiece! 💯"
    
    caption_parts = [
        f"**📺 {title}**",
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
