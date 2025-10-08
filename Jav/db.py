import logging
from typing import Optional, Dict, Any
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from .config import SETTINGS

LOG = logging.getLogger("Jav")

try:
    client = MongoClient(SETTINGS.mongo_uri, server_api=ServerApi('1'))
    db = client.get_database('kunalsdb')
    last_added = db.get_collection('last_added')
    files = db.get_collection('files')
    worker = db.get_collection('worker')
    users = db.get_collection('users')
    failed_downloads = db.get_collection('failed_downloads')
    pending_queue = db.get_collection('pending_queue')
except Exception as e:
    LOG.exception(f"Failed to connect to MongoDB: {e}")
    raise

def get_last_hash() -> Optional[str]:
    
    doc = last_added.find_one({'_id': 1})
    return doc.get('hash') if doc else None

def set_last_hash(h: str) -> None:
    
    last_added.update_one({'_id': 1}, {'$set': {'hash': h}}, upsert=True)
    LOG.debug(f"Last hash updated to {h}")

def add_file_record(name: str, file_hash: str, message_id: int) -> None:
    from datetime import datetime
    
    files.insert_one({
        "name": name,
        "hash": file_hash,
        "message_id": message_id,
        "upload_date": datetime.now()
    })
    LOG.debug(f"Added file record: {name} ({file_hash})")

def get_file_by_hash(h: str) -> Optional[Dict[str, Any]]:
    
    return files.find_one({"hash": h})

def is_working() -> bool:
    
    doc = worker.find_one({'_id': 1})
    if not doc:
        worker.insert_one({'_id': 1, 'working': False})
        return False
    return bool(doc.get('working', False))

def set_working(flag: bool) -> None:
    
    worker.update_one({'_id': 1}, {'$set': {'working': flag}}, upsert=True)
    LOG.debug(f"Worker state set to {flag}")

def add_user(user_id: int, name: str, username: Optional[str] = None) -> bool:
    from datetime import datetime
    
    existing = users.find_one({'user_id': user_id})
    if existing:
        return False
    
    users.insert_one({
        'user_id': user_id,
        'name': name,
        'username': username,
        'start_time': datetime.now(),
        'start_date': datetime.now().strftime('%Y-%m-%d')
    })
    LOG.info(f"New user added: {name} ({user_id})")
    return True

def get_total_users() -> int:
    try:
        return users.count_documents({})
    except Exception as e:
        LOG.error(f"Error getting total users: {e}")
        return 0

def get_all_user_ids() -> list:
    try:
        return [doc['user_id'] for doc in users.find({}, {'user_id': 1})]
    except Exception as e:
        LOG.error(f"Error getting user IDs: {e}")
        return []

def add_failed_download(title: str, magnet: str, reason: str = "Download failed") -> None:
    from datetime import datetime
    
    try:
        failed_downloads.insert_one({
            'title': title,
            'magnet': magnet,
            'reason': reason,
            'failed_at': datetime.now(),
            'failed_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        LOG.info(f"❌ Marked as failed download: {title}")
    except Exception as e:
        LOG.error(f"Error adding failed download record: {e}")

def is_failed_download(title: str) -> bool:
    try:
        existing = failed_downloads.find_one({'title': title})
        if existing:
            LOG.info(f"⚠️ Skipping previously failed download: {title}")
            return True
        return False
    except Exception as e:
        LOG.error(f"Error checking failed downloads: {e}")
        return False

def remove_failed_download(title: str) -> None:
    try:
        result = failed_downloads.delete_one({'title': title})
        if result.deleted_count > 0:
            LOG.info(f"🔄 Removed from failed downloads: {title}")
    except Exception as e:
        LOG.error(f"Error removing failed download: {e}")

def get_posts_today() -> int:
    from datetime import datetime
    
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    count = files.count_documents({
        'upload_date': {'$gte': today_start}
    })
    return count

def reset_daily_post_count():
    from datetime import datetime
    
    today = datetime.now().strftime('%Y-%m-%d')
    worker.update_one(
        {'_id': 1},
        {'$set': {'last_reset_date': today, 'posts_today': 0}},
        upsert=True
    )
    LOG.info("📅 Daily post count reset")

def can_post_today() -> bool:
    from datetime import datetime
    
    today = datetime.now().strftime('%Y-%m-%d')
    state = worker.find_one({'_id': 1})
    
    if not state or state.get('last_reset_date') != today:
        reset_daily_post_count()
        return True
    
    posts_today = get_posts_today()
    max_posts = SETTINGS.max_posts_per_day
    
    can_post = posts_today < max_posts
    if not can_post:
        LOG.info(f"⏸️ Daily limit reached: {posts_today}/{max_posts}")
    return can_post

def add_to_queue(item: Dict[str, Any]) -> bool:
    from datetime import datetime
    
    title = item.get('title', 'Unknown')
    item_hash = item.get('hash')
    
    if not item_hash:
        LOG.warning(f"Cannot add to queue - no hash: {title}")
        return False
    
    existing = pending_queue.find_one({'hash': item_hash})
    if existing:
        LOG.debug(f"Item already in queue: {title[:40]}")
        return False
    
    queue_item = {
        'hash': item_hash,
        'item_data': item,
        'added_at': datetime.now(),
        'status': 'pending'
    }
    
    pending_queue.insert_one(queue_item)
    LOG.info(f"📦 Added to queue: {title[:50]}")
    return True

def get_next_queue_item() -> Optional[Dict[str, Any]]:
    queue_item = pending_queue.find_one(
        {'status': 'pending'},
        sort=[('added_at', 1)]
    )
    
    if queue_item:
        return queue_item.get('item_data')
    
    return None

def mark_queue_item_processed(item_hash: str):
    from datetime import datetime
    
    pending_queue.update_one(
        {'hash': item_hash},
        {'$set': {'status': 'processed', 'processed_at': datetime.now()}}
    )
    LOG.debug(f"✅ Marked queue item as processed: {item_hash}")

def get_queue_size() -> int:
    return pending_queue.count_documents({'status': 'pending'})

def get_queue_stats() -> Dict[str, Any]:
    pending = pending_queue.count_documents({'status': 'pending'})
    processed = pending_queue.count_documents({'status': 'processed'})
    
    return {
        'pending': pending,
        'processed': processed,
        'total': pending + processed
    }

