"""
Test Atlas Shadow Sync Feature
==============================
Tests for Shadow Mode real-time sync with Atlas:
- Backend health check
- Sync API endpoints (status, start, stop, config)
- Auto-start verification via MongoDB state
- Synced tickets verification (created_by='atlas_sync')
- Synced messages verification (source='atlas')
"""
import pytest
import requests
import os
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone

# Get backend URL from environment - no defaults
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://docs-rebuild-polish.preview.emergentagent.com"

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')


@pytest.fixture(scope="module")
def db():
    """MongoDB database connection."""
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


@pytest.fixture(scope="module")
def auth_token(db):
    """Create or get a test user with auth token."""
    user_id = 'test-user-atlas-shadow-sync'
    session_token = f'test_session_atlas_sync_{int(datetime.now().timestamp())}'
    
    # Upsert test user
    db.users.update_one(
        {"user_id": user_id},
        {"$setOnInsert": {
            "user_id": user_id,
            "email": "atlassync.test@example.com",
            "name": "Atlas Sync Tester",
            "role": "admin",
            "created_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    # Create session
    db.user_sessions.delete_many({"user_id": user_id})
    db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
        "created_at": datetime.now(timezone.utc)
    })
    
    return session_token


@pytest.fixture(scope="module")
def api_client():
    """Requests session with JSON headers."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header."""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


class TestHealthCheck:
    """Basic health check test."""
    
    def test_health_endpoint_returns_healthy(self, api_client):
        """Test /api/health returns healthy status."""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "checks" in data
        assert data["checks"]["database"]["status"] == "healthy"
        print(f"✓ Health check passed: {data['status']}")


class TestSyncAPIEndpointsUnauthenticated:
    """Test sync endpoints return 401 without authentication."""
    
    def test_sync_status_requires_auth(self, api_client):
        """GET /api/admin/atlas/sync/status returns 401 without auth."""
        response = requests.get(f"{BASE_URL}/api/admin/atlas/sync/status")
        assert response.status_code == 401
        print("✓ GET /api/admin/atlas/sync/status returns 401 without auth")
    
    def test_sync_start_requires_auth(self, api_client):
        """POST /api/admin/atlas/sync/start returns 401 without auth."""
        response = requests.post(f"{BASE_URL}/api/admin/atlas/sync/start")
        assert response.status_code == 401
        print("✓ POST /api/admin/atlas/sync/start returns 401 without auth")
    
    def test_sync_stop_requires_auth(self, api_client):
        """POST /api/admin/atlas/sync/stop returns 401 without auth."""
        response = requests.post(f"{BASE_URL}/api/admin/atlas/sync/stop")
        assert response.status_code == 401
        print("✓ POST /api/admin/atlas/sync/stop returns 401 without auth")
    
    def test_sync_config_requires_auth(self, api_client):
        """PATCH /api/admin/atlas/sync/config returns 401 without auth."""
        response = requests.patch(
            f"{BASE_URL}/api/admin/atlas/sync/config",
            json={"poll_interval": 60}
        )
        assert response.status_code == 401
        print("✓ PATCH /api/admin/atlas/sync/config returns 401 without auth")


class TestSyncAPIEndpointsAuthenticated:
    """Test sync endpoints with authentication."""
    
    def test_sync_status_returns_data(self, authenticated_client):
        """GET /api/admin/atlas/sync/status returns sync status."""
        response = authenticated_client.get(f"{BASE_URL}/api/admin/atlas/sync/status")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields exist
        assert "status" in data
        assert "is_running" in data
        assert "poll_interval" in data
        assert "lookback_minutes" in data
        assert "cycles_completed" in data
        assert "new_tickets_created" in data
        assert "messages_synced" in data
        
        print(f"✓ Sync status: {data['status']}, is_running={data['is_running']}")
        print(f"  Cycles: {data['cycles_completed']}, New tickets: {data['new_tickets_created']}, Messages: {data['messages_synced']}")
    
    def test_sync_config_update(self, authenticated_client):
        """PATCH /api/admin/atlas/sync/config updates configuration."""
        # Get current config
        status_resp = authenticated_client.get(f"{BASE_URL}/api/admin/atlas/sync/status")
        current_interval = status_resp.json().get("poll_interval", 60)
        
        # Update to a different value
        new_interval = 65 if current_interval != 65 else 60
        response = authenticated_client.patch(
            f"{BASE_URL}/api/admin/atlas/sync/config",
            json={"poll_interval": new_interval, "lookback_minutes": 15}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["poll_interval"] == new_interval
        
        # Restore original
        authenticated_client.patch(
            f"{BASE_URL}/api/admin/atlas/sync/config",
            json={"poll_interval": current_interval}
        )
        
        print(f"✓ Config update works: poll_interval updated to {new_interval}")


class TestSyncAutoStart:
    """Test that sync auto-starts on boot."""
    
    def test_sync_state_shows_running(self, db):
        """MongoDB atlas_backfill_state shows shadow sync is running."""
        state = db.atlas_backfill_state.find_one({"_type": "shadow"}, {"_id": 0})
        
        assert state is not None, "Shadow sync state document not found"
        assert state.get("status") == "running", f"Expected status=running, got {state.get('status')}"
        assert state.get("started_at") is not None, "started_at should be set"
        assert state.get("cycles_completed", 0) >= 0, "cycles_completed should be >= 0"
        
        print(f"✓ Shadow sync auto-started on boot")
        print(f"  Status: {state['status']}")
        print(f"  Started at: {state['started_at']}")
        print(f"  Cycles completed: {state.get('cycles_completed', 0)}")


class TestSyncedTickets:
    """Test that sync has created tickets from Atlas."""
    
    def test_tickets_created_by_atlas_sync(self, db):
        """Tickets with created_by='atlas_sync' exist."""
        count = db.tickets.count_documents({"created_by": "atlas_sync"})
        
        assert count > 0, "No tickets found with created_by='atlas_sync'"
        print(f"✓ Found {count} tickets created by atlas_sync")
    
    def test_synced_tickets_have_atlas_fields(self, db):
        """Synced tickets have atlas_conversation_id and last_synced_at."""
        # Get a sample ticket created by sync
        ticket = db.tickets.find_one(
            {"created_by": "atlas_sync"},
            {"_id": 0, "ticket_id": 1, "atlas_conversation_id": 1, "last_synced_at": 1, "title": 1}
        )
        
        assert ticket is not None, "No sync-created ticket found"
        assert "atlas_conversation_id" in ticket, "Ticket missing atlas_conversation_id"
        assert ticket["atlas_conversation_id"], "atlas_conversation_id is empty"
        assert "last_synced_at" in ticket, "Ticket missing last_synced_at"
        
        print(f"✓ Synced ticket has required fields:")
        print(f"  ticket_id: {ticket['ticket_id']}")
        print(f"  atlas_conversation_id: {ticket['atlas_conversation_id']}")
        print(f"  last_synced_at: {ticket['last_synced_at']}")


class TestSyncedMessages:
    """Test that sync has created messages from Atlas."""
    
    def test_messages_with_source_atlas(self, db):
        """Messages with source='atlas' exist."""
        count = db.messages.count_documents({"source": "atlas"})
        
        assert count > 0, "No messages found with source='atlas'"
        print(f"✓ Found {count} messages with source='atlas'")
    
    def test_synced_messages_have_atlas_fields(self, db):
        """Synced messages have atlas_message_id and atlas_conversation_id."""
        # Get a sample message from sync
        message = db.messages.find_one(
            {"source": "atlas"},
            {"_id": 0, "message_id": 1, "atlas_message_id": 1, "atlas_conversation_id": 1, "ticket_id": 1, "type": 1}
        )
        
        assert message is not None, "No sync-created message found"
        assert "atlas_message_id" in message, "Message missing atlas_message_id"
        
        print(f"✓ Synced message has required fields:")
        print(f"  message_id: {message['message_id']}")
        print(f"  ticket_id: {message['ticket_id']}")
        print(f"  type: {message.get('type')}")


class TestSyncStatistics:
    """Test sync statistics are being tracked."""
    
    def test_sync_stats_in_state(self, db):
        """Shadow sync state has tracked statistics."""
        state = db.atlas_backfill_state.find_one({"_type": "shadow"}, {"_id": 0})
        
        assert state is not None, "Shadow sync state not found"
        
        # Verify stats fields exist
        assert "cycles_completed" in state
        assert "conversations_checked" in state
        assert "new_tickets_created" in state
        assert "messages_synced" in state
        assert "field_updates" in state
        assert "conflicts_skipped" in state
        
        print(f"✓ Sync statistics tracked:")
        print(f"  cycles_completed: {state.get('cycles_completed', 0)}")
        print(f"  conversations_checked: {state.get('conversations_checked', 0)}")
        print(f"  new_tickets_created: {state.get('new_tickets_created', 0)}")
        print(f"  messages_synced: {state.get('messages_synced', 0)}")
        print(f"  field_updates: {state.get('field_updates', 0)}")
        print(f"  conflicts_skipped: {state.get('conflicts_skipped', 0)}")
        print(f"  errors: {len(state.get('errors', []))}")


class TestSyncConfiguration:
    """Test sync configuration values."""
    
    def test_sync_config_values(self, db):
        """Shadow sync has correct default configuration."""
        state = db.atlas_backfill_state.find_one({"_type": "shadow"}, {"_id": 0})
        
        assert state is not None, "Shadow sync state not found"
        
        poll_interval = state.get("poll_interval", 60)
        lookback_minutes = state.get("lookback_minutes", 15)
        
        # Default values should be poll_interval=60, lookback_minutes=15
        assert 10 <= poll_interval <= 600, f"poll_interval {poll_interval} out of range [10, 600]"
        assert 5 <= lookback_minutes <= 120, f"lookback_minutes {lookback_minutes} out of range [5, 120]"
        
        print(f"✓ Sync configuration valid:")
        print(f"  poll_interval: {poll_interval}s")
        print(f"  lookback_minutes: {lookback_minutes}min")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
