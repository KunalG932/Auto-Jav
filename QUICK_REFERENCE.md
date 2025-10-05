# Quick Reference Guide - New Features

## 🎬 Telegraph Video Preview

### Basic Usage
```python
from Jav.utils.telegraph import create_telegraph_preview_async

# Generate preview
url = await create_telegraph_preview_async(
    video_path="/path/to/video.mp4",
    title="My Video",
    description="Optional description",
    num_screenshots=6  # Optional, default is 6
)

if url:
    print(f"Preview available at: {url}")
```

### Synchronous Version
```python
from Jav.utils.telegraph import create_telegraph_preview

url = create_telegraph_preview(
    video_path="/path/to/video.mp4",
    title="My Video"
)
```

---

## 🤖 AI Caption Generation

### Basic Usage
```python
from Jav.api.ai_caption import fetch_and_format, create_enhanced_caption

# Simple AI caption
caption = fetch_and_format(
    content="Video about awesome content",
    timeout=8,
    max_retries=2
)

# Enhanced caption with metadata
full_caption = create_enhanced_caption(
    title="Video Title",
    item={
        'code': 'ABC-123',
        'actresses': ['Actor 1', 'Actor 2'],
        'tags': ['tag1', 'tag2'],
        'description': 'Video description'
    },
    video_path="/path/to/video.mp4"
)
```

---

## ⏱️ Duration Extraction

### Basic Usage
```python
from Jav.api.ai_caption import get_video_duration

# Get formatted duration
duration = get_video_duration("/path/to/video.mp4")
print(duration)  # Output: "01:23:45" or "23:45"
```

---

## 🛡️ FloodWait Error Handling

### Pattern for Any Telegram API Call
```python
from pyrogram import errors
import asyncio

async def safe_telegram_operation():
    try:
        # Your Telegram API call
        await client.send_message(chat_id, text)
    except errors.FloodWait as fw:
        wait_time = int(fw.value) if isinstance(fw.value, (int, float)) else 60
        LOG.warning(f"FloodWait: sleeping for {wait_time}s")
        await asyncio.sleep(float(wait_time))
        try:
            # Retry once
            await client.send_message(chat_id, text)
        except Exception as e:
            LOG.error(f"Retry failed: {e}")
```

### Already Protected Operations
- Message editing
- Photo/video sending
- Document uploading
- Sticker sending
- Reply markup editing
- Button addition

---

## 🔍 Error Checking

### Check if FloodWait Handling is Working
```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.INFO)

# Look for these log messages:
# "FloodWait: sleeping for X seconds"
# "FloodWait during upload: sleeping for X seconds"
# "FloodWait when posting photo: sleeping for X seconds"
```

### Check Telegraph Preview Status
```python
# Look for these log messages:
# "🎬 Creating Telegraph preview with video screenshots..."
# "✅ Telegraph preview created: <url>"
# "Extracted screenshot X/Y at Z seconds"
```

---

## 📋 Common Patterns

### Pattern 1: Safe Message Editing
```python
async def safe_edit(text: str):
    try:
        await bot_client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text
        )
    except errors.FloodWait as fw:
        wait_time = int(fw.value) if isinstance(fw.value, (int, float)) else 60
        await asyncio.sleep(float(wait_time))
        try:
            await bot_client.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text
            )
        except Exception:
            pass
```

### Pattern 2: Safe File Upload
```python
async def safe_upload(file_path: str):
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            return await client.send_document(
                chat_id=chat_id,
                document=file_path
            )
        except errors.FloodWait as fw:
            if attempt < max_attempts:
                wait_time = int(fw.value) if isinstance(fw.value, (int, float)) else 60
                await asyncio.sleep(float(wait_time))
                continue
            raise
```

### Pattern 3: Telegraph + AI Caption
```python
async def create_full_post(video_path: str, title: str, item: dict):
    # Generate AI caption
    caption = create_enhanced_caption(title, item, video_path)
    
    # Create Telegraph preview
    telegraph_url = await create_telegraph_preview_async(
        video_path=video_path,
        title=title,
        description=f"Preview for {title}"
    )
    
    # Add Telegraph link to caption
    if telegraph_url:
        caption += f"\n\n🎬 [Video Preview]({telegraph_url})"
    
    return caption
```

---

## ⚙️ Configuration Examples

### Customize Telegraph Screenshots
```python
# More screenshots
telegraph_url = await create_telegraph_preview_async(
    video_path=path,
    title=title,
    num_screenshots=10
)

# Fewer screenshots (faster)
telegraph_url = await create_telegraph_preview_async(
    video_path=path,
    title=title,
    num_screenshots=4
)
```

### Customize AI Caption Retries
```python
# More aggressive retry
caption = fetch_and_format(
    content=content,
    timeout=15,
    max_retries=5
)

# Quick fail (no retry)
caption = fetch_and_format(
    content=content,
    timeout=5,
    max_retries=0
)
```

---

## 🧪 Testing Snippets

### Test Telegraph Module
```python
import asyncio
from Jav.utils.telegraph import create_telegraph_preview_async

async def test_telegraph():
    url = await create_telegraph_preview_async(
        video_path="test_video.mp4",
        title="Test Video",
        num_screenshots=3
    )
    print(f"Result: {url}")

asyncio.run(test_telegraph())
```

### Test FloodWait Handling
```python
from pyrogram import Client, errors
import asyncio

async def test_floodwait():
    async with Client("test") as app:
        for i in range(20):  # Trigger FloodWait
            try:
                await app.send_message("me", f"Test {i}")
            except errors.FloodWait as e:
                print(f"Got FloodWait: {e.value}s")
                await asyncio.sleep(e.value)

asyncio.run(test_floodwait())
```

### Test Duration Extraction
```python
from Jav.api.ai_caption import get_video_duration

videos = ["video1.mp4", "video2.mkv", "video3.ts"]
for video in videos:
    duration = get_video_duration(video)
    print(f"{video}: {duration or 'Failed'}")
```

---

## 🚨 Error Messages Reference

### Telegraph Errors
- `"Video file not found"` → Check file path
- `"Could not get video duration"` → ffprobe issue
- `"Failed to extract screenshot"` → ffmpeg issue
- `"No screenshots extracted"` → Check video file
- `"Failed to post to Telegraph"` → Network/API issue

### FloodWait Errors
- `"FloodWait: sleeping for X seconds"` → Normal rate limiting
- `"FloodWait during upload"` → Upload rate limit hit
- `"Failed after FloodWait retry"` → Persistent issue

### AI Caption Errors
- `"AI caption request failed"` → Network/API issue
- `"Failed to parse JSON"` → API response issue
- `"AI caption request timeout"` → Increase timeout

### Duration Extraction Errors
- `"ffprobe failed with return code X"` → ffprobe error
- `"Could not parse duration value"` → Invalid video
- `"ffprobe timeout"` → Large file or slow disk
- `"ffprobe not found"` → Install ffmpeg

---

## 💡 Best Practices

1. **Always handle FloodWait** in loops or bulk operations
2. **Use async Telegraph creation** to avoid blocking
3. **Log FloodWait occurrences** for monitoring
4. **Set appropriate timeouts** based on file sizes
5. **Test with small files first** before processing large videos
6. **Monitor Telegraph storage** (has limits)
7. **Catch and log all exceptions** for debugging
8. **Use fallback captions** when AI fails

---

## 📚 Additional Resources

- [Pyrogram FloodWait Docs](https://docs.pyrogram.org/api/errors)
- [Telegraph API](https://telegra.ph/api)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)

---

**Quick Start Checklist**:
- ✅ Install ffmpeg and ffprobe
- ✅ Verify html-telegraph-poster package
- ✅ Import necessary modules
- ✅ Add error handling to Telegram calls
- ✅ Test with sample videos
- ✅ Monitor logs for errors
