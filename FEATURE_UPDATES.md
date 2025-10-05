# Feature Updates - Auto-Jav Bot

## Overview
This document outlines the new features and improvements added to the Auto-Jav bot codebase.

---

## 🎬 Telegraph Video Preview Generation

### What's New
- **Automated screenshot extraction** from videos at regular intervals
- **Telegraph page creation** with video preview screenshots
- **Smart timing** - screenshots are extracted from 10-90% of video duration to skip intros/outros
- **Configurable screenshot count** (default: 6 screenshots per video)

### Implementation Details

#### New Module: `Jav/utils/telegraph.py`
- `extract_video_screenshots()` - Extracts screenshots using ffmpeg
- `create_telegraph_preview()` - Creates Telegraph pages with uploaded screenshots
- `create_telegraph_preview_async()` - Async wrapper for Telegraph operations

#### Integration Points
- Video processor automatically generates Telegraph preview after encoding
- Telegraph URL is appended to video caption with clickable link
- Preview link format: `🎬 [Video Preview](telegraph_url)`

#### Requirements
- ffmpeg and ffprobe must be installed
- html-telegraph-poster package (already in requirements.txt)

### Usage Example
```python
telegraph_url = await create_telegraph_preview_async(
    video_path="/path/to/video.mp4",
    title="Video Title",
    description="Preview description",
    num_screenshots=6
)
```

---

## 🤖 AI Caption Enhancements

### What's New
- **Retry logic** - Up to 3 attempts with exponential backoff
- **Enhanced error handling** - Better timeout and exception management
- **Improved prompts** - More detailed system prompts for better AI responses
- **Fallback mechanisms** - Graceful degradation when AI service is unavailable

### Implementation Details

#### Enhanced Functions in `Jav/api/ai_caption.py`
1. **`fetch_and_format()`**
   - Now accepts `max_retries` parameter (default: 2)
   - Handles `requests.exceptions.Timeout` separately
   - Better JSON parsing error handling
   - Logs detailed attempt information

2. **`create_enhanced_caption()`**
   - Improved AI prompt generation
   - Better fallback description generation
   - Uses API description when available

### Key Improvements
```python
# Before
fetch_and_format(content, timeout=8)

# After
fetch_and_format(content, timeout=8, max_retries=2)
```

---

## ⏱️ Duration Extraction Improvements

### What's New
- **Enhanced validation** - Checks for valid duration values
- **Better error messages** - Detailed logging for troubleshooting
- **Timeout handling** - Increased timeout to 15 seconds for large files
- **Format validation** - Ensures parsed duration is positive

### Implementation Details

#### Enhanced Function in `Jav/api/ai_caption.py`
- `get_video_duration()` - Improved ffprobe integration
  - Validates ffprobe return codes
  - Checks for stderr output
  - Handles timeout exceptions explicitly
  - Returns formatted duration (HH:MM:SS or MM:SS)

### Error Handling
```python
# Handles multiple error scenarios:
- File not found
- Invalid duration values (≤ 0)
- ffprobe execution errors
- Timeout after 15 seconds
- ValueError during parsing
- Missing ffprobe installation
```

---

## 🛡️ FloodWait Error Handling

### What's New
- **Automatic retry** after FloodWait errors
- **Smart sleep duration** - Uses Telegram-provided wait time
- **Comprehensive coverage** - Applied to all Telegram API calls
- **Type-safe implementation** - Properly handles fw.value types

### Implementation Details

#### Files Modified
1. **`Jav/processors/video_processor.py`**
   - `safe_edit()` function - Message editing with FloodWait handling
   - `post_to_main_channel()` - Photo/message posting with retries
   - Sticker sending with FloodWait handling
   - Reply markup editing with FloodWait handling

2. **`Jav/services/uploader.py`**
   - `upload_file()` - Document upload with FloodWait handling
   - `add_download_button()` - Button addition with FloodWait handling

### Pattern Used
```python
try:
    await telegram_api_call()
except errors.FloodWait as fw:
    wait_time = int(fw.value) if isinstance(fw.value, (int, float)) else 60
    LOG.warning(f"FloodWait: sleeping for {wait_time} seconds")
    await asyncio.sleep(float(wait_time))
    try:
        await telegram_api_call()  # Retry once
    except Exception:
        pass  # Log and continue
```

### Covered Operations
- ✅ Message editing (`edit_message_text`)
- ✅ Photo sending (`send_photo`)
- ✅ Document uploading (`send_document`)
- ✅ Message sending (`send_message`)
- ✅ Sticker sending (`send_sticker`)
- ✅ Reply markup editing (`edit_message_reply_markup`)
- ✅ Download button addition

---

## 📦 Dependencies

### Already Installed
- `kurigram` (Pyrogram wrapper)
- `requests`
- `html-telegraph-poster`
- `lxml_html_clean`

### Required System Tools
- `ffmpeg` - For video processing
- `ffprobe` - For duration extraction

---

## 🔧 Configuration

No additional configuration required! All features work with existing settings.

### Optional Settings
You can customize Telegraph preview generation:
```python
# In video_processor.py, line ~368
telegraph_url = await create_telegraph_preview_async(
    video_path=video_path,
    title=title,
    description=f"Preview for {title}",
    num_screenshots=8  # Change from default 6
)
```

---

## 📊 Benefits

### Performance
- ✅ Reduced API errors with FloodWait handling
- ✅ Improved success rate with retry logic
- ✅ Better resource cleanup with error handling

### User Experience
- ✅ Video previews on Telegraph for easy sharing
- ✅ More engaging AI-generated captions
- ✅ Accurate video duration display
- ✅ Fewer failed uploads due to rate limits

### Reliability
- ✅ Graceful degradation when services fail
- ✅ Comprehensive error logging
- ✅ Automatic retry mechanisms
- ✅ Type-safe error handling

---

## 🚀 Future Enhancements

Potential improvements for consideration:
1. Configurable retry attempts via environment variables
2. Telegraph preview caching to avoid regeneration
3. Advanced AI caption customization
4. Duration extraction for audio files
5. Rate limit prediction and preemptive throttling

---

## 📝 Testing Recommendations

### Test Telegraph Preview
1. Process a video through the bot
2. Check logs for "Creating Telegraph preview" message
3. Verify Telegraph URL in caption
4. Click preview link to see screenshots

### Test FloodWait Handling
1. Send multiple messages rapidly
2. Monitor logs for "FloodWait" warnings
3. Verify automatic retry after sleep
4. Confirm successful operation after retry

### Test AI Caption
1. Process video with various titles
2. Check AI-generated descriptions
3. Verify fallback descriptions work
4. Test with AI service unavailable

### Test Duration Extraction
1. Process videos of various lengths
2. Verify duration format (HH:MM:SS or MM:SS)
3. Check logs for extraction errors
4. Test with corrupted video files

---

## 🐛 Troubleshooting

### Telegraph Preview Issues
- **No screenshots**: Verify ffmpeg is installed
- **Upload fails**: Check internet connection
- **Invalid URL**: Verify Telegraph service is accessible

### FloodWait Issues
- **Still getting errors**: Check if retry logic is executing
- **Long wait times**: Normal for heavy usage, Telegram-imposed
- **Multiple retries**: May indicate rate limit issues

### AI Caption Issues
- **Generic captions**: AI service may be down, using fallback
- **Timeout errors**: Increase timeout parameter
- **No captions**: Check API endpoint availability

### Duration Extraction Issues
- **"Unknown" duration**: Verify ffprobe is installed
- **Incorrect duration**: Check video file integrity
- **Timeout errors**: Increase timeout for large files

---

## 📞 Support

For issues or questions:
1. Check logs in console/log files
2. Verify all dependencies are installed
3. Test system tools (ffmpeg, ffprobe)
4. Review error messages carefully

---

**Version**: 1.0.0  
**Last Updated**: 2025-10-05  
**Maintained By**: Auto-Jav Development Team
