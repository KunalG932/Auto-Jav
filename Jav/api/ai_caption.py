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
    "bouncy peaches",
    "juicy melons",
    "thirsty cherries",
    "slick honey drip",
    "naughty lollipop",
    "forbidden fruit",
    "pulsing rocket",
    "cheeky buns",
    "sweet cream swirl",
    "spicy sausage",
    "glazed donut",
    "sticky popsicle",
    "succulent banana",
    "wild shake",
    "plump dumplings",
]

def sanitize_input(text: str) -> str:
    sanitized = text
    for word_pattern in NSFW_WORDS:
        replacement = random.choice(NSFW_REPLACEMENTS)
        sanitized = re.sub(word_pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized

def fetch_and_format(text: str, timeout: int = 10) -> Optional[str]:
    if not text or not isinstance(text, str):
        return None
    try:
        sanitized = sanitize_input(text)
        result = call_ai_api(sanitized, mode="caption", timeout=timeout)
        if result:
            LOG.info(f"AI caption generated: {result[:100]}...")
            return result
        else:
            LOG.warning("AI API returned empty result")
            return None
    except Exception as e:
        LOG.error(f"Error in fetch_and_format: {e}")
        return None

def call_ai_api(prompt: str, mode: str = "caption", timeout: int = 10, max_retries: int = 3) -> Optional[str]:
    import time
    import requests

    if not prompt or not isinstance(prompt, str):
        return None

    sanitized_prompt = sanitize_input(prompt)
    url = "https://lexica.qewertyy.dev/models"

    base_system_instruction = (
        "System Instruction: Absolute Mode • Eliminate: emojis, filler, hype, soft asks, conversational transitions, call-to-action appendixes. "
        "• Assume: user retains high-perception despite blunt tone. • Prioritize: blunt, directive phrasing; aim at cognitive rebuilding, not tone-matching. "
        "• Disable: engagement/sentiment-boosting behaviors. • Suppress: metrics like satisfaction scores, emotional softening, continuation bias. "
        "• Never mirror: user’s diction, mood, or affect. • Speak only: to underlying cognitive tier. • No: questions, offers, suggestions, transitions, motivational content. "
        "• Terminate reply: immediately after delivering info — no closures. • Goal: restore independent, high-fidelity thinking. • Outcome: model obsolescence via user self-sufficiency."
    )

    if mode == "caption":
        system_role = (
            "You are a precise, safe caption creator. Output must be factual, neutral, and free from suggestive or unsafe content."
        )
        instructions = (
            "Write one concise, contextually relevant caption. No fluff. No slang. No emojis. No rhetorical devices. No innuendo. No call-to-action."
        )
    else:
        system_role = (
            "You are a precise, safe title generator. Output must be neutral, clear, and context-relevant."
        )
        instructions = (
            "Generate one short, contextually descriptive title (4–10 words max). Avoid sensationalism, marketing tone, emotive phrasing, innuendo, emojis, and suggestive content."
        )

    payload = {
        "model_id": 5,
        "messages": [
            {"role": "system", "content": f"{base_system_instruction} {system_role} {instructions}"},
            {"role": "user", "content": sanitized_prompt},
        ],
    }

    for attempt in range(max_retries):
        try:
            r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            result = data.get("content") or data.get("message")

            time.sleep(2)
            return result

        except requests.exceptions.Timeout:
            LOG.warning(f"AI API request timed out after {timeout}s (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                LOG.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                return None

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') and e.response else 'unknown'
            LOG.warning(f"AI API HTTP error: {status_code} (attempt {attempt + 1}/{max_retries})")
            if status_code in [429, 500, 502, 503]:
                if attempt < max_retries - 1:
                    wait_time = 3 ** attempt
                    LOG.info(f"Rate limited or server error. Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    LOG.error(f"Max retries reached for HTTP {status_code}")
                    return None
            else:
                return None

        except requests.exceptions.RequestException as e:
            LOG.warning(f"AI API network error: {e} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                return None

        except (ValueError, KeyError) as e:
            LOG.warning(f"AI API response parsing error: {e}")
            return None

        except Exception as e:
            LOG.error(f"Unexpected AI API error: {e}", exc_info=True)
            return None

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
            description = ai_caption if ai_caption and len(ai_caption.strip()) > 20 else f"Captivating performance by {actresses_str}, an unforgettable watch."
        except Exception:
            description = "Captivating performance you can’t miss."
    ai_title_prompt = f"Generate a precise, safe title for a film about: {title}, featuring {item.get('actresses', [])}."
    ai_title = call_ai_api(ai_title_prompt, "title", timeout=10)
    final_title = ai_title.strip() if ai_title else title
    caption_parts = [
        f"**📺 {final_title}**",
        "",
        f"**➪ Episode:-** __01 [{duration}]__",
        f"**➪ Subtitle:-** __English✅__",
        f"**➪ Rating:-** __{rating}/10__",
        f"**#{recommendation}**"
        "",
        f"> {description}",
        "",
        "**ᴘᴏᴡᴇʀᴇᴅ ʙʏ: [@The_Wyvern](https://t.me/Wyvern_Gateway_Bot?start=req_LTEwMDMxNjA3MzEwNjc)**"
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
