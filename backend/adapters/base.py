"""
Base adapter interfaces for distributed services.
These abstractions allow swapping between MongoDB and Redis backends.

To switch to Redis later:
1. Create RedisPresenceAdapter, RedisLockAdapter, RedisPubSubAdapter
2. Change the imports in __init__.py
3. Set ADAPTER_BACKEND=redis in environment
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Set, Callable
from datetime import datetime


class PresenceAdapter(ABC):
    """
    Abstract interface for presence management.
    Tracks online users, their locations, and typing status.
    """
    
    @abstractmethod
    async def add_user(self, user_id: str, socket_id: str, user_info: dict) -> None:
        """Register a user as online"""
        pass
    
    @abstractmethod
    async def remove_user(self, socket_id: str) -> Optional[str]:
        """Remove user on disconnect, returns user_id if found"""
        pass
    
    @abstractmethod
    async def get_user_by_socket(self, socket_id: str) -> Optional[str]:
        """Get user_id from socket_id"""
        pass
    
    @abstractmethod
    async def get_user_info(self, user_id: str) -> Optional[dict]:
        """Get user's connection info"""
        pass
    
    @abstractmethod
    async def set_location(self, user_id: str, location_type: str, location_id: str) -> None:
        """Set user's current location (e.g., viewing ticket X)"""
        pass
    
    @abstractmethod
    async def leave_location(self, user_id: str) -> Optional[tuple]:
        """Remove user from their current location, returns (type, id) if was set"""
        pass
    
    @abstractmethod
    async def get_users_at_location(self, location_type: str, location_id: str) -> List[dict]:
        """Get all users at a specific location"""
        pass
    
    @abstractmethod
    async def set_typing(self, user_id: str, location_type: str, location_id: str, is_typing: bool) -> None:
        """Set user's typing status at a location"""
        pass
    
    @abstractmethod
    async def get_typing_users(self, location_type: str, location_id: str) -> List[dict]:
        """Get users currently typing at a location"""
        pass
    
    @abstractmethod
    async def heartbeat(self, user_id: str) -> None:
        """Update user's last active timestamp"""
        pass
    
    @abstractmethod
    async def get_online_users(self) -> List[dict]:
        """Get all online users"""
        pass
    
    @abstractmethod
    async def get_user_count(self) -> int:
        """Get count of online users"""
        pass
    
    @abstractmethod
    async def cleanup_stale(self, timeout_seconds: int = 60) -> int:
        """Remove stale connections, returns count removed"""
        pass


class LockAdapter(ABC):
    """
    Abstract interface for distributed locking.
    Ensures only one instance runs a task at a time.
    """
    
    @abstractmethod
    async def acquire(self, lock_name: str, holder_id: str, ttl_seconds: int = 300) -> bool:
        """
        Try to acquire a lock.
        Returns True if lock acquired, False if already held by another.
        """
        pass
    
    @abstractmethod
    async def release(self, lock_name: str, holder_id: str) -> bool:
        """
        Release a lock.
        Returns True if released, False if not held by this holder.
        """
        pass
    
    @abstractmethod
    async def extend(self, lock_name: str, holder_id: str, ttl_seconds: int = 300) -> bool:
        """
        Extend lock TTL.
        Returns True if extended, False if not held by this holder.
        """
        pass
    
    @abstractmethod
    async def is_locked(self, lock_name: str) -> bool:
        """Check if a lock is currently held"""
        pass
    
    @abstractmethod
    async def get_holder(self, lock_name: str) -> Optional[str]:
        """Get the current holder of a lock"""
        pass


class PubSubAdapter(ABC):
    """
    Abstract interface for publish/subscribe messaging.
    Used for cross-instance event broadcasting.
    """
    
    @abstractmethod
    async def publish(self, channel: str, message: dict) -> None:
        """Publish a message to a channel"""
        pass
    
    @abstractmethod
    async def subscribe(self, channel: str, callback: Callable[[dict], Any]) -> None:
        """Subscribe to a channel with a callback"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel"""
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """Start listening for messages"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop listening and cleanup"""
        pass
