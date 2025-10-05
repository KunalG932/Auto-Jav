import logging
from typing import Optional, Dict, Any
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from .config import SETTINGS

LOG = logging.getLogger("Jav")

try:
    client = MongoClient(SETTINGS.mongo_uri, server_api=ServerApi('1'))
    db = client.get_database('kukusdb')
    last_added = db.get_collection('lasqt_added')
    files = db.get_collection('files')
    worker = db.get_collection('worker')
    users = db.get_collection('users')
    failed_downloads = db.get_collection('failed_downloads')
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
    
    files.insert_one({"name": name, "hash": file_hash, "message_id": message_id})
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
    """
    Add a new user to the database if not exists.
    Returns True if user was newly added, False if already exists.
    """
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
    """
    Get total number of users in database.
    """
    try:
        return users.count_documents({})
    except Exception as e:
        LOG.error(f"Error getting total users: {e}")
        return 0

def get_all_user_ids() -> list:
    """
    Get list of all user IDs for broadcasting.
    """
    try:
        return [doc['user_id'] for doc in users.find({}, {'user_id': 1})]
    except Exception as e:
        LOG.error(f"Error getting user IDs: {e}")
        return []

def add_failed_download(title: str, magnet: str, reason: str = "Download failed") -> None:
    """
    Add a failed download record to prevent re-downloading.
    """
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
    """
    Check if a video has previously failed to download.
    Returns True if it has failed before, False otherwise.
    """
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
    """
    Remove a title from failed downloads (in case you want to retry manually).
    """
    try:
        result = failed_downloads.delete_one({'title': title})
        if result.deleted_count > 0:
            LOG.info(f"🔄 Removed from failed downloads: {title}")
    except Exception as e:
        LOG.error(f"Error removing failed download: {e}")
