# 🔧 API Timeout Fix & Improvements

## Problem
```
HTTPSConnectionPool(host='jav-api-w4od.onrender.com', port=443): 
Read timed out. (read timeout=60)
```

**Root Cause:** Render.com free tier services go to sleep after inactivity and take 30-90 seconds to cold start.

## Solution Implemented

### ✅ 1. Increased Timeouts
**Before:**
```python
api_timeout_sec: 60
api_retries: 3
api_backoff_sec: 20
```

**After:**
```python
api_timeout_sec: 120  # 2 minutes base timeout
api_retries: 5        # More retry attempts
api_backoff_sec: 30   # Longer backoff between retries
```

### ✅ 2. Exponential Backoff
Each retry attempt gets progressively longer timeout:
- Attempt 1: 120s timeout, wait 30s on failure
- Attempt 2: 150s timeout, wait 60s on failure
- Attempt 3: 180s timeout, wait 90s on failure
- Attempt 4: 210s timeout, wait 120s on failure
- Attempt 5: 240s timeout (final attempt)

### ✅ 3. API Warm-up
Added `api_health.py` with:
- `ping_api()` - Check if API is alive
- `warm_up_api()` - Pre-warm API before starting worker loop

**When it runs:**
- Once at bot startup
- Pings API to wake it up
- Waits for API to be ready before starting main loop

### ✅ 4. Better Error Handling
```python
# Specific handling for different error types
- Timeout errors → Clear message about cold start
- Connection errors → Retry with backoff
- HTTP errors → Log status code
- Generic errors → Full exception trace
```

### ✅ 5. User-Friendly Logging
```
🏓 Pinging API to check availability...
⏱️ API timeout - service may be cold starting
🔥 Warming up API (attempt 1/2)...
✅ API is alive and responding!
```

## Configuration (Optional)

You can customize these via environment variables:

```bash
# .env file
JAV_API_TIMEOUT_SEC=120      # Base timeout in seconds
JAV_API_RETRIES=5            # Number of retry attempts
JAV_API_BACKOFF_SEC=30       # Base backoff time
```

## How It Works Now

### Bot Startup
```
1. Connect to MongoDB          ✅
2. Start Telegram clients      ✅
3. Register command handlers   ✅
4. Create downloads directory  ✅
5. 🔥 Warm up API             ← NEW!
   - Ping API to wake it up
   - Wait for response
   - Retry if needed
6. Start worker loop          ✅
```

### API Fetch Flow
```
1. First attempt (120s timeout)
   ↓ Timeout
2. Wait 30s, retry (150s timeout)
   ↓ Timeout
3. Wait 60s, retry (180s timeout)
   ↓ Success! ✅
```

## Expected Behavior

### Cold Start Scenario
```
2025-10-01 06:19:18 - INFO - 🔥 Warming up API...
2025-10-01 06:19:18 - INFO - 🏓 Pinging API...
2025-10-01 06:20:48 - WARNING - ⏱️ API timeout - service may be cold starting
2025-10-01 06:20:48 - INFO - Waiting 45s before next attempt...
2025-10-01 06:21:33 - INFO - 🏓 Pinging API (attempt 2/2)...
2025-10-01 06:21:38 - INFO - ✅ API is alive and responding!
2025-10-01 06:21:38 - INFO - 🚀 AABv2 started successfully!
```

### Regular Fetch (After Warm-up)
```
2025-10-01 06:26:38 - INFO - Fetching from API (attempt 1/5, timeout=120s)...
2025-10-01 06:26:42 - INFO - ✅ API fetch successful on attempt 1
2025-10-01 06:26:42 - INFO - Fetched 10 items from API
```

### Failed Fetch (Max Retries)
```
2025-10-01 06:30:00 - INFO - Fetching from API (attempt 1/5, timeout=120s)...
2025-10-01 06:32:00 - WARNING - ⏱️ API timeout (try 1/5): Service may be cold starting
2025-10-01 06:32:00 - INFO - Retrying in 30s with exponential backoff...
2025-10-01 06:32:30 - INFO - Fetching from API (attempt 2/5, timeout=150s)...
... (continues up to 5 attempts)
2025-10-01 06:40:00 - ERROR - ❌ All retries exhausted - API unavailable
2025-10-01 06:40:00 - INFO - No results from feed
```

## Benefits

✅ **Handles cold starts** - API warm-up at startup
✅ **More resilient** - 5 retries with exponential backoff
✅ **Longer timeouts** - Up to 4 minutes total wait time
✅ **Better UX** - Clear emoji-based status messages
✅ **Configurable** - Override via environment variables

## Monitoring

### Check API Status Manually
```python
from AABv2.services.api_health import ping_api

if ping_api():
    print("✅ API is available")
else:
    print("❌ API is not responding")
```

### Check Logs
```bash
# View recent logs
tail -f logging_v2.txt

# Search for API issues
grep "API" logging_v2.txt | tail -20
```

## Troubleshooting

### Still Getting Timeouts?

1. **Check API directly in browser:**
   ```
   https://jav-api-w4od.onrender.com/api/latest?limit=10&sort_by_date=true&translate=true
   ```

2. **Increase timeout further:**
   ```bash
   export JAV_API_TIMEOUT_SEC=180
   export JAV_API_RETRIES=7
   ```

3. **Check network/firewall:**
   ```bash
   curl -v https://jav-api-w4od.onrender.com/api/latest
   ```

4. **Consider upgrading Render tier:**
   - Free tier: Cold starts
   - Paid tier: Always on, no cold starts

## Summary

The API timeout issue is now handled with:
- 🔥 **Warm-up phase** at startup
- ⏱️ **Extended timeouts** (120s → 240s)
- 🔄 **Exponential backoff** (30s → 120s)
- 🎯 **More retries** (3 → 5 attempts)
- 📝 **Clear logging** with emojis

Your bot should now handle API cold starts gracefully! 🎉
