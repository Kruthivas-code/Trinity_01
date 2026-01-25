"""
Trinity Real-time Collaboration Module
Production-ready WebSocket implementation with Socket.IO
"""

import socketio
import asyncio
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Any
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Socket.IO server with async mode
# For production with Redis: sio = socketio.AsyncServer(async_mode='asgi', client_manager=socketio.AsyncRedisManager('redis://localhost'))
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True
)

# In-memory presence store (for single instance)
# For production scaling, use Redis
class PresenceManager:
    def __init__(self):
        # user_id -> {socket_id, location, last_heartbeat, user_info}
        self.users: Dict[str, Dict[str, Any]] = {}
        # location_key -> set of user_ids (e.g., "ticket:uuid" -> {user1, user2})
        self.locations: Dict[str, Set[str]] = {}
        # socket_id -> user_id mapping
        self.socket_to_user: Dict[str, str] = {}
        # Typing indicators: location_key -> {user_id: timestamp}
        self.typing: Dict[str, Dict[str, datetime]] = {}
    
    def add_user(self, user_id: str, socket_id: str, user_info: dict):
        """Register a user connection"""
        self.users[user_id] = {
            "socket_id": socket_id,
            "location": None,
            "last_heartbeat": datetime.now(timezone.utc),
            "user_info": user_info,
            "connected_at": datetime.now(timezone.utc)
        }
        self.socket_to_user[socket_id] = user_id
        logger.info(f"User {user_id} connected via socket {socket_id}")
    
    def remove_user(self, socket_id: str) -> Optional[str]:
        """Remove user on disconnect"""
        user_id = self.socket_to_user.pop(socket_id, None)
        if user_id:
            user_data = self.users.pop(user_id, None)
            if user_data and user_data.get("location"):
                self._leave_location(user_id, user_data["location"])
            logger.info(f"User {user_id} disconnected")
        return user_id
    
    def set_location(self, user_id: str, location_type: str, location_id: Optional[str] = None):
        """Update user's current location"""
        if user_id not in self.users:
            return
        
        old_location = self.users[user_id].get("location")
        if old_location:
            self._leave_location(user_id, old_location)
        
        new_location = f"{location_type}:{location_id}" if location_id else location_type
        self.users[user_id]["location"] = new_location
        
        if new_location not in self.locations:
            self.locations[new_location] = set()
        self.locations[new_location].add(user_id)
        
        logger.info(f"User {user_id} moved to {new_location}")
    
    def _leave_location(self, user_id: str, location: str):
        """Remove user from a location"""
        if location in self.locations:
            self.locations[location].discard(user_id)
            if not self.locations[location]:
                del self.locations[location]
        # Clear typing indicator
        if location in self.typing:
            self.typing[location].pop(user_id, None)
    
    def get_users_at_location(self, location_type: str, location_id: Optional[str] = None) -> list:
        """Get all users at a specific location"""
        location_key = f"{location_type}:{location_id}" if location_id else location_type
        user_ids = self.locations.get(location_key, set())
        return [
            {
                "user_id": uid,
                **self.users[uid]["user_info"],
                "connected_at": self.users[uid]["connected_at"].isoformat()
            }
            for uid in user_ids if uid in self.users
        ]
    
    def set_typing(self, user_id: str, location_type: str, location_id: str, is_typing: bool):
        """Update typing indicator"""
        location_key = f"{location_type}:{location_id}"
        if location_key not in self.typing:
            self.typing[location_key] = {}
        
        if is_typing:
            self.typing[location_key][user_id] = datetime.now(timezone.utc)
        else:
            self.typing[location_key].pop(user_id, None)
    
    def get_typing_users(self, location_type: str, location_id: str) -> list:
        """Get users currently typing at a location"""
        location_key = f"{location_type}:{location_id}"
        typing_users = self.typing.get(location_key, {})
        # Filter out stale typing indicators (>5 seconds old)
        now = datetime.now(timezone.utc)
        active_typing = []
        for uid, timestamp in list(typing_users.items()):
            if (now - timestamp).total_seconds() < 5:
                if uid in self.users:
                    active_typing.append({
                        "user_id": uid,
                        **self.users[uid]["user_info"]
                    })
            else:
                del typing_users[uid]
        return active_typing
    
    def heartbeat(self, user_id: str):
        """Update user heartbeat"""
        if user_id in self.users:
            self.users[user_id]["last_heartbeat"] = datetime.now(timezone.utc)
    
    def get_online_users(self) -> list:
        """Get all online users"""
        return [
            {
                "user_id": uid,
                "location": data.get("location"),
                **data["user_info"]
            }
            for uid, data in self.users.items()
        ]
    
    def get_user_count(self) -> int:
        """Get count of online users"""
        return len(self.users)


# Global presence manager
presence = PresenceManager()


# Socket.IO Event Handlers
@sio.event
async def connect(sid, environ, auth):
    """Handle new connection"""
    logger.info(f"Client connecting: {sid}")
    # Auth will be validated when user sends 'authenticate' event
    await sio.emit('connected', {'sid': sid}, to=sid)


@sio.event
async def disconnect(sid):
    """Handle disconnection"""
    user_id = presence.remove_user(sid)
    if user_id:
        # Notify others about user leaving
        await sio.emit('user:offline', {
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })


@sio.event
async def authenticate(sid, data):
    """Authenticate user and register presence"""
    user_id = data.get('user_id')
    user_info = {
        'name': data.get('name', 'Unknown'),
        'email': data.get('email', ''),
        'picture': data.get('picture', '')
    }
    
    if not user_id:
        await sio.emit('auth_error', {'message': 'user_id required'}, to=sid)
        return
    
    presence.add_user(user_id, sid, user_info)
    
    # Send confirmation
    await sio.emit('authenticated', {
        'user_id': user_id,
        'online_count': presence.get_user_count()
    }, to=sid)
    
    # Notify others
    await sio.emit('user:online', {
        'user_id': user_id,
        **user_info,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }, skip_sid=sid)


@sio.event
async def join_location(sid, data):
    """User joins a location (ticket, dashboard, etc.)"""
    user_id = presence.socket_to_user.get(sid)
    if not user_id:
        return
    
    location_type = data.get('type', 'unknown')  # 'ticket', 'dashboard', 'admin'
    location_id = data.get('id')  # ticket_id, etc.
    
    presence.set_location(user_id, location_type, location_id)
    
    # Join Socket.IO room for this location
    room = f"{location_type}:{location_id}" if location_id else location_type
    sio.enter_room(sid, room)
    
    # Get other users at this location
    users_here = presence.get_users_at_location(location_type, location_id)
    
    # Send current presence to the joining user
    await sio.emit('presence:sync', {
        'location': room,
        'users': users_here
    }, to=sid)
    
    # Notify others in the room
    if user_id in presence.users:
        await sio.emit('user:joined', {
            'user_id': user_id,
            **presence.users[user_id]['user_info'],
            'location': room,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }, room=room, skip_sid=sid)


@sio.event
async def leave_location(sid, data):
    """User leaves a location"""
    user_id = presence.socket_to_user.get(sid)
    if not user_id:
        return
    
    location_type = data.get('type')
    location_id = data.get('id')
    room = f"{location_type}:{location_id}" if location_id else location_type
    
    sio.leave_room(sid, room)
    
    # Notify others
    await sio.emit('user:left', {
        'user_id': user_id,
        'location': room,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }, room=room)


@sio.event
async def typing(sid, data):
    """User is typing"""
    user_id = presence.socket_to_user.get(sid)
    if not user_id:
        return
    
    location_type = data.get('type', 'ticket')
    location_id = data.get('id')
    is_typing = data.get('is_typing', True)
    
    if not location_id:
        return
    
    presence.set_typing(user_id, location_type, location_id, is_typing)
    
    room = f"{location_type}:{location_id}"
    
    # Broadcast to room
    await sio.emit('user:typing', {
        'user_id': user_id,
        'name': presence.users.get(user_id, {}).get('user_info', {}).get('name', 'Unknown'),
        'is_typing': is_typing,
        'location': room,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }, room=room, skip_sid=sid)


@sio.event
async def heartbeat(sid):
    """Heartbeat to keep connection alive"""
    user_id = presence.socket_to_user.get(sid)
    if user_id:
        presence.heartbeat(user_id)


# Broadcast functions for use from FastAPI endpoints
async def broadcast_ticket_update(ticket_id: str, action: str, ticket_data: dict, updated_by: dict):
    """Broadcast ticket update to all users viewing the ticket"""
    room = f"ticket:{ticket_id}"
    await sio.emit('ticket:update', {
        'ticket_id': ticket_id,
        'action': action,  # 'created', 'updated', 'deleted', 'status_changed', 'assigned'
        'ticket': ticket_data,
        'updated_by': updated_by,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }, room=room)
    
    # Also broadcast to dashboard for list updates
    await sio.emit('ticket:update', {
        'ticket_id': ticket_id,
        'action': action,
        'ticket': ticket_data,
        'updated_by': updated_by,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }, room='dashboard')


async def broadcast_ticket_created(ticket_data: dict, created_by: dict):
    """Broadcast new ticket creation"""
    await sio.emit('ticket:created', {
        'ticket': ticket_data,
        'created_by': created_by,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }, room='dashboard')


async def broadcast_ticket_deleted(ticket_id: str, deleted_by: dict):
    """Broadcast ticket deletion"""
    await sio.emit('ticket:deleted', {
        'ticket_id': ticket_id,
        'deleted_by': deleted_by,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


async def broadcast_notification(user_id: str, notification: dict):
    """Send notification to specific user"""
    # Find user's socket
    if user_id in presence.users:
        socket_id = presence.users[user_id]['socket_id']
        await sio.emit('notification:new', notification, to=socket_id)


def get_presence_stats() -> dict:
    """Get presence statistics"""
    return {
        'online_users': presence.get_user_count(),
        'active_locations': len(presence.locations),
        'users': presence.get_online_users()
    }


def get_users_viewing_ticket(ticket_id: str) -> list:
    """Get users currently viewing a specific ticket"""
    return presence.get_users_at_location('ticket', ticket_id)


def get_typing_in_ticket(ticket_id: str) -> list:
    """Get users typing in a specific ticket"""
    return presence.get_typing_users('ticket', ticket_id)


# Create ASGI app for Socket.IO
socket_app = socketio.ASGIApp(sio)
