import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List

load_dotenv()

def _get_list(var: str, default: str = "") -> List[int]:
    raw = os.getenv(var, default)
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    out: List[int] = []
    for p in parts:
        try:
            out.append(int(p))
        except ValueError:
            pass
    return out

@dataclass(frozen=True)
class Settings:
    author: str = os.getenv("AUTHOR", "Unknown")
    licensed_under: str = os.getenv("LICENSED_UNDER", "Unknown")

    owner_ids: tuple[int, ...] = tuple(_get_list("OWNER_IDS"))

    mongo_uri: str = os.getenv("MONGO_URI", "")

    main_channel: str = os.getenv("MAIN_CHANNEL", "")
    thumbnail_path: str = os.getenv("THUMBNAIL_PATH", "AAB/utils/thumb.jpeg")
    files_channel: int = int(os.getenv("FILES_CHANNEL", "0"))
    production_chat: int = int(os.getenv("PRODUCTION_CHAT", "0"))

    api_id: int = int(os.getenv("API_ID", "0"))
    api_hash: str = os.getenv("API_HASH", "")
    main_bot_token: str = os.getenv("MAIN_BOT_TOKEN", "")
    client_bot_token: str = os.getenv("CLIENT_BOT_TOKEN", "")

    check_interval_sec: int = int(os.getenv("CHECK_INTERVAL_SEC", "300"))
    api_endpoint: str = os.getenv("JAV_API_URL", "https://jav-api-w4od.onrender.com/api/latest?limit=20&sort_by_date=true&translate=true")
    api_timeout_sec: int = int(os.getenv("JAV_API_TIMEOUT_SEC", "120"))
    api_retries: int = int(os.getenv("JAV_API_RETRIES", "5"))
    api_backoff_sec: int = int(os.getenv("JAV_API_BACKOFF_SEC", "30"))

    torrent_metadata_timeout_sec: int = int(os.getenv("TORRENT_METADATA_TIMEOUT_SEC", "90"))
    torrent_stall_timeout_sec: int = int(os.getenv("TORRENT_STALL_TIMEOUT_SEC", "300"))
    download_update_interval_sec: int = int(os.getenv("DOWNLOAD_UPDATE_INTERVAL_SEC", "10"))

    enable_encoding: bool = os.getenv("ENABLE_ENCODING", "true").lower() == "true"
    max_resolution_width: int = int(os.getenv("MAX_RESOLUTION_WIDTH", "1280"))
    max_resolution_height: int = int(os.getenv("MAX_RESOLUTION_HEIGHT", "720"))
    encode_crf: int = int(os.getenv("ENCODE_CRF", "23"))
    encode_preset: str = os.getenv("ENCODE_PRESET", "medium")
    encode_video_codec: str = os.getenv("ENCODE_VIDEO_CODEC", "libx264")
    encode_audio_codec: str = os.getenv("ENCODE_AUDIO_CODEC", "aac")
    encode_audio_bitrate: str = os.getenv("ENCODE_AUDIO_BITRATE", "128k")

    sticker_id: str = os.getenv("STICKER_ID", "CAACAgUAAx0CfPp_PwABAcDbaOJjfQ7heaCB2i0QYNE41czE0KAAAq8YAAKcZulW-3JDFK03uP8eBA")

SETTINGS = Settings()
