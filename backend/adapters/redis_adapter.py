"""
Redis implementation of distributed adapters.
Uses Redis native features for pub/sub, distributed locking, and presence.

This is the recommended adapter for multi-instance deployments.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Callable
import redis.asyncio as redis

from .base import PresenceAdapter, LockAdapter, PubSubAdapter

logger = logging.getLogger(__name__)


class RedisPresenceAdapter(PresenceAdapter):
    """
    Redis-backed presence management using sorted sets and hashes.
    
    Keys used:
    - presence:connections        -> Hash: socket_id -> JSON user data
    - presence:users             -> Hash: user_id -> socket_id  
    - presence:location:{key}    -> Set: user_ids at this location
    - presence:user_location:{uid} -> String: current location key
    - presence:typing:{key}      -> Sorted set: user_id -> expiry timestamp
    - presence:heartbeat         -> Sorted set: user_id -> timestamp (for cleanup)
    """
    
    def __init__(self, redis_url: str, connection_ttl: int = 120):
        """
        Initialize Redis presence adapter.
        
        Args:
            redis_url: Redis connection URL
            connection_ttl: Seconds before a connection is considered stale
        """
        self.redis_url = redis_url
        self.connection_ttl = connection_ttl
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection"""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    async def add_user(self, user_id: str, socket_id: str, user_info: dict) -> None:
        r = await self._get_redis()
        
        now = datetime.now(timezone.utc)
        
        # Remove any existing connection for this user
        old_socket = await r.hget("presence:users", user_id)
        if old_socket:
            await r.hdel("presence:connections", old_socket)
        
        # Store connection data
        user_data = {
            "user_id": user_id,
            "socket_id": socket_id,
            "user_info": user_info,
            "connected_at": now.isoformat()
        }
        
        pipe = r.pipeline()
        pipe.hset("presence:connections", socket_id, json.dumps(user_data))
        pipe.hset("presence:users", user_id, socket_id)
        pipe.zadd("presence:heartbeat", {user_id: now.timestamp()})
        await pipe.execute()
        
        logger.info(f"[PRESENCE] User {user_id} connected via {socket_id}")
    
    async def remove_user(self, socket_id: str) -> Optional[str]:
        r = await self._get_redis()
        
        # Get user data from connection
        data = await r.hget("presence:connections", socket_id)
        if not data:
            return None
        
        user_data = json.loads(data)
        user_id = user_data["user_id"]
        
        # Clean up user's location
        await self.leave_location(user_id)
        
        # Remove all presence data
        pipe = r.pipeline()
        pipe.hdel("presence:connections", socket_id)
        pipe.hdel("presence:users", user_id)
        pipe.zrem("presence:heartbeat", user_id)
        await pipe.execute()
        
        logger.info(f"[PRESENCE] User {user_id} disconnected")
        return user_id
    
    async def get_user_by_socket(self, socket_id: str) -> Optional[str]:
        r = await self._get_redis()
        data = await r.hget("presence:connections", socket_id)
        if data:
            return json.loads(data)["user_id"]
        return None
    
    async def get_user_info(self, user_id: str) -> Optional[dict]:
        r = await self._get_redis()
        socket_id = await r.hget("presence:users", user_id)
        if not socket_id:
            return None
        
        data = await r.hget("presence:connections", socket_id)
        if data:
            user_data = json.loads(data)
            return {
                "socket_id": user_data["socket_id"],
                "user_info": user_data["user_info"],
                "connected_at": user_data["connected_at"]
            }
        return None
    
    async def set_location(self, user_id: str, location_type: str, location_id: str) -> None:
        r = await self._get_redis()
        location_key = f"{location_type}:{location_id}"
        
        # Get user info for storing with location
        user_info = await self.get_user_info(user_id)
        if not user_info:
            return
        
        # Remove from previous location
        await self.leave_location(user_id)
        
        # Store location data
        location_data = {
            "user_id": user_id,
            "user_info": user_info["user_info"],
            "joined_at": datetime.now(timezone.utc).isoformat()
        }
        
        pipe = r.pipeline()
        pipe.sadd(f"presence:location:{location_key}", json.dumps(location_data))
        pipe.set(f"presence:user_location:{user_id}", location_key)
        await pipe.execute()
        
        logger.debug(f"[PRESENCE] User {user_id} joined {location_key}")
    
    async def leave_location(self, user_id: str) -> Optional[tuple]:
        r = await self._get_redis()
        
        # Get current location
        location_key = await r.get(f"presence:user_location:{user_id}")
        if not location_key:
            return None
        
        # Find and remove user from location set
        members = await r.smembers(f"presence:location:{location_key}")
        for member in members:
            try:
                data = json.loads(member)
                if data.get("user_id") == user_id:
                    await r.srem(f"presence:location:{location_key}", member)
                    break
            except json.JSONDecodeError:
                continue
        
        # Remove user's location pointer
        await r.delete(f"presence:user_location:{user_id}")
        
        # Also clear typing
        await r.zrem(f"presence:typing:{location_key}", user_id)
        
        parts = location_key.split(":", 1)
        if len(parts) == 2:
            return (parts[0], parts[1])
        return None
    
    async def get_users_at_location(self, location_type: str, location_id: str) -> List[dict]:
        r = await self._get_redis()
        location_key = f"{location_type}:{location_id}"
        
        members = await r.smembers(f"presence:location:{location_key}")
        users = []
        for member in members:
            try:
                data = json.loads(member)
                users.append({
                    "user_id": data["user_id"],
                    "user_info": data["user_info"],
                    "joined_at": data["joined_at"]
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return users
    
    async def set_typing(self, user_id: str, location_type: str, location_id: str, is_typing: bool) -> None:
        r = await self._get_redis()
        location_key = f"{location_type}:{location_id}"
        typing_key = f"presence:typing:{location_key}"
        
        if is_typing:
            # Get user info
            user_info = await self.get_user_info(user_id)
            if not user_info:
                return
            
            # Store typing with 5-second expiry timestamp
            expires_at = datetime.now(timezone.utc).timestamp() + 5
            
            # Store user info alongside for retrieval
            info_key = f"presence:typing_info:{location_key}:{user_id}"
            await r.setex(info_key, 5, json.dumps(user_info["user_info"]))
            
            await r.zadd(typing_key, {user_id: expires_at})
        else:
            await r.zrem(typing_key, user_id)
    
    async def get_typing_users(self, location_type: str, location_id: str) -> List[dict]:
        r = await self._get_redis()
        location_key = f"{location_type}:{location_id}"
        typing_key = f"presence:typing:{location_key}"
        
        now = datetime.now(timezone.utc).timestamp()
        
        # Get non-expired typing indicators
        typing_users = await r.zrangebyscore(typing_key, now, "+inf")
        
        # Clean up expired entries
        await r.zremrangebyscore(typing_key, "-inf", now)
        
        users = []
        for user_id in typing_users:
            # Try to get user info
            info_key = f"presence:typing_info:{location_key}:{user_id}"
            info_data = await r.get(info_key)
            name = "Unknown"
            if info_data:
                try:
                    info = json.loads(info_data)
                    name = info.get("name", "Unknown")
                except json.JSONDecodeError:
                    pass
            
            users.append({
                "user_id": user_id,
                "name": name,
                "started_at": datetime.now(timezone.utc).isoformat()
            })
        
        return users
    
    async def heartbeat(self, user_id: str) -> None:
        r = await self._get_redis()
        now = datetime.now(timezone.utc).timestamp()
        await r.zadd("presence:heartbeat", {user_id: now})
    
    async def get_online_users(self) -> List[dict]:
        r = await self._get_redis()
        
        # Get all connections
        connections = await r.hgetall("presence:connections")
        users = []
        for socket_id, data in connections.items():
            try:
                user_data = json.loads(data)
                users.append({
                    "user_id": user_data["user_id"],
                    "user_info": user_data["user_info"],
                    "connected_at": user_data["connected_at"]
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return users
    
    async def get_user_count(self) -> int:
        r = await self._get_redis()
        return await r.hlen("presence:connections")
    
    async def cleanup_stale(self, timeout_seconds: int = 60) -> int:
        r = await self._get_redis()
        cutoff = datetime.now(timezone.utc).timestamp() - timeout_seconds
        
        # Find stale users
        stale_users = await r.zrangebyscore("presence:heartbeat", "-inf", cutoff)
        
        count = 0
        for user_id in stale_users:
            socket_id = await r.hget("presence:users", user_id)
            if socket_id:
                await self.remove_user(socket_id)
                count += 1
        
        if count > 0:
            logger.info(f"[PRESENCE] Cleaned up {count} stale connections")
        
        return count


class RedisLockAdapter(LockAdapter):
    """
    Redis-backed distributed locking using SET NX with expiry.
    
    Keys used:
    - lock:{name} -> String with holder_id, auto-expires
    """
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    async def acquire(self, lock_name: str, holder_id: str, ttl_seconds: int = 300) -> bool:
        r = await self._get_redis()
        key = f"lock:{lock_name}"
        
        # Try to set lock with NX (only if not exists) and EX (expiry)
        acquired = await r.set(key, holder_id, nx=True, ex=ttl_seconds)
        
        if acquired:
            logger.info(f"[LOCK] Acquired lock '{lock_name}' by {holder_id}")
            return True
        
        # Check if we already hold it (re-acquire)
        current_holder = await r.get(key)
        if current_holder == holder_id:
            # Extend our existing lock
            await r.expire(key, ttl_seconds)
            logger.info(f"[LOCK] Re-acquired lock '{lock_name}' by {holder_id}")
            return True
        
        return False
    
    async def release(self, lock_name: str, holder_id: str) -> bool:
        r = await self._get_redis()
        key = f"lock:{lock_name}"
        
        # Lua script to atomically check and delete
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        result = await r.eval(script, 1, key, holder_id)
        
        if result:
            logger.info(f"[LOCK] Released lock '{lock_name}' by {holder_id}")
            return True
        return False
    
    async def extend(self, lock_name: str, holder_id: str, ttl_seconds: int = 300) -> bool:
        r = await self._get_redis()
        key = f"lock:{lock_name}"
        
        # Lua script to atomically check and extend
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        
        result = await r.eval(script, 1, key, holder_id, ttl_seconds)
        return bool(result)
    
    async def is_locked(self, lock_name: str) -> bool:
        r = await self._get_redis()
        key = f"lock:{lock_name}"
        return await r.exists(key) > 0
    
    async def get_holder(self, lock_name: str) -> Optional[str]:
        r = await self._get_redis()
        key = f"lock:{lock_name}"
        return await r.get(key)


class RedisPubSubAdapter(PubSubAdapter):
    """
    Redis-backed pub/sub using native Redis pub/sub.
    
    This is the most efficient solution for cross-instance messaging.
    No polling required - true push notifications.
    """
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.subscriptions: Dict[str, List[Callable]] = {}
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._running = False
        self._listen_task: Optional[asyncio.Task] = None
    
    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    async def publish(self, channel: str, message: dict) -> None:
        r = await self._get_redis()
        await r.publish(f"pubsub:{channel}", json.dumps(message))
    
    async def subscribe(self, channel: str, callback: Callable[[dict], Any]) -> None:
        if channel not in self.subscriptions:
            self.subscriptions[channel] = []
            
            # Actually subscribe to Redis channel if running
            if self._pubsub:
                await self._pubsub.subscribe(f"pubsub:{channel}")
        
        self.subscriptions[channel].append(callback)
        logger.debug(f"[PUBSUB] Subscribed to channel: {channel}")
    
    async def unsubscribe(self, channel: str) -> None:
        if channel in self.subscriptions:
            del self.subscriptions[channel]
            
            if self._pubsub:
                await self._pubsub.unsubscribe(f"pubsub:{channel}")
            
            logger.debug(f"[PUBSUB] Unsubscribed from channel: {channel}")
    
    async def start(self) -> None:
        """Start listening for messages"""
        r = await self._get_redis()
        self._pubsub = r.pubsub()
        self._running = True
        
        # Subscribe to all registered channels
        for channel in self.subscriptions.keys():
            await self._pubsub.subscribe(f"pubsub:{channel}")
        
        # Start listener task
        self._listen_task = asyncio.create_task(self._listen_loop())
        logger.info("[PUBSUB] Started Redis pub/sub listener")
    
    async def _listen_loop(self):
        """Listen for pub/sub messages"""
        while self._running:
            try:
                message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                
                if message and message["type"] == "message":
                    # Extract channel name (remove 'pubsub:' prefix)
                    full_channel = message["channel"]
                    if full_channel.startswith("pubsub:"):
                        channel = full_channel[7:]  # Remove 'pubsub:' prefix
                    else:
                        channel = full_channel
                    
                    # Parse message data
                    try:
                        data = json.loads(message["data"])
                    except json.JSONDecodeError:
                        data = message["data"]
                    
                    # Call subscribers
                    if channel in self.subscriptions:
                        for callback in self.subscriptions[channel]:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(data)
                                else:
                                    callback(data)
                            except Exception as e:
                                logger.error(f"[PUBSUB] Callback error: {e}")
                
                # Small sleep to prevent tight loop when no messages
                await asyncio.sleep(0.01)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._running:
                    logger.error(f"[PUBSUB] Listen error: {e}")
                    await asyncio.sleep(1)
    
    async def stop(self) -> None:
        """Stop listening and cleanup"""
        self._running = False
        
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        
        if self._pubsub:
            await self._pubsub.close()
        
        if self._redis:
            await self._redis.close()
        
        logger.info("[PUBSUB] Stopped")
