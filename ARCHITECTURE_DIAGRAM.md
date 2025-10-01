# 🎬 Auto-JAV Bot - Video Encoding Architecture

## 📐 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AUTO-JAV BOT v2.0                            │
│                    (With 720p Encoding)                             │
└─────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │  JAV API    │
                              │  (External) │
                              └──────┬──────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────┐
│                         FEED CHECKER                                │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ AABv2/services/feed.py                                       │ │
│  │ • Fetch latest items from API                                │ │
│  │ • Parse video metadata                                       │ │
│  │ • Check for duplicates                                       │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                      VIDEO PROCESSOR                                │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ AABv2/processors/video_processor.py                          │ │
│  │                                                               │ │
│  │  ┌─────────────────┐                                         │ │
│  │  │ 1. DOWNLOAD     │  ←─── Magnet/Torrent Link               │ │
│  │  └────────┬────────┘                                         │ │
│  │           │ AABv2/services/downloader.py                     │ │
│  │           │ • libtorrent integration                         │ │
│  │           │ • Progress tracking                              │ │
│  │           │ • Find largest video file                        │ │
│  │           ▼                                                   │ │
│  │  ┌─────────────────┐                                         │ │
│  │  │ 2. REMUX        │  ←─── .ts → .mp4 conversion            │ │
│  │  └────────┬────────┘                                         │ │
│  │           │ FFmpeg: -c copy                                  │ │
│  │           │ • Container format change                        │ │
│  │           │ • No re-encoding                                 │ │
│  │           ▼                                                   │ │
│  │  ┌─────────────────┐                                         │ │
│  │  │ 3. ENCODE ✨    │  ←─── NEW! 720p Encoding               │ │
│  │  └────────┬────────┘                                         │ │
│  │           │ AABv2/services/encode.py                         │ │
│  │           │ • Check resolution                               │ │
│  │           │ • Scale to max 720p                              │ │
│  │           │ • H.264 encoding (CRF 23)                        │ │
│  │           │ • AAC audio (128k)                               │ │
│  │           │ • File size reduction ~50%                       │ │
│  │           ▼                                                   │ │
│  │  ┌─────────────────┐                                         │ │
│  │  │ 4. UPLOAD       │  ←─── To Telegram                      │ │
│  │  └────────┬────────┘                                         │ │
│  │           │ AABv2/services/uploader.py                       │ │
│  │           │ • Split if >2GB                                  │ │
│  │           │ • Progress tracking                              │ │
│  │           │ • Generate file hash                             │ │
│  │           ▼                                                   │ │
│  │  ┌─────────────────┐                                         │ │
│  │  │ 5. POST         │  ←─── To main channel                  │ │
│  │  └────────┬────────┘                                         │ │
│  │           │ • Thumbnail                                      │ │
│  │           │ • Caption                                        │ │
│  │           │ • Download button                                │ │
│  │           ▼                                                   │ │
│  │  ┌─────────────────┐                                         │ │
│  │  │ 6. CLEANUP      │  ←─── Remove temp files                │ │
│  │  └─────────────────┘                                         │ │
│  │                                                               │ │
│  └──────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘

```

## 🔧 Encoding Module Detail

```
┌────────────────────────────────────────────────────────────────────┐
│                    AABv2/services/encode.py                         │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  get_video_info(file_path)                                 │   │
│  ├────────────────────────────────────────────────────────────┤   │
│  │  • Run ffprobe                                             │   │
│  │  • Extract: width, height, duration, bitrate              │   │
│  │  • Return: Dict[str, Any]                                  │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  encode_file(input_path, output_path=None)                 │   │
│  ├────────────────────────────────────────────────────────────┤   │
│  │                                                             │   │
│  │  1. Get current video info                                 │   │
│  │     ↓                                                       │   │
│  │  2. Build FFmpeg command                                   │   │
│  │     • Video: libx264, CRF 23, medium preset                │   │
│  │     • Scale: max 1280px width (720p)                       │   │
│  │     • Audio: AAC 128k                                      │   │
│  │     ↓                                                       │   │
│  │  3. Execute FFmpeg (timeout: 1 hour)                       │   │
│  │     ↓                                                       │   │
│  │  4. Verify output exists                                   │   │
│  │     ↓                                                       │   │
│  │  5. Calculate size reduction                               │   │
│  │     ↓                                                       │   │
│  │  6. Return: encoded_file_path or None                      │   │
│  │                                                             │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  encode_with_crf(input_path, crf=23, output_path=None)     │   │
│  ├────────────────────────────────────────────────────────────┤   │
│  │  • Temporary override CRF setting                          │   │
│  │  • Call encode_file()                                      │   │
│  │  • Restore original CRF                                    │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

## ⚙️ Configuration Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                         .env File                                   │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ENABLE_ENCODING=true                                              │
│  MAX_RESOLUTION_WIDTH=1280                                         │
│  MAX_RESOLUTION_HEIGHT=720                                         │
│  ENCODE_CRF=23                                                     │
│  ENCODE_PRESET=medium                                              │
│  ENCODE_VIDEO_CODEC=libx264                                        │
│  ENCODE_AUDIO_CODEC=aac                                            │
│  ENCODE_AUDIO_BITRATE=128k                                         │
│                                                                     │
└───────────────────────────┬────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────────┐
│                    AABv2/config.py                                  │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  @dataclass(frozen=True)                                           │
│  class Settings:                                                   │
│      enable_encoding: bool                                         │
│      max_resolution_width: int                                     │
│      max_resolution_height: int                                    │
│      encode_crf: int                                               │
│      encode_preset: str                                            │
│      encode_video_codec: str                                       │
│      encode_audio_codec: str                                       │
│      encode_audio_bitrate: str                                     │
│                                                                     │
│  SETTINGS = Settings()  # Global instance                          │
│                                                                     │
└───────────────────────────┬────────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────────┐
│              Used by encode.py & video_processor.py                 │
│                                                                     │
│  if SETTINGS.enable_encoding:                                      │
│      encode_file(...)                                              │
│  else:                                                              │
│      use_original_file(...)                                        │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

## 📊 Data Flow Example

```
┌─────────────────────────────────────────────────────────────────────┐
│                     PROCESSING EXAMPLE                              │
└─────────────────────────────────────────────────────────────────────┘

Input Video:
┌──────────────────────────────────────┐
│ File: video.mkv                      │
│ Resolution: 1920x1080 (FHD)          │
│ Size: 2.5 GB                         │
│ Format: Matroska (MKV)               │
│ Codec: H.264                         │
└──────────────────┬───────────────────┘
                   │
                   │ STEP 1: Download
                   ▼
┌──────────────────────────────────────┐
│ File: video.mkv                      │
│ Location: ./downloads/               │
│ Status: Downloaded ✓                 │
└──────────────────┬───────────────────┘
                   │
                   │ STEP 2: Remux (if needed)
                   ▼
┌──────────────────────────────────────┐
│ File: video.mp4                      │
│ Resolution: 1920x1080                │
│ Size: 2.5 GB                         │
│ Format: MP4                          │
│ Status: Remuxed ✓                    │
└──────────────────┬───────────────────┘
                   │
                   │ STEP 3: Encode ✨ NEW!
                   ▼
┌──────────────────────────────────────┐
│ FFmpeg Command:                      │
│ ffmpeg -i video.mp4 \                │
│   -c:v libx264 -crf 23 \             │
│   -preset medium \                   │
│   -vf "scale='min(1280,iw)':-2" \    │
│   -c:a aac -b:a 128k \               │
│   video_encoded.mp4                  │
└──────────────────┬───────────────────┘
                   │
                   │ Processing... (~12 min)
                   ▼
Output Video:
┌──────────────────────────────────────┐
│ File: video_encoded.mp4              │
│ Resolution: 1280x720 (HD)            │
│ Size: 1.2 GB (-52%)                  │
│ Format: MP4                          │
│ Codec: H.264 (optimized)             │
│ Status: Ready for upload ✓           │
└──────────────────┬───────────────────┘
                   │
                   │ STEP 4: Upload
                   ▼
┌──────────────────────────────────────┐
│ Telegram Files Channel               │
│ File uploaded ✓                      │
│ Hash generated ✓                     │
└──────────────────┬───────────────────┘
                   │
                   │ STEP 5: Post
                   ▼
┌──────────────────────────────────────┐
│ Telegram Main Channel                │
│ • Thumbnail displayed                │
│ • Caption posted                     │
│ • Download button added              │
│ Status: Complete ✓                   │
└──────────────────────────────────────┘

RESULT:
• Original: 2.5 GB, 1920x1080
• Final: 1.2 GB, 1280x720
• Savings: 1.3 GB (52% reduction)
• Upload time: 50% faster
```

## 🎯 Resolution Scaling Logic

```
┌────────────────────────────────────────────────────────────────────┐
│                     RESOLUTION HANDLING                             │
└────────────────────────────────────────────────────────────────────┘

FFmpeg Filter: scale='min(1280,iw)':-2

Logic:
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  IF input_width > 1280:                                     │
│      new_width = 1280                                       │
│      new_height = (1280 / input_width) * input_height      │
│      # Downscale to 720p                                    │
│                                                              │
│  ELSE:                                                       │
│      new_width = input_width                                │
│      new_height = input_height                              │
│      # Keep original size, but re-encode for quality        │
│                                                              │
│  # Ensure height is divisible by 2                          │
│  new_height = floor(new_height / 2) * 2                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘

Examples:
┌──────────────────┬───────────────────┬────────────────┐
│ Input            │ Output            │ Action         │
├──────────────────┼───────────────────┼────────────────┤
│ 3840x2160 (4K)   │ 1280x720          │ ⬇️ Downscale   │
│ 1920x1080 (FHD)  │ 1280x720          │ ⬇️ Downscale   │
│ 1280x720 (HD)    │ 1280x720          │ 🔄 Re-encode   │
│ 854x480 (SD)     │ 854x480           │ 🔄 Re-encode   │
│ 640x360          │ 640x360           │ 🔄 Re-encode   │
└──────────────────┴───────────────────┴────────────────┘

Note: Videos are NEVER upscaled, only downscaled or re-encoded
```

## 🚦 Error Handling Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                      ERROR HANDLING                                 │
└────────────────────────────────────────────────────────────────────┘

encode_file() execution:
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  try:                                                        │
│      1. Check input file exists                             │
│         ├─ No → Log error, return None                      │
│         └─ Yes → Continue                                   │
│                                                              │
│      2. Get video info                                      │
│         ├─ Failed → Log warning, continue                   │
│         └─ Success → Use info                               │
│                                                              │
│      3. Build FFmpeg command                                │
│                                                              │
│      4. Execute FFmpeg                                      │
│         ├─ Timeout (>1hr) → Log error, return None          │
│         ├─ Non-zero exit → Log error, return None           │
│         ├─ FFmpeg not found → Log error, return None        │
│         └─ Success → Continue                               │
│                                                              │
│      5. Verify output file                                  │
│         ├─ Not exists → Log error, return None              │
│         └─ Exists → Return path                             │
│                                                              │
│  except Exception as e:                                      │
│      Log exception                                           │
│      return None                                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘

In video_processor.py:
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  if SETTINGS.enable_encoding:                               │
│      encoded_path = encode_file(path)                       │
│                                                              │
│      if encoded_path:                                       │
│          upload_path = encoded_path  # Use encoded          │
│      else:                                                   │
│          upload_path = original_path  # Fallback            │
│          notify_user("Encoding failed, using original")     │
│                                                              │
└─────────────────────────────────────────────────────────────┘

Result: System NEVER fails due to encoding errors
        Always falls back to original file
```

## 📁 File Structure

```
Auto-Jav/
├── AABv2/
│   ├── config.py ────────────────┐ (Settings dataclass)
│   ├── processors/               │
│   │   └── video_processor.py ───┤ (Main workflow)
│   └── services/                 │
│       ├── encode.py ─────────────┤ (Encoding engine) ✨ NEW
│       ├── downloader.py ─────────┤ (Torrent download)
│       ├── uploader.py ───────────┤ (Telegram upload)
│       └── feed.py ───────────────┘ (API fetching)
│
├── .env.example ─────────────────┐ (Config template)
├── README.md ────────────────────┤ (Main docs)
├── ENCODING_SETUP.md ────────────┤ (Setup guide) ✨ NEW
├── ENCODING_QUICK_REFERENCE.md ──┤ (Quick ref) ✨ NEW
├── VIDEO_ENCODING_IMPLEMENTATION.md ┤ (Tech docs) ✨ NEW
├── IMPLEMENTATION_COMPLETE.md ───┤ (Status) ✨ NEW
├── FILE_CHANGES_SUMMARY.md ──────┤ (Changes) ✨ NEW
└── test_encoding.py ─────────────┘ (Test suite) ✨ NEW
```

---

**Legend:**
- ✨ NEW = Newly created/implemented
- ⬇️ = Downscaling action
- 🔄 = Re-encoding action
- ✓ = Completed step
- → = Data flow
- ↓ = Sequential flow
