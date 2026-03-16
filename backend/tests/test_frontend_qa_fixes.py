"""
Test Frontend QA Audit Fixes - Iteration 81
Tests the 5 fixes from the frontend QA audit:
1. POST /api/auth/shift-start returns 200 with valid session
2. POST /api/auth/shift-start returns 401 without auth
3. Health check endpoint still works
4. Teams API authorization still works
"""

import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestSession:
    """Store test session data"""
    user_id = None
    session_token = None


@pytest.fixture(scope="module")
def test_user_session():
    """Create test user and session for authenticated tests"""
    import pymongo
    client = pymongo.MongoClient("mongodb://localhost:27017")
    db = client["test_database"]
    
    user_id = f"test-qa-fix-{int(datetime.now().timestamp() * 1000)}"
    session_token = f"test_session_fix_{int(datetime.now().timestamp() * 1000)}"
    
    # Create test user
    db.users.insert_one({
        "user_id": user_id,
        "email": f"test.fix.{int(datetime.now().timestamp())}@example.com",
        "name": "Test Fix User",
        "role": "agent",
        "created_at": datetime.utcnow()
    })
    
    # Create session
    db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": datetime.utcnow() + timedelta(days=7),
        "created_at": datetime.utcnow()
    })
    
    TestSession.user_id = user_id
    TestSession.session_token = session_token
    
    yield {"user_id": user_id, "session_token": session_token}
    
    # Cleanup
    db.users.delete_one({"user_id": user_id})
    db.user_sessions.delete_one({"session_token": session_token})
    client.close()


@pytest.fixture(scope="module")
def lead_user_session():
    """Create lead user and session for authorization tests"""
    import pymongo
    client = pymongo.MongoClient("mongodb://localhost:27017")
    db = client["test_database"]
    
    user_id = f"test-lead-{int(datetime.now().timestamp() * 1000)}"
    session_token = f"test_lead_session_{int(datetime.now().timestamp() * 1000)}"
    
    # Create lead user
    db.users.insert_one({
        "user_id": user_id,
        "email": f"test.lead.{int(datetime.now().timestamp())}@example.com",
        "name": "Test Lead User",
        "role": "lead",
        "created_at": datetime.utcnow()
    })
    
    # Create session
    db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": datetime.utcnow() + timedelta(days=7),
        "created_at": datetime.utcnow()
    })
    
    yield {"user_id": user_id, "session_token": session_token}
    
    # Cleanup
    db.users.delete_one({"user_id": user_id})
    db.user_sessions.delete_one({"session_token": session_token})
    client.close()


class TestHealthCheck:
    """Test health check endpoint still works"""
    
    def test_health_endpoint_returns_200(self):
        """GET /api/health should return 200 with healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data.get("status") == "healthy", f"Expected healthy status, got {data}"
        print("✓ Health check returns 200 with healthy status")


class TestShiftStartEndpoint:
    """Test the new /api/auth/shift-start endpoint"""
    
    def test_shift_start_returns_401_without_auth(self):
        """POST /api/auth/shift-start should return 401 without session"""
        response = requests.post(f"{BASE_URL}/api/auth/shift-start")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Shift-start returns 401 without auth")
    
    def test_shift_start_returns_200_with_auth(self, test_user_session):
        """POST /api/auth/shift-start should return 200 with valid session"""
        response = requests.post(
            f"{BASE_URL}/api/auth/shift-start",
            cookies={"session_token": test_user_session["session_token"]}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "tickets_assigned" in data, f"Expected tickets_assigned in response, got {data}"
        assert "ticket_ids" in data, f"Expected ticket_ids in response, got {data}"
        assert isinstance(data["tickets_assigned"], int), "tickets_assigned should be integer"
        assert isinstance(data["ticket_ids"], list), "ticket_ids should be list"
        print(f"✓ Shift-start returns 200 with tickets_assigned={data['tickets_assigned']}")


class TestTeamsAuthorization:
    """Test Teams API authorization still works (requires lead/admin)"""
    
    def test_teams_get_works_for_agent(self, test_user_session):
        """GET /api/teams should work for agents"""
        response = requests.get(
            f"{BASE_URL}/api/teams",
            cookies={"session_token": test_user_session["session_token"]}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ GET /api/teams works for agents")
    
    def test_teams_post_blocked_for_agent(self, test_user_session):
        """POST /api/teams should return 403 for agents"""
        response = requests.post(
            f"{BASE_URL}/api/teams",
            cookies={"session_token": test_user_session["session_token"]},
            json={"name": "Test Team", "description": "Test"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ POST /api/teams returns 403 for agents (authorization working)")
    
    def test_teams_post_allowed_for_lead(self, lead_user_session):
        """POST /api/teams should work for leads"""
        import pymongo
        client = pymongo.MongoClient("mongodb://localhost:27017")
        db = client["test_database"]
        
        response = requests.post(
            f"{BASE_URL}/api/teams",
            cookies={"session_token": lead_user_session["session_token"]},
            json={"name": f"Test Team {int(datetime.now().timestamp())}", "description": "Test"}
        )
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"
        
        # Cleanup created team
        if response.status_code in [200, 201]:
            team_id = response.json().get("team_id")
            if team_id:
                db.teams.delete_one({"team_id": team_id})
        
        client.close()
        print("✓ POST /api/teams works for leads")


class TestAuthMeEndpoint:
    """Test auth/me endpoint"""
    
    def test_auth_me_returns_user_data(self, test_user_session):
        """GET /api/auth/me should return user data with valid session"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            cookies={"session_token": test_user_session["session_token"]}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "user_id" in data, f"Expected user_id in response, got {data}"
        assert "email" in data, f"Expected email in response, got {data}"
        print(f"✓ Auth/me returns user data: {data.get('email')}")
    
    def test_auth_me_returns_401_without_session(self):
        """GET /api/auth/me should return 401 without session"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Auth/me returns 401 without session")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
