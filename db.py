from pymongo import MongoClient
from pymongo.collection import Collection

from config import (
    MONGODB_URI, DB_NAME,
    TASKS_COLLECTION, SESSIONS_COLLECTION,
    PROFILE_COLLECTION
)

_client_singleton = None

def get_client() -> MongoClient:
    global _client_singleton
    if _client_singleton is None:
        if not MONGODB_URI:
            raise RuntimeError("Missing MONGODB_URI in .env")
        _client_singleton = MongoClient(MONGODB_URI)
    return _client_singleton

def tasks_col() -> Collection:
    c = get_client()
    return c[DB_NAME][TASKS_COLLECTION]

def sessions_col() -> Collection:
    c = get_client()
    return c[DB_NAME][SESSIONS_COLLECTION]

def profiles_col() -> Collection:
    c = get_client()
    return c[DB_NAME][PROFILE_COLLECTION]