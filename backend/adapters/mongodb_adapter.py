"""
MongoDB implementation of distributed adapters.
Uses MongoDB collections with TTL indexes for automatic cleanup.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Callable
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from .base import PresenceAdapter, LockAdapter, PubSubAdapter

logger = logging.getLogger(__name__)


class MongoPresenceAdapter(PresenceAdapter):
    """
    MongoDB-backed presence management.
    
    Collections used:
    - presence_connections: Active user connections
    - presence_locations: User locations (which ticket they're viewing)
    - presence_typing: Typing indicators with TTL
    
    Requires indexes (created on init):
    - presence_connections: {socket_id: 1}, {user_id: 1}, {expires_at: 1} TTL
    - presence_locations: {location_key: 1, user_id: 1}
    - presence_typing: {location_key: 1}, {expires_at: 1} TTL
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, connection_ttl: int = 120):
        """
        Initialize MongoDB presence adapter.
        
        Args:
            db: Motor async MongoDB database instance
            connection_ttl: Seconds before a connection is considered stale (default 2 mins)
        """
        self.db = db
        self.connections = db.presence_connections
        self.locations = db.presence_locations
        self.typing = db.presence_typing
        self.connection_ttl = connection_ttl
        self._indexes_created = False
    
    async def ensure_indexes(self):
        """Create necessary indexes if not already created"""
        if self._indexes_created:
            return
        
        try:
            # Connections collection indexes
            await self.connections.create_index("socket_id", unique=True)
            await self.connections.create_index("user_id")
            await self.connections.create_index("expires_at", expireAfterSeconds=0)
            
            # Locations collection indexes
            await self.locations.create_index([("location_key", 1), ("user_id", 1)], unique=True)
            await self.locations.create_index("user_id")
            
            # Typing collection indexes (5 second TTL)
            await self.typing.create_index("location_key")
            await self.typing.create_index("user_id")
            await self.typing.create_index("expires_at", expireAfterSeconds=0)
            
            self._indexes_created = True
            logger.info("[PRESENCE] MongoDB indexes created")
        except Exception as e:
            logger.warning(f"[PRESENCE] Index creation warning (may already exist): {e}")
            self._indexes_created = True
    
    async def add_user(self, user_id: str, socket_id: str, user_info: dict) -> None:
        await self.ensure_indexes()
        
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.connection_ttl)
        
        # Remove any existing connection for this user (single session)
        await self.connections.delete_many({"user_id": user_id})
        
        await self.connections.insert_one({
            "user_id": user_id,
            "socket_id": socket_id,
            "user_info": user_info,
            "connected_at": now,
            "last_heartbeat": now,
            "expires_at": expires_at
        })
        logger.info(f"[PRESENCE] User {user_id} connected via {socket_id}")
    
    async def remove_user(self, socket_id: str) -> Optional[str]:
        # Find and remove the connection
        doc = await self.connections.find_one_and_delete({"socket_id": socket_id})
        
        if doc:
            user_id = doc["user_id"]
            # Clean up locations and typing
            await self.locations.delete_many({"user_id": user_id})
            await self.typing.delete_many({"user_id": user_id})
            logger.info(f"[PRESENCE] User {user_id} disconnected")
            return user_id
        return None
    
    async def get_user_by_socket(self, socket_id: str) -> Optional[str]:
        doc = await self.connections.find_one({"socket_id": socket_id})
        return doc["user_id"] if doc else None
    
    async def get_user_info(self, user_id: str) -> Optional[dict]:
        doc = await self.connections.find_one({"user_id": user_id})
        if doc:
            return {
                "socket_id": doc["socket_id"],
                "user_info": doc["user_info"],
                "connected_at": doc["connected_at"],
                "last_heartbeat": doc["last_heartbeat"]
            }
        return None
    
    async def set_location(self, user_id: str, location_type: str, location_id: str) -> None:
        location_key = f"{location_type}:{location_id}"
        
        # Get user info for storing with location
        user_doc = await self.connections.find_one({"user_id": user_id})
        if not user_doc:
            return
        
        # Remove from any previous location
        await self.locations.delete_many({"user_id": user_id})
        
        # Add to new location
        await self.locations.update_one(
            {"location_key": location_key, "user_id": user_id},
            {"$set": {
                "location_key": location_key,
                "location_type": location_type,
                "location_id": location_id,
                "user_id": user_id,
                "user_info": user_doc["user_info"],
                "joined_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        logger.debug(f"[PRESENCE] User {user_id} joined {location_key}")
    
    async def leave_location(self, user_id: str) -> Optional[tuple]:
        doc = await self.locations.find_one_and_delete({"user_id": user_id})
        if doc:
            # Also clear typing
            await self.typing.delete_many({"user_id": user_id})
            return (doc["location_type"], doc["location_id"])
        return None
    
    async def get_users_at_location(self, location_type: str, location_id: str) -> List[dict]:
        location_key = f"{location_type}:{location_id}"
        cursor = self.locations.find({"location_key": location_key})
        users = []
        async for doc in cursor:
            users.append({
                "user_id": doc["user_id"],
                "user_info": doc["user_info"],
                "joined_at": doc["joined_at"]
            })
        return users
    
    async def set_typing(self, user_id: str, location_type: str, location_id: str, is_typing: bool) -> None:
        location_key = f"{location_type}:{location_id}"
        
        if is_typing:
            # Get user info
            user_doc = await self.connections.find_one({"user_id": user_id})
            if not user_doc:
                return
            
            # Set typing with 5-second TTL
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=5)
            await self.typing.update_one(
                {"location_key": location_key, "user_id": user_id},
                {"$set": {
                    "location_key": location_key,
                    "user_id": user_id,
                    "user_info": user_doc["user_info"],
                    "started_at": datetime.now(timezone.utc),
                    "expires_at": expires_at
                }},
                upsert=True
            )
        else:
            # Remove typing indicator
            await self.typing.delete_one({"location_key": location_key, "user_id": user_id})
    
    async def get_typing_users(self, location_type: str, location_id: str) -> List[dict]:
        location_key = f"{location_type}:{location_id}"
        now = datetime.now(timezone.utc)
        
        # Find non-expired typing indicators
        cursor = self.typing.find({
            "location_key": location_key,
            "expires_at": {"$gt": now}
        })
        
        users = []
        async for doc in cursor:
            users.append({
                "user_id": doc["user_id"],
                "name": doc["user_info"].get("name", "Unknown"),
                "started_at": doc["started_at"]
            })
        return users
    
    async def heartbeat(self, user_id: str) -> None:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.connection_ttl)
        
        await self.connections.update_one(
            {"user_id": user_id},
            {"$set": {
                "last_heartbeat": now,
                "expires_at": expires_at
            }}
        )
    
    async def get_online_users(self) -> List[dict]:
        cursor = self.connections.find({})
        users = []
        async for doc in cursor:
            users.append({
                "user_id": doc["user_id"],
                "user_info": doc["user_info"],
                "connected_at": doc["connected_at"]
            })
        return users
    
    async def get_user_count(self) -> int:
        return await self.connections.count_documents({})
    
    async def cleanup_stale(self, timeout_seconds: int = 60) -> int:
        """MongoDB TTL index handles this automatically, but manual cleanup available"""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
        result = await self.connections.delete_many({"last_heartbeat": {"$lt": cutoff}})
        if result.deleted_count > 0:
            logger.info(f"[PRESENCE] Cleaned up {result.deleted_count} stale connections")
        return result.deleted_count


class MongoLockAdapter(LockAdapter):
    """
    MongoDB-backed distributed locking using atomic operations.
    
    Collection: distributed_locks
    Requires index: {lock_name: 1} unique
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.locks = db.distributed_locks
        self._indexes_created = False
    
    async def ensure_indexes(self):
        if self._indexes_created:
            return
        
        try:
            await self.locks.create_index("lock_name", unique=True)
            await self.locks.create_index("expires_at", expireAfterSeconds=0)
            self._indexes_created = True
            logger.info("[LOCK] MongoDB indexes created")
        except Exception as e:
            logger.warning(f"[LOCK] Index creation warning: {e}")
            self._indexes_created = True
    
    async def acquire(self, lock_name: str, holder_id: str, ttl_seconds: int = 300) -> bool:
        await self.ensure_indexes()
        
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)
        
        try:
            # Try to insert new lock OR update expired lock
            result = await self.locks.find_one_and_update(
                {
                    "lock_name": lock_name,
                    "$or": [
                        {"expires_at": {"$lt": now}},  # Expired
                        {"holder_id": holder_id}       # Already ours (re-acquire)
                    ]
                },
                {
                    "$set": {
                        "lock_name": lock_name,
                        "holder_id": holder_id,
                        "acquired_at": now,
                        "expires_at": expires_at
                    }
                },
                upsert=True,
                return_document=ReturnDocument.AFTER
            )
            
            if result and result.get("holder_id") == holder_id:
                logger.info(f"[LOCK] Acquired lock '{lock_name}' by {holder_id}")
                return True
            return False
            
        except DuplicateKeyError:
            # Lock exists and is held by someone else
            return False
        except Exception as e:
            logger.error(f"[LOCK] Error acquiring lock: {e}")
            return False
    
    async def release(self, lock_name: str, holder_id: str) -> bool:
        result = await self.locks.delete_one({
            "lock_name": lock_name,
            "holder_id": holder_id
        })
        
        if result.deleted_count > 0:
            logger.info(f"[LOCK] Released lock '{lock_name}' by {holder_id}")
            return True
        return False
    
    async def extend(self, lock_name: str, holder_id: str, ttl_seconds: int = 300) -> bool:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        
        result = await self.locks.update_one(
            {"lock_name": lock_name, "holder_id": holder_id},
            {"$set": {"expires_at": expires_at}}
        )
        
        return result.modified_count > 0
    
    async def is_locked(self, lock_name: str) -> bool:
        now = datetime.now(timezone.utc)
        doc = await self.locks.find_one({
            "lock_name": lock_name,
            "expires_at": {"$gt": now}
        })
        return doc is not None
    
    async def get_holder(self, lock_name: str) -> Optional[str]:
        now = datetime.now(timezone.utc)
        doc = await self.locks.find_one({
            "lock_name": lock_name,
            "expires_at": {"$gt": now}
        })
        return doc["holder_id"] if doc else None


class MongoPubSubAdapter(PubSubAdapter):
    """
    MongoDB-backed pub/sub using change streams.
    
    Collection: pubsub_messages (capped collection for efficiency)
    
    Note: Requires MongoDB replica set for change streams.
    For single-node MongoDB, falls back to polling (less efficient).
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, use_polling: bool = False):
        """
        Initialize MongoDB pub/sub adapter.
        
        Args:
            db: Motor async MongoDB database instance
            use_polling: Use polling instead of change streams (for non-replica MongoDB)
        """
        self.db = db
        self.messages = db.pubsub_messages
        self.use_polling = use_polling
        self.subscriptions: Dict[str, List[Callable]] = {}
        self._running = False
        self._change_stream = None
        self._poll_task = None
        self._last_id = None
        self._initialized = False
    
    async def _ensure_collection(self):
        """Ensure the capped collection exists"""
        if self._initialized:
            return
            
        try:
            # Try to create capped collection
            await self.db.create_collection(
                "pubsub_messages",
                capped=True,
                size=10 * 1024 * 1024,  # 10MB
                max=10000  # Max 10K messages
            )
        except Exception:
            # Collection might already exist
            pass
        
        # Create index on channel for efficient filtering
        try:
            await self.messages.create_index("channel")
            await self.messages.create_index("created_at")
        except Exception:
            pass
        
        self._initialized = True
    
    async def publish(self, channel: str, message: dict) -> None:
        await self._ensure_collection()
        
        await self.messages.insert_one({
            "channel": channel,
            "message": message,
            "created_at": datetime.now(timezone.utc)
        })
    
    async def subscribe(self, channel: str, callback: Callable[[dict], Any]) -> None:
        if channel not in self.subscriptions:
            self.subscriptions[channel] = []
        self.subscriptions[channel].append(callback)
        logger.debug(f"[PUBSUB] Subscribed to channel: {channel}")
    
    async def unsubscribe(self, channel: str) -> None:
        if channel in self.subscriptions:
            del self.subscriptions[channel]
            logger.debug(f"[PUBSUB] Unsubscribed from channel: {channel}")
    
    async def start(self) -> None:
        """Start listening for messages"""
        await self._ensure_collection()
        self._running = True
        
        if self.use_polling:
            self._poll_task = asyncio.create_task(self._poll_loop())
            logger.info("[PUBSUB] Started MongoDB polling mode")
        else:
            try:
                # Try change stream first
                asyncio.create_task(self._change_stream_loop())
                logger.info("[PUBSUB] Started MongoDB change stream mode")
            except Exception as e:
                logger.warning(f"[PUBSUB] Change stream failed, falling back to polling: {e}")
                self.use_polling = True
                self._poll_task = asyncio.create_task(self._poll_loop())
    
    async def _change_stream_loop(self):
        """Listen for changes using MongoDB change streams"""
        while self._running:
            try:
                async with self.messages.watch(
                    [{"$match": {"operationType": "insert"}}],
                    full_document="updateLookup"
                ) as stream:
                    self._change_stream = stream
                    async for change in stream:
                        if not self._running:
                            break
                        
                        doc = change.get("fullDocument", {})
                        channel = doc.get("channel")
                        message = doc.get("message", {})
                        
                        if channel in self.subscriptions:
                            for callback in self.subscriptions[channel]:
                                try:
                                    if asyncio.iscoroutinefunction(callback):
                                        await callback(message)
                                    else:
                                        callback(message)
                                except Exception as e:
                                    logger.error(f"[PUBSUB] Callback error: {e}")
            except Exception as e:
                if self._running:
                    logger.error(f"[PUBSUB] Change stream error: {e}")
                    await asyncio.sleep(1)
    
    async def _poll_loop(self):
        """Fallback polling mode for non-replica MongoDB"""
        # Get the latest message ID to start from
        latest = await self.messages.find_one(sort=[("_id", -1)])
        if latest:
            self._last_id = latest["_id"]
        
        while self._running:
            try:
                query = {}
                if self._last_id:
                    query["_id"] = {"$gt": self._last_id}
                
                cursor = self.messages.find(query).sort("_id", 1)
                async for doc in cursor:
                    self._last_id = doc["_id"]
                    channel = doc.get("channel")
                    message = doc.get("message", {})
                    
                    if channel in self.subscriptions:
                        for callback in self.subscriptions[channel]:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(message)
                                else:
                                    callback(message)
                            except Exception as e:
                                logger.error(f"[PUBSUB] Callback error: {e}")
                
                await asyncio.sleep(0.5)  # Poll every 500ms
                
            except Exception as e:
                if self._running:
                    logger.error(f"[PUBSUB] Poll error: {e}")
                    await asyncio.sleep(1)
    
    async def stop(self) -> None:
        """Stop listening and cleanup"""
        self._running = False
        
        if self._change_stream:
            await self._change_stream.close()
        
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        
        logger.info("[PUBSUB] Stopped")
