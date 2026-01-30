"""
MongoDB Adapter Factory for distributed services.
Provides presence tracking, distributed locking, and pub/sub messaging.

Usage:
    from adapters import get_presence_adapter, get_lock_adapter, get_pubsub_adapter
    
    presence = get_presence_adapter()
    lock = get_lock_adapter()
    pubsub = get_pubsub_adapter()

Configuration:
    Call set_database(db) before using adapters.
"""

import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from .base import PresenceAdapter, LockAdapter, PubSubAdapter
from .mongodb_adapter import MongoPresenceAdapter, MongoLockAdapter, MongoPubSubAdapter

logger = logging.getLogger(__name__)

# Global adapter instances (singletons)
_presence_adapter: Optional[PresenceAdapter] = None
_lock_adapter: Optional[LockAdapter] = None
_pubsub_adapter: Optional[PubSubAdapter] = None
_db: Optional[AsyncIOMotorDatabase] = None


def set_database(db: AsyncIOMotorDatabase):
    """Set the database instance for MongoDB adapters"""
    global _db
    _db = db
    logger.info("[ADAPTERS] MongoDB database configured")


def get_presence_adapter() -> PresenceAdapter:
    """
    Get the presence adapter singleton.
    Creates adapter on first call.
    """
    global _presence_adapter
    
    if _presence_adapter is None:
        if _db is None:
            raise RuntimeError("Database not configured. Call set_database() first.")
        _presence_adapter = MongoPresenceAdapter(_db)
        logger.info("[ADAPTERS] Using MongoDB presence adapter")
    
    return _presence_adapter


def get_lock_adapter() -> LockAdapter:
    """
    Get the distributed lock adapter singleton.
    Creates adapter on first call.
    """
    global _lock_adapter
    
    if _lock_adapter is None:
        if _db is None:
            raise RuntimeError("Database not configured. Call set_database() first.")
        _lock_adapter = MongoLockAdapter(_db)
        logger.info("[ADAPTERS] Using MongoDB lock adapter")
    
    return _lock_adapter


def get_pubsub_adapter() -> PubSubAdapter:
    """
    Get the pub/sub adapter singleton.
    Creates adapter on first call.
    
    Uses MongoDB change streams if available (replica set),
    otherwise falls back to polling mode.
    """
    global _pubsub_adapter
    
    if _pubsub_adapter is None:
        if _db is None:
            raise RuntimeError("Database not configured. Call set_database() first.")
        # Start with change streams, will auto-fallback to polling if not available
        _pubsub_adapter = MongoPubSubAdapter(_db, use_polling=False)
        logger.info("[ADAPTERS] Using MongoDB pubsub adapter")
    
    return _pubsub_adapter


def reset_adapters():
    """Reset all adapter singletons (useful for testing)"""
    global _presence_adapter, _lock_adapter, _pubsub_adapter
    _presence_adapter = None
    _lock_adapter = None
    _pubsub_adapter = None
    logger.info("[ADAPTERS] All adapters reset")


# Convenience exports
__all__ = [
    'PresenceAdapter',
    'LockAdapter', 
    'PubSubAdapter',
    'set_database',
    'get_presence_adapter',
    'get_lock_adapter',
    'get_pubsub_adapter',
    'reset_adapters'
]
