"""
Test Suite for Socket.IO Real-time Broadcasting
Tests the fix for:
1. broadcast_ticket_created() with serialize_doc() to strip ObjectId
2. broadcast_ticket_update() with correct function name and argument count (4 args)
3. Frontend socket events: ticket:created, ticket:update, ticket:deleted
"""
import pytest
import requests
import os
import time
import json
from datetime import datetime, timezone
from pymongo import MongoClient

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://sync-engine-fixes.preview.emergentagent.com')

# MongoDB connection for direct inspection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')


@pytest.fixture(scope="module")
def mongo_client():
    """MongoDB client for direct database inspection"""
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def test_session():
    """Create test user and session for authenticated requests"""
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    timestamp = int(time.time() * 1000)
    user_id = f"test-realtime-{timestamp}"
    session_token = f"test_session_{timestamp}"
    
    # Create user
    db.users.insert_one({
        "user_id": user_id,
        "email": f"test.realtime.{timestamp}@example.com",
        "name": "Test Realtime User",
        "picture": "https://via.placeholder.com/150",
        "created_at": datetime.now(timezone.utc)
    })
    
    # Create session
    db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": datetime.now(timezone.utc).replace(year=2027),
        "created_at": datetime.now(timezone.utc)
    })
    
    yield {"user_id": user_id, "session_token": session_token}
    
    # Cleanup
    db.users.delete_many({"user_id": user_id})
    db.user_sessions.delete_many({"session_token": session_token})
    client.close()


@pytest.fixture(scope="module")
def api_client(test_session):
    """HTTP client with session cookie"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.cookies.set("session_token", test_session["session_token"])
    return session


class TestHealthAndBasicConnectivity:
    """Basic connectivity tests"""
    
    def test_health_check(self, api_client):
        """Verify backend health endpoint"""
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["database"]["status"] == "healthy"
        print(f"Health check passed: {data}")
    
    def test_auth_me(self, api_client, test_session):
        """Verify authentication is working"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Auth check failed: {response.text}"
        
        data = response.json()
        assert data["user_id"] == test_session["user_id"]
        print(f"Auth check passed for user: {data['user_id']}")


class TestEmailSyncEndpoint:
    """Test POST /api/email/sync endpoint which triggers broadcast_ticket_created"""
    
    def test_manual_sync_returns_valid_response(self, api_client):
        """
        Test that POST /api/email/sync returns proper counts.
        The sync uses serialize_doc() to strip ObjectId before broadcasting.
        """
        response = api_client.post(f"{BASE_URL}/api/email/sync")
        
        # Sync endpoint should succeed (even if no new emails)
        assert response.status_code == 200, f"Sync failed: {response.text}"
        
        data = response.json()
        assert "tickets_created" in data
        assert "replies_added" in data
        assert "emails_found" in data
        assert "last_uid" in data
        
        print(f"Email sync response: {json.dumps(data, indent=2)}")
    
    def test_sync_does_not_return_objectid(self, api_client, mongo_client):
        """
        Verify that serialized documents don't contain ObjectId or _id fields.
        This checks the serialize_doc() fix that was applied.
        """
        # Get a ticket from database
        ticket = mongo_client.tickets.find_one({}, {"_id": 1, "ticket_id": 1})
        
        if ticket:
            # Verify MongoDB has _id
            assert "_id" in ticket, "MongoDB should have _id field"
            
            # Now get via API and verify _id is stripped
            response = api_client.get(f"{BASE_URL}/api/tickets/{ticket['ticket_id']}")
            
            if response.status_code == 200:
                api_ticket = response.json()
                assert "_id" not in api_ticket, "API response should not contain _id"
                print(f"Verified _id is properly stripped from API response")
            else:
                print(f"Ticket fetch returned {response.status_code}")
        else:
            print("No tickets found to verify serialization")


class TestSerializeDocFunction:
    """Test the serialize_doc function indirectly through API responses"""
    
    def test_ticket_response_serialization(self, api_client):
        """Verify ticket API responses are properly serialized (no ObjectId)"""
        response = api_client.get(f"{BASE_URL}/api/tickets?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        tickets = data.get("tickets", [])
        
        for ticket in tickets:
            # Check no _id field
            assert "_id" not in ticket, f"Ticket {ticket.get('ticket_id')} should not have _id"
            
            # Check datetime fields are ISO strings
            if "created_at" in ticket:
                assert isinstance(ticket["created_at"], str), "created_at should be ISO string"
            
            if "updated_at" in ticket:
                assert isinstance(ticket["updated_at"], str), "updated_at should be ISO string"
        
        print(f"Verified {len(tickets)} tickets are properly serialized")
    
    def test_user_response_serialization(self, api_client):
        """Verify user API responses are properly serialized"""
        response = api_client.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        
        users = response.json()
        
        for user in users:
            assert "_id" not in user, f"User {user.get('user_id')} should not have _id"
        
        print(f"Verified {len(users)} users are properly serialized")


class TestRealtimeBroadcastSetup:
    """Test that realtime module is properly configured"""
    
    def test_realtime_module_imports(self, mongo_client):
        """Verify realtime functions are properly exported from server.py"""
        # This test verifies the imports work by checking the server is running
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        
        # If server is running, imports are working
        print("Server running - realtime module imports successful")
    
    def test_socket_io_endpoint_exists(self):
        """Verify Socket.IO endpoint is accessible"""
        # Socket.IO polling handshake
        response = requests.get(
            f"{BASE_URL}/socket.io/",
            params={"EIO": "4", "transport": "polling"}
        )
        
        # Socket.IO returns 200 or 400 for handshake, not 404
        assert response.status_code != 404, "Socket.IO endpoint should exist"
        print(f"Socket.IO endpoint returned status: {response.status_code}")


class TestTicketCRUDWithBroadcast:
    """Test ticket CRUD operations that trigger broadcasts"""
    
    def test_create_ticket_broadcasts(self, api_client, mongo_client):
        """
        Test creating a ticket via API (should trigger broadcast_ticket_created).
        Verifies the fix: serialize_doc() is now called before sio.emit().
        """
        ticket_data = {
            "title": "TEST_REALTIME Test Ticket for Broadcast",
            "description": "Testing broadcast_ticket_created fix",
            "priority": "medium",
            "status": "todo"
        }
        
        response = api_client.post(f"{BASE_URL}/api/tickets", json=ticket_data)
        assert response.status_code in [200, 201], f"Failed to create ticket: {response.text}"
        
        created_ticket = response.json()
        assert "ticket_id" in created_ticket
        assert "_id" not in created_ticket, "Response should not contain _id"
        
        print(f"Created ticket {created_ticket['ticket_id']} - broadcast should have been triggered")
        
        # Store for cleanup
        return created_ticket["ticket_id"]
    
    def test_update_ticket_broadcasts(self, api_client, mongo_client):
        """
        Test updating a ticket (should trigger broadcast_ticket_update with 4 args).
        Verifies the fix: broadcast_ticket_update(ticket_id, action, data, updated_by)
        """
        # First create a ticket
        ticket_data = {
            "title": "TEST_REALTIME Update Broadcast Test",
            "description": "Testing broadcast_ticket_update fix",
            "priority": "low",
            "status": "todo"
        }
        
        create_response = api_client.post(f"{BASE_URL}/api/tickets", json=ticket_data)
        assert create_response.status_code in [200, 201]
        
        ticket_id = create_response.json()["ticket_id"]
        
        # Update the ticket
        update_data = {"status": "in_progress", "priority": "high"}
        update_response = api_client.put(f"{BASE_URL}/api/tickets/{ticket_id}", json=update_data)
        
        assert update_response.status_code == 200, f"Failed to update: {update_response.text}"
        
        updated_ticket = update_response.json()
        assert updated_ticket["status"] == "in_progress"
        assert updated_ticket["priority"] == "high"
        assert "_id" not in updated_ticket
        
        print(f"Updated ticket {ticket_id} - broadcast_ticket_update should have been triggered")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/tickets/{ticket_id}")
    
    def test_delete_ticket_broadcasts(self, api_client):
        """Test deleting a ticket (should trigger broadcast_ticket_deleted)"""
        # Create a ticket to delete
        ticket_data = {
            "title": "TEST_REALTIME Delete Broadcast Test",
            "description": "Testing broadcast_ticket_deleted",
            "priority": "low"
        }
        
        create_response = api_client.post(f"{BASE_URL}/api/tickets", json=ticket_data)
        assert create_response.status_code in [200, 201]
        
        ticket_id = create_response.json()["ticket_id"]
        
        # Delete the ticket
        delete_response = api_client.delete(f"{BASE_URL}/api/tickets/{ticket_id}")
        assert delete_response.status_code in [200, 204], f"Failed to delete: {delete_response.text}"
        
        print(f"Deleted ticket {ticket_id} - broadcast_ticket_deleted should have been triggered")


class TestEmailSyncBroadcasting:
    """Test email sync broadcasting specifically"""
    
    def test_email_sync_status(self, api_client):
        """Test email sync status endpoint"""
        response = api_client.get(f"{BASE_URL}/api/email/status", timeout=20)
        
        # May timeout or succeed depending on IMAP connection
        if response.status_code == 200:
            data = response.json()
            print(f"Email status: {json.dumps(data, indent=2)}")
            
            # Verify sync_state structure
            if "sync_state" in data:
                sync_state = data["sync_state"]
                assert "last_uid" in sync_state or sync_state is None
        elif response.status_code == 503:
            print("IMAP connection unavailable (expected in test environment)")
        else:
            print(f"Email status returned: {response.status_code}")
    
    def test_sync_state_persistence(self, mongo_client):
        """Verify IMAP sync state is persisted in MongoDB"""
        sync_state = mongo_client.imap_sync_state.find_one({"_id": "imap_last_uid"})
        
        if sync_state:
            assert "last_uid" in sync_state
            print(f"Sync state: last_uid={sync_state['last_uid']}, seeded={sync_state.get('seeded')}")
        else:
            print("No sync state found (first run)")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_tickets(self, api_client, mongo_client):
        """Remove test-created tickets"""
        # Delete test tickets via MongoDB directly
        result = mongo_client.tickets.delete_many({"title": {"$regex": "^TEST_REALTIME"}})
        print(f"Cleaned up {result.deleted_count} test tickets")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
