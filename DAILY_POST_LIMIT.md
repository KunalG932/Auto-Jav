# 📅 Daily Post Limit System

## ✅ Implementation Complete!

The bot now posts only **2-3 videos per day** (configurable) instead of posting everything at once from the API.

---

## 🎯 Features Added

### 1. **Daily Post Limit**
- Configurable via `MAX_POSTS_PER_DAY` in `.env` (default: 3)
- Automatically resets at midnight
- Tracks posts made today

### 2. **Queue System**
- Unposted items are automatically added to a queue
- Queue processes oldest items first (FIFO)
- Queue persists in MongoDB

### 3. **New Commands**

#### `/queue` - Show Queue Status
```
📊 Queue & Daily Limit Status

📅 Today's Posts: 2/3
⏳ Remaining Today: 1
📦 Queue Size: 15 pending
✅ Processed Total: 47

📋 Next in Queue:
1. Movie Title 1...
2. Movie Title 2...
3. Movie Title 3...
4. Movie Title 4...
5. Movie Title 5...

...and 10 more items

🔄 Check Interval: Every 600s
```

#### `/resources` - Show System Resources
```
💻 System Resources

🖥️ CPU Usage: 15.2%
🧠 RAM: 2.45GB / 8.00GB (30.6%)
💾 Disk: 45.3GB / 100.0GB (45.3%)
📁 Free Space: 54.7GB

📂 Storage Breakdown:
├ Downloads: 2.35GB
└ Encode: 1.12GB

📊 Database Stats:
├ Total Files: 127
├ Total Users: 45
├ Queue Items: 15
└ Failed Downloads: 3

⏰ Updated: 2025-10-08 14:35:22
```

---

## 📋 How It Works

### Daily Flow:

```
Day 1 - 10:00 AM:
├─ API fetches 10 new items
├─ Post 1: ✅ Posted to channel
├─ Post 2: ✅ Posted to channel  
├─ Post 3: ✅ Posted to channel
├─ Posts 4-10: ⏸️ Added to queue
└─ Daily limit reached: 3/3 posts

Day 1 - 10:10 AM (next check):
├─ Daily limit still reached
└─ Waiting for tomorrow...

Day 2 - 12:00 AM (midnight):
├─ Counter resets: 0/3 posts
└─ Queue still has 7 items

Day 2 - 10:00 AM:
├─ API fetches 5 new items
├─ New item 1: ✅ Posted
├─ New item 2: ✅ Posted
├─ New item 3: ✅ Posted
├─ New items 4-5: ⏸️ Added to queue
└─ Daily limit reached: 3/3 posts

Day 3 - 12:00 AM:
├─ Counter resets: 0/3 posts
└─ Queue now has 9 items (7 + 2)

Day 3 - 10:00 AM:
├─ No new items from API
├─ Queue item 1: ✅ Posted
├─ Queue item 2: ✅ Posted
├─ Queue item 3: ✅ Posted
└─ Daily limit reached: 3/3 posts
```

---

## ⚙️ Configuration

### `.env` file:
```env
# Daily post limit (2-3 posts per day)
MAX_POSTS_PER_DAY=3
```

**Recommended values:**
- `2` = 2 posts per day
- `3` = 3 posts per day (default)
- `5` = 5 posts per day (if you want more)

---

## 🗄️ Database Collections

### New Collection: `pending_queue`
Stores items that couldn't be posted due to daily limit:

```json
{
  "_id": "...",
  "hash": "abc123...",
  "item_data": { /* full item data */ },
  "added_at": "2025-10-08T10:15:30",
  "status": "pending",
  "processed_at": null
}
```

**Status values:**
- `pending` - Waiting to be processed
- `processed` - Already posted

---

## 📊 Resource Monitoring

The `/resources` command shows:

### System Resources:
- **CPU Usage**: Real-time CPU percentage
- **RAM**: Used/Total memory
- **Disk**: Used/Total/Free disk space

### Storage Breakdown:
- **Downloads folder**: Size of `./downloads`
- **Encode folder**: Size of `./encode`

### Database Stats:
- **Total Files**: Count of uploaded files
- **Total Users**: Count of bot users
- **Queue Items**: Pending items in queue
- **Failed Downloads**: Count of failed items

---

## 🔧 Commands Summary

| Command | Description | Access |
|---------|-------------|--------|
| `/queue` | Show queue status and daily post limits | Owner only |
| `/resources` | Show system resource usage | Owner only |
| `/stats` | Show bot statistics | Owner only |
| `/status` | Show worker status | Owner only |
| `/failed` | Manage failed downloads | Owner only |
| `/broadcast` | Broadcast message to all users | Owner only |

---

## 💾 Storage Usage

### Typical Usage:
- **Each video**: ~500MB - 2GB
- **Encoded video**: ~200MB - 800MB (40-50% smaller)
- **Downloads + Encode**: Can use 5-10GB temporarily
- **MongoDB**: Minimal (~few MB for metadata)

### Cleanup:
Files are automatically cleaned up after:
1. ✅ Upload complete
2. ✅ Encoding complete
3. ⏰ User receives file (deleted after 3 minutes)

---

## 🚀 Benefits

✅ **Controlled posting** - Only 2-3 posts per day
✅ **No content loss** - Unposted items stored in queue
✅ **Fair distribution** - Oldest items processed first
✅ **Automatic reset** - Counter resets at midnight
✅ **Queue management** - See what's pending with `/queue`
✅ **Resource monitoring** - Track storage and system usage
✅ **Flexible** - Change `MAX_POSTS_PER_DAY` anytime

---

## 📦 Installation

1. **Install psutil** (for resource monitoring):
```bash
pip install psutil
```

2. **Update .env**:
```env
MAX_POSTS_PER_DAY=3
```

3. **Restart bot**:
```bash
python -m Jav
```

---

## 🐛 Troubleshooting

### Issue: Bot not posting anything
- Check `/queue` - items might be in queue
- Check daily limit: `MAX_POSTS_PER_DAY` in `.env`
- Check if daily limit reached: `/queue` shows posts today

### Issue: Resource command fails
- Install psutil: `pip install psutil`
- Restart bot

### Issue: Queue keeps growing
- Increase `MAX_POSTS_PER_DAY` in `.env`
- Or clear queue manually via MongoDB

---

## 📝 Notes

- Queue is persistent (stored in MongoDB)
- Items stay in queue until posted
- Daily counter resets at midnight (system time)
- Resource monitoring requires `psutil` module
- All commands are owner-only except `/start`

---

**Enjoy your controlled daily posting! 🎉**
