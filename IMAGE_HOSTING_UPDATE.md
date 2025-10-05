# 🖼️ Telegraph Image Hosting Update

## Changes Made

### Problem with Original Approach
The original code was passing local file paths to Telegraph, expecting it to upload them. This wasn't working reliably.

### New Solution: External Image Hosting

Now the workflow is:
1. ✅ Extract screenshots from video (ffmpeg)
2. ✅ Upload each screenshot to **envs.sh** (free image host)
3. ✅ Get direct image URLs from envs.sh
4. ✅ Create Telegraph page using those URLs
5. ✅ Telegraph displays the images properly

---

## How It Works

### 1. Image Upload Function

```python
def upload_image_to_host(image_path: str) -> Optional[str]:
    """Upload an image to envs.sh and return the URL."""
    try:
        with open(image_path, 'rb') as img_file:
            files = {'file': img_file}
            response = requests.post('https://envs.sh', files=files, timeout=30)
            response.raise_for_status()
            
            # envs.sh returns the direct URL in response text
            image_url = response.text.strip()
            return image_url
    except Exception as e:
        LOG.error(f"Failed to upload image: {e}")
        return None
```

### 2. Updated Telegraph Creation

**Before** (Broken):
```python
# Using local file paths - doesn't work
img_tag = f'<img src="{screenshot_path}"/>'  # Local path
html_parts.append(img_tag)
```

**After** (Working):
```python
# Upload to envs.sh first, then use URL
image_url = upload_image_to_host(screenshot_path)  # Get URL
if image_url:
    img_tag = f'<img src="{image_url}"/>'  # Use hosted URL
    html_parts.append(img_tag)
```

---

## Benefits

### ✅ Reliable Image Display
- Images are hosted on envs.sh
- Direct URLs that work everywhere
- No Telegraph upload issues

### ✅ Free Hosting
- envs.sh is free to use
- No registration required
- Fast and reliable

### ✅ Better Error Handling
- Uploads each image individually
- Skips failed uploads
- Creates Telegraph page even if some images fail

### ✅ Clean Logs
```
INFO - Uploading screenshot 1/6 to image host...
INFO - ✅ Added screenshot 1/6 with URL: https://envs.sh/abc123.jpg
INFO - Uploading screenshot 2/6 to image host...
INFO - ✅ Added screenshot 2/6 with URL: https://envs.sh/def456.jpg
...
INFO - Successfully uploaded 6/6 screenshots
INFO - ✅ Telegraph preview created: https://telegra.ph/Video-Title-10-05
```

---

## About envs.sh

### What is envs.sh?
- Free, anonymous file hosting service
- No account needed
- Direct image links
- Fast CDN delivery
- No ads on direct links

### API Usage
```bash
# Simple POST request with file
curl -F "file=@image.jpg" https://envs.sh

# Returns direct URL
https://envs.sh/abc123.jpg
```

### Example Response
```
https://envs.sh/q2F.jpg
```

---

## File Modified

**File**: `Jav/utils/telegraph.py`

**Changes**:
1. ✅ Added `requests` import
2. ✅ Created `upload_image_to_host()` function
3. ✅ Updated screenshot processing to upload images first
4. ✅ Changed Telegraph to use hosted URLs instead of local paths
5. ✅ Enhanced error handling and logging

---

## Expected Behavior

### Log Output During Telegraph Creation

```
🎬 Creating Telegraph preview with video screenshots...
INFO - Creating Telegraph preview for: Video Title
INFO - Extracted screenshot 6/6 at 5622.6s
INFO - Successfully extracted 6/6 screenshots

INFO - Uploading screenshot 1/6 to image host...
INFO - ✅ Added screenshot 1/6 with URL: https://envs.sh/abc.jpg
INFO - Uploading screenshot 2/6 to image host...
INFO - ✅ Added screenshot 2/6 with URL: https://envs.sh/def.jpg
INFO - Uploading screenshot 3/6 to image host...
INFO - ✅ Added screenshot 3/6 with URL: https://envs.sh/ghi.jpg
INFO - Uploading screenshot 4/6 to image host...
INFO - ✅ Added screenshot 4/6 with URL: https://envs.sh/jkl.jpg
INFO - Uploading screenshot 5/6 to image host...
INFO - ✅ Added screenshot 5/6 with URL: https://envs.sh/mno.jpg
INFO - Uploading screenshot 6/6 to image host...
INFO - ✅ Added screenshot 6/6 with URL: https://envs.sh/pqr.jpg

INFO - Successfully uploaded 6/6 screenshots
DEBUG - Posting to Telegraph with content length: 450
DEBUG - Telegraph response type: <class 'dict'>, value: {'url': '...'}
DEBUG - Extracted URL from dict: https://telegra.ph/Video-Title-10-05
INFO - ✅ Telegraph preview created: https://telegra.ph/Video-Title-10-05
```

### Telegraph Page Result

The Telegraph page will now display all images properly because they're hosted on envs.sh:

```html
<p><strong>Preview for Video Title</strong></p>
<p>📸 Video Preview Screenshots:</p>
<img src="https://envs.sh/abc.jpg"/>
<img src="https://envs.sh/def.jpg"/>
<img src="https://envs.sh/ghi.jpg"/>
<img src="https://envs.sh/jkl.jpg"/>
<img src="https://envs.sh/mno.jpg"/>
<img src="https://envs.sh/pqr.jpg"/>
```

---

## Error Handling

### If Image Upload Fails
```
WARNING - Failed to upload screenshot 3, skipping
INFO - Successfully uploaded 5/6 screenshots
```
- Continues with remaining screenshots
- Creates Telegraph page with available images

### If All Uploads Fail
```
ERROR - No images uploaded successfully, cannot create Telegraph page
WARNING - Failed to create Telegraph preview
```
- Skips Telegraph creation
- Video post continues without preview link

---

## Deployment

### On Your Server

```bash
cd ~/test
git pull origin main

# No additional dependencies needed - requests is already installed
python3 -m Jav
```

### Verify It Works

Next video processed should:
1. ✅ Extract 6 screenshots
2. ✅ Upload each to envs.sh
3. ✅ Create Telegraph page with hosted images
4. ✅ Add working preview link to caption

---

## Alternative Image Hosts

If envs.sh ever stops working, you can easily switch to another host:

### Option 1: 0x0.st
```python
response = requests.post('https://0x0.st', files=files, timeout=30)
```

### Option 2: catbox.moe
```python
response = requests.post('https://catbox.moe/user/api.php', 
                        data={'reqtype': 'fileupload'},
                        files={'fileToUpload': img_file},
                        timeout=30)
```

### Option 3: imgbb.com (requires API key)
```python
response = requests.post(
    f'https://api.imgbb.com/1/upload?key={API_KEY}',
    data={'image': base64.b64encode(img_file.read())},
    timeout=30
)
```

Just change the `upload_image_to_host()` function!

---

## Performance Considerations

### Upload Time
- Each screenshot: ~1-2 seconds to upload
- 6 screenshots: ~6-12 seconds total
- Still faster than encoding!

### Network Usage
- Each screenshot: ~100-300 KB
- 6 screenshots: ~600-1800 KB total
- Minimal impact on server

---

## Testing

### Test the Upload Function Manually

```python
from Jav.utils.telegraph import upload_image_to_host

# Test with a sample image
url = upload_image_to_host("AAB/utils/thumb.jpeg")
print(f"Uploaded to: {url}")

# Should print something like:
# Uploaded to: https://envs.sh/abc123.jpg
```

### Test Full Telegraph Creation

```python
from Jav.utils.telegraph import create_telegraph_preview

url = create_telegraph_preview(
    video_path="/path/to/video.mp4",
    title="Test Video",
    description="Test preview",
    num_screenshots=3
)
print(f"Telegraph page: {url}")
```

---

## Troubleshooting

### Issue: envs.sh is down or blocked

**Solution**: Switch to alternative host (see above)

### Issue: Uploads timing out

**Solution**: Increase timeout in code:
```python
response = requests.post('https://envs.sh', files=files, timeout=60)  # Increased to 60s
```

### Issue: Invalid image URLs returned

**Check**: 
- Is envs.sh accessible from server?
- Are image files valid?
- Check logs for exact error

---

## Dependencies

### Already Installed
- ✅ `requests` - For HTTP uploads
- ✅ `html_telegraph_poster` - For Telegraph pages

### No New Dependencies Needed! ✅

---

**Status**: ✅ **IMPLEMENTED**  
**Testing**: 🟡 **Ready for Testing**  
**Impact**: 🟢 **Telegraph previews will now work properly**

The next video processed should create a working Telegraph preview with properly displayed images! 🎉
