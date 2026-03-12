"""
Tests for Atlas Admin Control Panel endpoints:
- GET /api/admin/atlas/test - Atlas API connectivity test
- GET /api/admin/atlas/parity - Data parity statistics  
- GET /api/admin/atlas/sync/status - Sync status with full_sync state
All endpoints require authentication.
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestAtlasAdminEndpointsUnauthenticated:
    """Test that all Atlas admin endpoints require authentication"""
    
    def test_atlas_test_requires_auth(self):
        """GET /api/admin/atlas/test returns 401/403 without session"""
        response = requests.get(f"{BASE_URL}/api/admin/atlas/test")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        assert "Not authenticated" in data["detail"] or "auth" in data["detail"].lower()
        print("✓ /api/admin/atlas/test correctly requires authentication")

    def test_atlas_parity_requires_auth(self):
        """GET /api/admin/atlas/parity returns 401/403 without session"""
        response = requests.get(f"{BASE_URL}/api/admin/atlas/parity")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        assert "Not authenticated" in data["detail"] or "auth" in data["detail"].lower()
        print("✓ /api/admin/atlas/parity correctly requires authentication")

    def test_atlas_sync_status_requires_auth(self):
        """GET /api/admin/atlas/sync/status returns 401/403 without session"""
        response = requests.get(f"{BASE_URL}/api/admin/atlas/sync/status")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        assert "Not authenticated" in data["detail"] or "auth" in data["detail"].lower()
        print("✓ /api/admin/atlas/sync/status correctly requires authentication")


@pytest.fixture(scope="module")
def auth_session():
    """Create test user and session for authenticated tests"""
    from pymongo import MongoClient
    import uuid
    
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'test_database')
    client = MongoClient(mongo_url)
    db = client[db_name]
    
    user_id = f"test-user-atlas-{uuid.uuid4().hex[:8]}"
    session_token = f"test_session_atlas_{uuid.uuid4().hex}"
    
    # Create test user
    db.users.insert_one({
        "user_id": user_id,
        "email": f"test.atlas.{uuid.uuid4().hex[:6]}@example.com",
        "name": "Atlas Test User",
        "created_at": datetime.utcnow()
    })
    
    # Create session
    db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": datetime.utcnow() + timedelta(days=1),
        "created_at": datetime.utcnow()
    })
    
    yield {
        "session_token": session_token,
        "user_id": user_id,
        "cookies": {"session_token": session_token}
    }
    
    # Cleanup
    db.users.delete_one({"user_id": user_id})
    db.user_sessions.delete_one({"session_token": session_token})
    client.close()


class TestAtlasApiTestEndpoint:
    """Tests for GET /api/admin/atlas/test - 1-click API health check"""
    
    def test_atlas_test_returns_expected_fields(self, auth_session):
        """Verify /test endpoint returns all expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/test",
            cookies=auth_session["cookies"]
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify required fields exist
        required_fields = ["key_masked", "key_set", "connection", "status_code", 
                         "response_time_ms", "total_conversations", "error"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ /api/admin/atlas/test returns all expected fields: {list(data.keys())}")
        
    def test_atlas_test_connection_status(self, auth_session):
        """Verify connection status is a valid value"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/test",
            cookies=auth_session["cookies"]
        )
        assert response.status_code == 200
        data = response.json()
        
        valid_statuses = ["healthy", "error", "auth_failed", "timeout", "unknown"]
        assert data["connection"] in valid_statuses, f"Invalid connection status: {data['connection']}"
        print(f"✓ Connection status '{data['connection']}' is valid")
        
    def test_atlas_test_key_masked_format(self, auth_session):
        """Verify API key is properly masked"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/test",
            cookies=auth_session["cookies"]
        )
        assert response.status_code == 200
        data = response.json()
        
        if data["key_set"]:
            # Key should be masked like "...XXXXXX"
            assert data["key_masked"].startswith("..."), f"Key not properly masked: {data['key_masked']}"
            assert len(data["key_masked"]) <= 10, "Key mask should not reveal too many characters"
        print(f"✓ API key properly masked: {data['key_masked']}")
        
    def test_atlas_test_response_time_tracked(self, auth_session):
        """Verify response time is tracked when connection succeeds"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/test",
            cookies=auth_session["cookies"]
        )
        assert response.status_code == 200
        data = response.json()
        
        if data["connection"] == "healthy":
            assert data["response_time_ms"] is not None
            assert isinstance(data["response_time_ms"], int)
            assert data["response_time_ms"] > 0
            print(f"✓ Response time tracked: {data['response_time_ms']}ms")
        else:
            print(f"✓ Connection not healthy, response_time_ms may be null")


class TestAtlasParityEndpoint:
    """Tests for GET /api/admin/atlas/parity - Data parity statistics"""
    
    def test_parity_returns_expected_fields(self, auth_session):
        """Verify /parity endpoint returns all expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/parity",
            cookies=auth_session["cookies"]
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify top-level fields
        required_fields = ["trinity_total", "atlas_total", "atlas_linked", "imap_only",
                         "missing_from_trinity", "ticket_ids_matched", "ticket_ids_mismatched",
                         "parity_pct", "full_sync", "users"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ /api/admin/atlas/parity returns all expected fields")
        
    def test_parity_full_sync_structure(self, auth_session):
        """Verify full_sync object has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/parity",
            cookies=auth_session["cookies"]
        )
        assert response.status_code == 200
        data = response.json()
        
        full_sync = data.get("full_sync", {})
        required_full_sync_fields = ["cursor", "total", "completed_passes"]
        for field in required_full_sync_fields:
            assert field in full_sync, f"Missing full_sync field: {field}"
        
        # Verify types
        assert isinstance(full_sync["cursor"], int), "cursor should be int"
        assert isinstance(full_sync["total"], int), "total should be int"
        assert isinstance(full_sync["completed_passes"], int), "completed_passes should be int"
        
        print(f"✓ full_sync has correct structure: cursor={full_sync['cursor']}, total={full_sync['total']}, passes={full_sync['completed_passes']}")
        
    def test_parity_users_structure(self, auth_session):
        """Verify users object has correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/parity",
            cookies=auth_session["cookies"]
        )
        assert response.status_code == 200
        data = response.json()
        
        users = data.get("users", {})
        assert "total" in users, "Missing users.total"
        assert "imported_local_emails" in users, "Missing users.imported_local_emails"
        
        assert isinstance(users["total"], int), "users.total should be int"
        assert isinstance(users["imported_local_emails"], int), "users.imported_local_emails should be int"
        
        print(f"✓ users has correct structure: total={users['total']}, imported_local={users['imported_local_emails']}")
        
    def test_parity_numeric_values(self, auth_session):
        """Verify all numeric fields are integers"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/parity",
            cookies=auth_session["cookies"]
        )
        assert response.status_code == 200
        data = response.json()
        
        int_fields = ["trinity_total", "atlas_total", "atlas_linked", "imap_only",
                     "missing_from_trinity", "ticket_ids_matched", "ticket_ids_mismatched"]
        for field in int_fields:
            assert isinstance(data[field], int), f"{field} should be int, got {type(data[field])}"
        
        # parity_pct can be float
        assert isinstance(data["parity_pct"], (int, float)), "parity_pct should be numeric"
        
        print(f"✓ All numeric fields have correct types")


class TestAtlasSyncStatusEndpoint:
    """Tests for GET /api/admin/atlas/sync/status"""
    
    def test_sync_status_returns_full_sync(self, auth_session):
        """Verify sync/status returns full_sync field"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/sync/status",
            cookies=auth_session["cookies"]
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "full_sync" in data, "Missing full_sync field in sync status"
        
        full_sync = data["full_sync"]
        assert "cursor" in full_sync, "Missing full_sync.cursor"
        assert "total" in full_sync, "Missing full_sync.total"
        assert "completed_passes" in full_sync, "Missing full_sync.completed_passes"
        
        print(f"✓ sync/status includes full_sync with cursor={full_sync['cursor']}, total={full_sync['total']}")
        
    def test_sync_status_phase1_fields(self, auth_session):
        """Verify Phase 1 (realtime) sync fields are present"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/sync/status",
            cookies=auth_session["cookies"]
        )
        assert response.status_code == 200
        data = response.json()
        
        phase1_fields = ["conversations_checked", "new_tickets_created", 
                        "messages_synced", "field_updates", "cycles_completed"]
        for field in phase1_fields:
            assert field in data, f"Missing Phase 1 field: {field}"
            
        print(f"✓ Phase 1 fields present: conversations={data.get('conversations_checked')}, new_tickets={data.get('new_tickets_created')}")
        
    def test_sync_status_config_fields(self, auth_session):
        """Verify config fields are present"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/sync/status",
            cookies=auth_session["cookies"]
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "poll_interval" in data, "Missing poll_interval"
        assert "lookback_minutes" in data, "Missing lookback_minutes"
        assert "is_running" in data, "Missing is_running"
        
        print(f"✓ Config fields: poll_interval={data.get('poll_interval')}s, lookback={data.get('lookback_minutes')}min, running={data.get('is_running')}")
        
    def test_sync_status_is_running_boolean(self, auth_session):
        """Verify is_running is a boolean"""
        response = requests.get(
            f"{BASE_URL}/api/admin/atlas/sync/status",
            cookies=auth_session["cookies"]
        )
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data.get("is_running"), bool), "is_running should be boolean"
        print(f"✓ is_running is boolean: {data.get('is_running')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
