import logging
from typing import Optional, Dict, Any
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from .config import SETTINGS

LOG = logging.getLogger("AABv2")

try:
    client = MongoClient(SETTINGS.mongo_uri, server_api=ServerApi('1'))
    db = client.get_database('nanosbotdb')
    last_added = db.get_collection('last_added')
    files = db.get_collection('files')
    worker = db.get_collection('worker')
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
