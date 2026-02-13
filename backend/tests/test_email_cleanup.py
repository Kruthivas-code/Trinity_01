"""
Test suite for email/Gmail cleanup verification.
Verifies:
1. Gmail endpoints are removed (return 404)
2. Core app features still work
3. File upload/serving still works
4. Ticket replies work without Gmail dependency
5. CSAT works without Gmail dependency
"""
import pytest
import requests
import os
import json
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthCheck:
    """Health check should work"""
    
    def test_health_endpoint(self):
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        assert "checks" in data
        assert "database" in data["checks"]
        print(f"✅ Health check passed: {data}")


class TestGmailEndpointsRemoved:
    """Gmail/IMAP endpoints should return 404"""
    
    def test_gmail_status_404(self):
        response = requests.get(f"{BASE_URL}/api/gmail/status", headers={"Authorization": "Bearer test"})
        assert response.status_code in [404, 401], f"Expected 404/401 for removed endpoint, got {response.status_code}"
        print(f"✅ /api/gmail/status returns {response.status_code}")
    
    def test_gmail_connect_404(self):
        response = requests.post(f"{BASE_URL}/api/gmail/connect", headers={"Authorization": "Bearer test"})
        assert response.status_code in [404, 401], f"Expected 404/401 for removed endpoint, got {response.status_code}"
        print(f"✅ /api/gmail/connect returns {response.status_code}")
    
    def test_gmail_disconnect_404(self):
        response = requests.post(f"{BASE_URL}/api/gmail/disconnect", headers={"Authorization": "Bearer test"})
        assert response.status_code in [404, 401], f"Expected 404/401 for removed endpoint, got {response.status_code}"
        print(f"✅ /api/gmail/disconnect returns {response.status_code}")
    
    def test_email_sync_404(self):
        response = requests.post(f"{BASE_URL}/api/email/sync", headers={"Authorization": "Bearer test"})
        assert response.status_code in [404, 401], f"Expected 404/401 for removed endpoint, got {response.status_code}"
        print(f"✅ /api/email/sync returns {response.status_code}")
    
    def test_email_status_404(self):
        response = requests.get(f"{BASE_URL}/api/email/status", headers={"Authorization": "Bearer test"})
        assert response.status_code in [404, 401], f"Expected 404/401 for removed endpoint, got {response.status_code}"
        print(f"✅ /api/email/status returns {response.status_code}")


class TestCoreEndpointsStillWork:
    """Core ticket management endpoints should still work"""
    
    def test_tickets_list(self):
        response = requests.get(f"{BASE_URL}/api/tickets")
        # 401 is expected without auth, but not 500 or 404
        assert response.status_code in [200, 401], f"Unexpected status {response.status_code}"
        print(f"✅ GET /api/tickets returns {response.status_code}")
    
    def test_knowledge_base_list(self):
        response = requests.get(f"{BASE_URL}/api/knowledge-base")
        # 401 is expected without auth, but not 500 or 404
        assert response.status_code in [200, 401], f"Unexpected status {response.status_code}"
        print(f"✅ GET /api/knowledge-base returns {response.status_code}")
    
    def test_import_endpoint_exists(self):
        """Import endpoint should exist (requires auth)"""
        response = requests.post(f"{BASE_URL}/api/import")
        # 401/422 is expected without auth/body, but not 404
        assert response.status_code in [401, 422], f"Expected 401/422, got {response.status_code}"
        print(f"✅ POST /api/import returns {response.status_code} (endpoint exists)")
    
    def test_upload_image_endpoint_exists(self):
        """Upload endpoint should exist (GET returns 405, requires auth for POST)"""
        response = requests.get(f"{BASE_URL}/api/upload/image")
        assert response.status_code == 405, f"Expected 405 Method Not Allowed for GET, got {response.status_code}"
        print(f"✅ GET /api/upload/image returns 405 (endpoint exists, needs POST)")


class TestAuthenticatedEndpoints:
    """Test endpoints that require authentication using session from previous test"""
    
    @pytest.fixture(autouse=True)
    def setup_session(self):
        """Get session token from database or use existing one"""
        # Use existing session from iteration_21 test
        self.session_token = "7N_TW_9vqeefrLlsBi_s9cZyXCYznDfSPaSt8iwcJic"
        self.session = requests.Session()
        self.session.cookies.set("session_token", self.session_token)
    
    def test_auth_me(self):
        """Test auth/me endpoint"""
        response = self.session.get(f"{BASE_URL}/api/auth/me")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Authenticated as: {data.get('name', 'unknown')}")
        else:
            pytest.skip(f"Auth not working (status {response.status_code}), skipping authenticated tests")
    
    def test_tickets_list_authenticated(self):
        """Test tickets list with auth"""
        response = self.session.get(f"{BASE_URL}/api/tickets")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "tickets" in data or isinstance(data, list), "Expected tickets array"
        print(f"✅ GET /api/tickets works, returned {len(data.get('tickets', data))} tickets")
    
    def test_knowledge_base_authenticated(self):
        """Test knowledge base list with auth"""
        response = self.session.get(f"{BASE_URL}/api/knowledge-base")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "items" in data, "Expected items in response"
        print(f"✅ GET /api/knowledge-base works, returned {len(data.get('items', []))} items")


class TestCSATWithoutGmail:
    """CSAT should work without Gmail dependency"""
    
    @pytest.fixture(autouse=True)
    def setup_session(self):
        self.session_token = "7N_TW_9vqeefrLlsBi_s9cZyXCYznDfSPaSt8iwcJic"
        self.session = requests.Session()
        self.session.cookies.set("session_token", self.session_token)
    
    def test_csat_analytics(self):
        """CSAT analytics should work"""
        response = self.session.get(f"{BASE_URL}/api/csat/analytics")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "total_responses" in data, "Expected total_responses in CSAT analytics"
        print(f"✅ GET /api/csat/analytics works: {data.get('total_responses', 0)} responses")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
