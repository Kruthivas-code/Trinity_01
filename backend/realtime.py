"""
Trinity Real-time Collaboration Module
Production-ready WebSocket implementation with Socket.IO

This module uses the adapter pattern for distributed presence management.
Uses MongoDB for presence, locking, and pub/sub.

Configuration:
    MONGODB_PUBSUB_POLLING: 'true' for non-replica MongoDB (default: false)
"""

import socketio
import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Any
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Build allowed origins for Socket.IO CORS (must match server.py CORS config)
_sio_origins = os.environ.get("ALLOWED_ORIGINS", "").split(",")
if not _sio_origins or _sio_origins == [""]:
    _sio_origins = [
        "https://audit-engine-13.preview.emergentagent.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
_sio_origins = [o.strip() for o in _sio_origins if o.strip()]

# Create Socket.IO server with async mode
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=_sio_origins,
    logger=True,
    engineio_logger=True
)

# Presence adapter (initialized later when DB is available)
_presence_adapter = None
_pubsub_adapter = None

# Local socket-to-user mapping (required for Socket.IO event handling)
# This is instance-local but presence state is in the distributed adapter
_socket_to_user: Dict[str, str] = {}
_user_to_socket: Dict[str, str] = {}


def initialize_realtime(db):
    """
    Initialize realtime module with database connection.
    Must be called from server.py after database is connected.
    """
    global _presence_adapter, _pubsub_adapter
    
    from adapters import set_database, get_presence_adapter, get_pubsub_adapter
    
    set_database(db)
    _presence_adapter = get_presence_adapter()
    _pubsub_adapter = get_pubsub_adapter()
    
    logger.info("[REALTIME] Initialized with MongoDB adapters")
    return _presence_adapter, _pubsub_adapter


async def start_pubsub():
    """Start the pub/sub listener for cross-instance messaging"""
    global _pubsub_adapter
    if _pubsub_adapter:
        # Subscribe to cross-instance events
        await _pubsub_adapter.subscribe('ticket_updates', _handle_cross_instance_ticket_update)
        await _pubsub_adapter.subscribe('typing_updates', _handle_cross_instance_typing)
        await _pubsub_adapter.subscribe('notifications', _handle_cross_instance_notification)
        await _pubsub_adapter.start()
        logger.info("[REALTIME] Pub/sub listener started")


async def stop_pubsub():
    """Stop the pub/sub listener"""
    global _pubsub_adapter
    if _pubsub_adapter:
        await _pubsub_adapter.stop()
        logger.info("[REALTIME] Pub/sub listener stopped")


async def _handle_cross_instance_ticket_update(message: dict):
    """Handle ticket updates from other instances"""
    room = message.get('room')
    event = message.get('event')
    data = message.get('data')
    source_instance = message.get('source')
    
    # Don't re-broadcast our own messages
    if source_instance == _get_instance_id():
        return
    
    if room and event and data:
        await sio.emit(event, data, room=room)


async def _handle_cross_instance_typing(message: dict):
    """Handle typing indicators from other instances"""
    room = message.get('room')
    data = message.get('data')
    source_instance = message.get('source')
    
    if source_instance == _get_instance_id():
        return
    
    if room and data:
        await sio.emit('user:typing', data, room=room)


async def _handle_cross_instance_notification(message: dict):
    """Handle notifications from other instances"""
    user_id = message.get('user_id')
    notification = message.get('notification')
    source_instance = message.get('source')
    
    if source_instance == _get_instance_id():
        return
    
    # Check if user is connected to THIS instance
    if user_id in _user_to_socket:
        socket_id = _user_to_socket[user_id]
        await sio.emit('notification:new', notification, to=socket_id)


def _get_instance_id() -> str:
    """Get unique identifier for this server instance"""
    return os.environ.get('INSTANCE_ID', os.environ.get('HOSTNAME', 'default'))


# ==================== WebSocket Security Configuration ====================
# Authentication timeout in seconds - disconnect if not authenticated within this time
WS_AUTH_TIMEOUT = 30
# Maximum message size in bytes
WS_MAX_MESSAGE_SIZE = 65536  # 64KB
# Track unauthenticated connections for timeout enforcement
_unauthenticated_sids: Dict[str, datetime] = {}

# Socket.IO Event Handlers
@sio.event
async def connect(sid, environ, auth):
    """Handle new connection - require authentication within timeout"""
    logger.info(f"Client connecting: {sid}")
    
    # Track when this connection was established for auth timeout
    _unauthenticated_sids[sid] = datetime.now(timezone.utc)
    
    await sio.emit('connected', {'sid': sid, 'auth_timeout': WS_AUTH_TIMEOUT}, to=sid)
    
    # Schedule authentication timeout check
    asyncio.create_task(_check_auth_timeout(sid))


async def _check_auth_timeout(sid: str):
    """Disconnect client if not authenticated within timeout"""
    await asyncio.sleep(WS_AUTH_TIMEOUT)
    
    # Check if still in unauthenticated list
    if sid in _unauthenticated_sids:
        logger.warning(f"WebSocket auth timeout for {sid} - disconnecting")
        del _unauthenticated_sids[sid]
        await sio.emit('auth_error', {'message': 'Authentication timeout'}, to=sid)
        await sio.disconnect(sid)


@sio.event
async def disconnect(sid):
    """Handle disconnection"""
    global _presence_adapter
    
    # Clean up from unauthenticated list if present
    _unauthenticated_sids.pop(sid, None)
    
    user_id = _socket_to_user.pop(sid, None)
    if user_id:
        _user_to_socket.pop(user_id, None)
        
        # Remove from distributed presence
        if _presence_adapter:
            await _presence_adapter.remove_user(sid)
        
        # Notify others about user leaving
        await sio.emit('user:offline', {
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })


@sio.event
async def authenticate(sid, data):
    """
    Authenticate user and register presence.
    
    Security improvements:
    - Validates user_id format
    - Limits data sizes
    - Tracks authentication state
    """
    global _presence_adapter
    
    # Validate data size to prevent memory attacks
    if len(str(data)) > WS_MAX_MESSAGE_SIZE:
        await sio.emit('auth_error', {'message': 'Data too large'}, to=sid)
        return
    
    user_id = data.get('user_id')
    
    # Validate user_id format
    if not user_id or not isinstance(user_id, str):
        await sio.emit('auth_error', {'message': 'user_id required'}, to=sid)
        return
    
    if len(user_id) > 100:
        await sio.emit('auth_error', {'message': 'Invalid user_id'}, to=sid)
        return
    
    # Validate user_id format (basic sanitization)
    if not user_id.replace('_', '').replace('-', '').isalnum():
        await sio.emit('auth_error', {'message': 'Invalid user_id format'}, to=sid)
        return
    
    # Sanitize user info
    user_info = {
        'name': str(data.get('name', 'Unknown'))[:100],
        'email': str(data.get('email', ''))[:255],
        'picture': str(data.get('picture', ''))[:500]
    }
    
    # Remove from unauthenticated list (authentication successful)
    _unauthenticated_sids.pop(sid, None)
    
    # Local mapping
    _socket_to_user[sid] = user_id
    _user_to_socket[user_id] = sid
    
    # Distributed presence
    if _presence_adapter:
        await _presence_adapter.add_user(user_id, sid, user_info)
    
    # Get online count
    online_count = await _presence_adapter.get_user_count() if _presence_adapter else 1
    
    logger.info(f"WebSocket authenticated: {user_id} ({sid})")
    
    # Send confirmation
    await sio.emit('authenticated', {
        'user_id': user_id,
        'online_count': online_count
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
    global _presence_adapter
    
    user_id = _socket_to_user.get(sid)
    if not user_id:
        return
    
    location_type = data.get('type', 'unknown')
    location_id = data.get('id')
    
    # Update distributed presence
    if _presence_adapter:
        await _presence_adapter.set_location(user_id, location_type, location_id)
    
    # Join Socket.IO room for this location
    room = f"{location_type}:{location_id}" if location_id else location_type
    sio.enter_room(sid, room)
    
    # Get other users at this location
    users_here = []
    if _presence_adapter:
        users_here = await _presence_adapter.get_users_at_location(location_type, location_id)
    
    # Send current presence to the joining user
    await sio.emit('presence:sync', {
        'location': room,
        'users': users_here
    }, to=sid)
    
    # Get user info for notification
    user_info = {}
    if _presence_adapter:
        info = await _presence_adapter.get_user_info(user_id)
        if info:
            user_info = info.get('user_info', {})
    
    # Notify others in the room
    await sio.emit('user:joined', {
        'user_id': user_id,
        **user_info,
        'location': room,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }, room=room, skip_sid=sid)


@sio.event
async def leave_location(sid, data):
    """User leaves a location"""
    global _presence_adapter
    
    user_id = _socket_to_user.get(sid)
    if not user_id:
        return
    
    location_type = data.get('type')
    location_id = data.get('id')
    room = f"{location_type}:{location_id}" if location_id else location_type
    
    # Leave Socket.IO room
    sio.leave_room(sid, room)
    
    # Update distributed presence
    if _presence_adapter:
        await _presence_adapter.leave_location(user_id)
    
    # Notify others
    await sio.emit('user:left', {
        'user_id': user_id,
        'location': room,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }, room=room)


@sio.event
async def typing(sid, data):
    """User is typing"""
    global _presence_adapter, _pubsub_adapter
    
    user_id = _socket_to_user.get(sid)
    if not user_id:
        return
    
    location_type = data.get('type', 'ticket')
    location_id = data.get('id')
    is_typing = data.get('is_typing', True)
    
    if not location_id:
        return
    
    # Get user name
    user_name = 'Unknown'
    if _presence_adapter:
        info = await _presence_adapter.get_user_info(user_id)
        if info:
            user_name = info.get('user_info', {}).get('name', 'Unknown')
        
        # Update typing status in distributed store
        await _presence_adapter.set_typing(user_id, location_type, location_id, is_typing)
    
    room = f"{location_type}:{location_id}"
    typing_data = {
        'user_id': user_id,
        'name': user_name,
        'is_typing': is_typing,
        'location': room,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    # Broadcast to local room
    await sio.emit('user:typing', typing_data, room=room, skip_sid=sid)
    
    # Also publish to other instances via pub/sub
    if _pubsub_adapter:
        await _pubsub_adapter.publish('typing_updates', {
            'room': room,
            'data': typing_data,
            'source': _get_instance_id()
        })


@sio.event
async def heartbeat(sid):
    """Heartbeat to keep connection alive"""
    global _presence_adapter
    
    user_id = _socket_to_user.get(sid)
    if user_id and _presence_adapter:
        await _presence_adapter.heartbeat(user_id)


# Broadcast functions for use from FastAPI endpoints
async def broadcast_ticket_update(ticket_id: str, action: str, ticket_data: dict, updated_by: dict):
    """Broadcast ticket update to all connected clients"""
    global _pubsub_adapter
    
    room = f"ticket:{ticket_id}"
    event_data = {
        'ticket_id': ticket_id,
        'action': action,
        'ticket': ticket_data,
        'updated_by': updated_by,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    # Emit ONLY ONCE to all connected clients
    # This prevents triple updates and UI glitching
    await sio.emit('ticket:update', event_data)
    
    # Broadcast to other server instances via pub/sub
    if _pubsub_adapter:
        await _pubsub_adapter.publish('ticket_updates', {
            'room': 'all',
            'event': 'ticket:update',
            'data': event_data,
            'source': _get_instance_id()
        })


async def broadcast_ticket_created(ticket_data: dict, created_by: dict):
    """Broadcast new ticket creation to all connected clients"""
    global _pubsub_adapter
    
    event_data = {
        'ticket': ticket_data,
        'created_by': created_by,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    # Emit ONLY ONCE to all connected clients
    # This prevents double updates and UI glitching
    await sio.emit('ticket:created', event_data)
    
    if _pubsub_adapter:
        await _pubsub_adapter.publish('ticket_updates', {
            'room': 'all',
            'event': 'ticket:created',
            'data': event_data,
            'source': _get_instance_id()
        })


async def broadcast_ticket_deleted(ticket_id: str, deleted_by: dict):
    """Broadcast ticket deletion"""
    global _pubsub_adapter
    
    event_data = {
        'ticket_id': ticket_id,
        'deleted_by': deleted_by,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    await sio.emit('ticket:deleted', event_data)
    
    if _pubsub_adapter:
        await _pubsub_adapter.publish('ticket_updates', {
            'room': 'all',
            'event': 'ticket:deleted',
            'data': event_data,
            'source': _get_instance_id()
        })


async def broadcast_notification(user_id: str, notification: dict):
    """Send notification to specific user"""
    global _pubsub_adapter
    
    # Try local first
    if user_id in _user_to_socket:
        socket_id = _user_to_socket[user_id]
        await sio.emit('notification:new', notification, to=socket_id)
    elif _pubsub_adapter:
        # User might be on another instance
        await _pubsub_adapter.publish('notifications', {
            'user_id': user_id,
            'notification': notification,
            'source': _get_instance_id()
        })


# ==================== Leave Broadcasting ====================

async def broadcast_leave_created(leave_data: dict, created_by: dict):
    """Broadcast new leave creation to all connected users"""
    await sio.emit('leave:created', {
        'leave': leave_data,
        'created_by': created_by,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


async def broadcast_leave_updated(leave_id: str, leave_data: dict, updated_by: dict):
    """Broadcast leave update to all connected users"""
    await sio.emit('leave:updated', {
        'leave_id': leave_id,
        'leave': leave_data,
        'updated_by': updated_by,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


async def broadcast_leave_deleted(leave_id: str, deleted_by: dict):
    """Broadcast leave deletion to all connected users"""
    await sio.emit('leave:deleted', {
        'leave_id': leave_id,
        'deleted_by': deleted_by,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


async def broadcast_mention_notification(user_id: str, ticket_id: str, ticket_title: str, mentioned_by: str, note_preview: str):
    """Send notification to a user when they are mentioned in a ticket"""
    global _pubsub_adapter
    
    notification = {
        'type': 'mention',
        'ticket_id': ticket_id,
        'ticket_title': ticket_title,
        'mentioned_by': mentioned_by,
        'note_preview': note_preview,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    # Try local first
    if user_id in _user_to_socket:
        socket_id = _user_to_socket[user_id]
        await sio.emit('notification:mention', notification, to=socket_id)
    elif _pubsub_adapter:
        # User might be on another instance
        await _pubsub_adapter.publish('notifications', {
            'user_id': user_id,
            'notification': notification,
            'source': _get_instance_id()
        })
    
    # Also broadcast to the ticket room
    await sio.emit('ticket:mention', {
        'ticket_id': ticket_id,
        'mentioned_user_id': user_id,
        'mentioned_by': mentioned_by,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


async def get_presence_stats() -> dict:
    """Get presence statistics"""
    global _presence_adapter
    
    if _presence_adapter:
        online_users = await _presence_adapter.get_online_users()
        return {
            'online_users': len(online_users),
            'active_locations': 0,  # Would need to track this
            'users': online_users
        }
    return {'online_users': 0, 'active_locations': 0, 'users': []}


async def get_users_viewing_ticket(ticket_id: str) -> list:
    """Get users currently viewing a specific ticket"""
    global _presence_adapter
    
    if _presence_adapter:
        return await _presence_adapter.get_users_at_location('ticket', ticket_id)
    return []


async def get_typing_in_ticket(ticket_id: str) -> list:
    """Get users typing in a specific ticket"""
    global _presence_adapter
    
    if _presence_adapter:
        return await _presence_adapter.get_typing_users('ticket', ticket_id)
    return []


# Create ASGI app for Socket.IO
# Configure socketio_path to match where we expect requests
socket_app = socketio.ASGIApp(sio, socketio_path='/')
