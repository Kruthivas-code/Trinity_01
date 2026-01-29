"""
Adapter factory for distributed services.
Provides easy switching between MongoDB and Redis backends.

Usage:
    from adapters import get_presence_adapter, get_lock_adapter, get_pubsub_adapter
    
    presence = get_presence_adapter()
    lock = get_lock_adapter()
    pubsub = get_pubsub_adapter()

Configuration:
    Set environment variable ADAPTER_BACKEND to 'mongodb' or 'redis'
    Default is 'mongodb'
    
    For Redis, also set:
    - REDIS_URL: Redis connection URL (e.g., redis://localhost:6379)
"""

import os
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
    logger.info("[ADAPTERS] Database configured")


def get_adapter_backend() -> str:
    """Get the configured adapter backend"""
    return os.environ.get("ADAPTER_BACKEND", "mongodb").lower()


def get_presence_adapter() -> PresenceAdapter:
    """
    Get the presence adapter singleton.
    Creates adapter on first call based on ADAPTER_BACKEND setting.
    """
    global _presence_adapter
    
    if _presence_adapter is None:
        backend = get_adapter_backend()
        
        if backend == "redis":
            # Redis implementation (future)
            # from .redis_adapter import RedisPresenceAdapter
            # _presence_adapter = RedisPresenceAdapter(os.environ.get("REDIS_URL"))
            raise NotImplementedError(
                "Redis adapter not implemented yet. "
                "Set ADAPTER_BACKEND=mongodb or implement RedisPresenceAdapter"
            )
        else:
            # MongoDB implementation (default)
            if _db is None:
                raise RuntimeError("Database not configured. Call set_database() first.")
            _presence_adapter = MongoPresenceAdapter(_db)
            logger.info("[ADAPTERS] Using MongoDB presence adapter")
    
    return _presence_adapter


def get_lock_adapter() -> LockAdapter:
    """
    Get the distributed lock adapter singleton.
    Creates adapter on first call based on ADAPTER_BACKEND setting.
    """
    global _lock_adapter
    
    if _lock_adapter is None:
        backend = get_adapter_backend()
        
        if backend == "redis":
            # Redis implementation (future)
            # from .redis_adapter import RedisLockAdapter
            # _lock_adapter = RedisLockAdapter(os.environ.get("REDIS_URL"))
            raise NotImplementedError(
                "Redis adapter not implemented yet. "
                "Set ADAPTER_BACKEND=mongodb or implement RedisLockAdapter"
            )
        else:
            # MongoDB implementation (default)
            if _db is None:
                raise RuntimeError("Database not configured. Call set_database() first.")
            _lock_adapter = MongoLockAdapter(_db)
            logger.info("[ADAPTERS] Using MongoDB lock adapter")
    
    return _lock_adapter


def get_pubsub_adapter(use_polling: bool = False) -> PubSubAdapter:
    """
    Get the pub/sub adapter singleton.
    Creates adapter on first call based on ADAPTER_BACKEND setting.
    
    Args:
        use_polling: For MongoDB, use polling instead of change streams
                    (required if not using replica set)
    """
    global _pubsub_adapter
    
    if _pubsub_adapter is None:
        backend = get_adapter_backend()
        
        if backend == "redis":
            # Redis implementation (future)
            # from .redis_adapter import RedisPubSubAdapter
            # _pubsub_adapter = RedisPubSubAdapter(os.environ.get("REDIS_URL"))
            raise NotImplementedError(
                "Redis adapter not implemented yet. "
                "Set ADAPTER_BACKEND=mongodb or implement RedisPubSubAdapter"
            )
        else:
            # MongoDB implementation (default)
            if _db is None:
                raise RuntimeError("Database not configured. Call set_database() first.")
            _pubsub_adapter = MongoPubSubAdapter(_db, use_polling=use_polling)
            logger.info(f"[ADAPTERS] Using MongoDB pubsub adapter (polling={use_polling})")
    
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
    'get_adapter_backend',
    'reset_adapters'
]
