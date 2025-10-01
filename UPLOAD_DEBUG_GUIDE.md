# 🔍 Upload Issue Debugging Guide

## Problem
File downloads successfully (100%) but bot sends "No file uploaded" message.

## Current Logs Pattern
```
✅ 100.00% down:1007.0 kB/s
✅ Download completed: ./downloads/[file].mkv
🔄 Using magnet link (← NEXT ITEM, should upload first!)
⏱️ Waiting for torrent metadata... (← stuck here)
```

## What SHOULD Happen
```
✅ 100.00% down:1007.0 kB/s
✅ Download completed: ./downloads/[file].mkv
📤 Starting upload...
⬆️ Uploading file to Telegram...
✅ Successfully uploaded
📱 Posted to main channel
```

## Enhanced Logging Added

### New Log Messages to Watch For:

1. **After Download:**
   ```
   ✅ Download successful, starting post-processing for: [path]
   ```

2. **File Size Check:**
   ```
   File size: X bytes (Y GB)
   File <=2GB, uploading as single file
   OR
   File >2GB, will split into parts
   ```

3. **Upload Start:**
   ```
   Starting post to main channel...
   ```

4. **Upload Success:**
   ```
   ✅ Successfully uploaded and posted: [title]
   ```

5. **Upload Failure:**
   ```
   ❌ Upload failed for: [title]
   ```

6. **Errors:**
   ```
   ❌ Error during upload process: [details with full traceback]
   ```

## Next Steps for Debugging

### 1. Run Bot and Watch Logs
```powershell
cd "c:\Users\kunal\OneDrive\Desktop\Auto-Jav"
python -m AABv2
```

### 2. Look for These Specific Messages

**If you see:**
```
✅ Download successful, starting post-processing
```
✅ Good! Download is working

**If you DON'T see:**
```
File size: X bytes
```
❌ Problem: File size check is failing

**If you see:**
```
❌ Error during upload process
```
❌ Problem: Upload code is throwing an exception

**If upload never starts:**
❌ Problem: Code is not reaching upload block

### 3. Check for Exception Traces

With the new logging, any error will show full traceback:
```
ERROR - ❌ Error during upload process for [title]: [error]
Traceback (most recent call last):
  ...
```

This will tell us EXACTLY what's failing.

## Possible Issues

### Issue 1: File Client Not Available
```python
# If file_client is None, uploads fail
if not file_client:
    LOG.error("file_client is None!")
```

**Check:** Look for this in logs at startup:
```
✅ Command handlers registered on file client
```

If missing, file_client didn't start properly.

### Issue 2: FILES_CHANNEL Not Configured
```python
# Need valid FILES_CHANNEL to upload
if not SETTINGS.files_channel:
    LOG.error("FILES_CHANNEL not set!")
```

**Check `.env`:**
```env
FILES_CHANNEL=123456789  # Must be set
```

### Issue 3: Upload Timeout
Telegram uploads can take time for large files.

**Check:** If logs stop at "Uploading", might be timeout.

### Issue 4: Permission Issues
Bot doesn't have permission to post in files_channel.

**Check:** Bot must be admin in FILES_CHANNEL.

## Test Commands

### 1. Test API Connection
```powershell
python test_api.py
```

### 2. Check Bot Status
Send to bot in Telegram:
```
/status
```

### 3. Get Logs
Send to bot in Telegram:
```
/logs
```

## Manual Verification

### Check Downloads Folder
```powershell
ls "c:\Users\kunal\OneDrive\Desktop\Auto-Jav\downloads"
```

**If files exist but not uploaded:**
- ✅ Download works
- ❌ Upload blocked

### Check Database
Files should be recorded in MongoDB after upload.

If download completes but DB has no record:
- Upload never happened

## Quick Fix Checklist

- [ ] Bot has admin rights in FILES_CHANNEL
- [ ] FILES_CHANNEL is set in .env
- [ ] file_client starts successfully (check logs)
- [ ] No firewall blocking Telegram uploads
- [ ] Enough disk space for downloads
- [ ] MongoDB is connected

## What to Send for Help

If issue persists, provide:

1. **Full logs from startup to "No file uploaded":**
   ```powershell
   Get-Content logging_v2.txt | Select-Object -Last 100
   ```

2. **Bot status output:**
   - Send `/status` to bot
   - Share screenshot

3. **Environment check:**
   ```powershell
   Get-Content .env
   ```
   (Hide sensitive values!)

4. **Downloads folder:**
   ```powershell
   ls downloads
   ```

## Expected Log Flow

Here's what you should see in order:

```
1. 🎬 Starting download process for: [title]
2. 📥 Downloading: [title]
3. [Progress updates: 0% -> 100%]
4. ✅ Download completed: [path]
5. ✅ Download successful, starting post-processing for: [path]
6. File size: X bytes (Y GB)
7. File <=2GB, uploading as single file
8. Upload completed: uploaded=True
9. Starting post to main channel...
10. ✅ Successfully uploaded and posted: [title]
11. 📤 Download process completed: uploaded=True
12. ✅ [link to channel]
```

If the flow stops at any point, that's where the issue is!

## Emergency Recovery

### If downloads pile up but don't upload:

1. **Stop bot** (Ctrl+C)

2. **Check what's in downloads folder:**
   ```powershell
   ls downloads
   ```

3. **Clear old downloads:**
   ```powershell
   Remove-Item downloads\* -Force
   ```

4. **Restart bot**

5. **Monitor logs closely**

---

**Next:** Run the bot and share the logs from a complete cycle (download start -> end).
