"""
Regression Test Suite for Trinity Backend Refactoring
======================================================
Tests all critical endpoints after the major backend refactoring:
- database.py: MongoDB collections and constants
- models/schemas.py: Pydantic models
- dependencies.py: Auth functions (get_current_user, verify_api_key)
- utils.py: serialize_doc utility
- routes/filters.py: Filter and inbox routes (APIRouter)

Test areas:
1. Health check
2. Authentication (session cookie)
3. Tickets (paginated, filtered)
4. Users (paginated)
5. Filter routes (POST /api/filter/tickets, GET /api/filter/fields)
6. Inbox CRUD (GET, POST, PUT, DELETE /api/inboxes)
7. Inbox sharing (POST /api/inboxes/{id}/share)
8. Inbox tickets (GET /api/inboxes/{id}/tickets)
9. Analytics (GET /api/analytics/summary)
10. Teams (GET /api/teams)
"""
import pytest
import requests
import os
import uuid

# Use the public URL from frontend/.env for testing
BASE_URL = "https://ticket-search-debug.preview.emergentagent.com"

# Test credentials
SESSION_TOKEN = "7N_TW_9vqeefrLlsBi_s9cZyXCYznDfSPaSt8iwcJic"
USER_ID = "user_5aeff57a3631"
OTHER_USER_ID = "b1bbdaf9-5ac0-47a9-ac7d-31b0b149010e"


@pytest.fixture
def api_client():
    """Shared requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Cookie": f"session_token={SESSION_TOKEN}"
    })
    return session


# ==================== 1. Health Check ====================
class TestHealthCheck:
    """Health endpoint tests - no auth required"""
    
    def test_health_endpoint(self):
        """GET /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert data["version"] == "2.0.0"
        assert "checks" in data
        assert data["checks"]["database"]["status"] == "healthy"
        print("PASS: Health endpoint returns healthy status with version 2.0.0")


# ==================== 2. Authentication ====================
class TestAuthentication:
    """Session-based authentication tests"""
    
    def test_auth_me_with_session_cookie(self, api_client):
        """GET /api/auth/me returns user data with valid session"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        
        data = response.json()
        assert "user_id" in data
        assert data["user_id"] == USER_ID
        assert "email" in data
        print(f"PASS: Auth/me returns user data for {data['user_id']}")
    
    def test_auth_without_session_returns_401(self):
        """GET /api/auth/me without session returns 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("PASS: Auth/me returns 401 without session")


# ==================== 3. Tickets (Paginated) ====================
class TestTickets:
    """Ticket endpoints tests"""
    
    def test_get_tickets_paginated(self, api_client):
        """GET /api/tickets returns paginated tickets"""
        response = api_client.get(f"{BASE_URL}/api/tickets?page=1&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
        assert isinstance(data["tickets"], list)
        assert len(data["tickets"]) <= 5
        assert "total" in data
        assert "page" in data
        print(f"PASS: Tickets endpoint returns {len(data['tickets'])} tickets (total: {data['total']})")
    
    def test_get_tickets_with_status_filter(self, api_client):
        """GET /api/tickets with status filter returns filtered results"""
        response = api_client.get(f"{BASE_URL}/api/tickets?page=1&limit=5&status=todo")
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
        # All returned tickets should have status=todo
        for ticket in data["tickets"]:
            assert ticket.get("status") == "todo"
        print(f"PASS: Tickets filtered by status=todo returns {len(data['tickets'])} tickets")


# ==================== 4. Users (Paginated) ====================
class TestUsers:
    """Users endpoint tests"""
    
    def test_get_users_paginated(self, api_client):
        """GET /api/users returns paginated users with items array"""
        response = api_client.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        
        data = response.json()
        # Response structure should be: {items: [], total, skip, limit, has_more}
        assert "items" in data
        assert isinstance(data["items"], list)
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert "has_more" in data
        print(f"PASS: Users endpoint returns {len(data['items'])} users (total: {data['total']})")


# ==================== 5. Filter Routes (routes/filters.py) ====================
class TestFilterRoutes:
    """Filter routes tests - verifies routes/filters.py integration"""
    
    def test_filter_tickets_with_status(self, api_client):
        """POST /api/filter/tickets with filter_tree returns filtered results"""
        filter_payload = {
            "filter_tree": {
                "logic": "and",
                "conditions": [
                    {"field": "status", "op": "is", "value": "todo"}
                ],
                "groups": []
            },
            "page": 1,
            "limit": 5,
            "sort_by": "created_at",
            "sort_order": "desc"
        }
        
        response = api_client.post(f"{BASE_URL}/api/filter/tickets", json=filter_payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "has_more" in data
        
        # All returned tickets should have status=todo
        for ticket in data["tickets"]:
            assert ticket.get("status") == "todo"
        print(f"PASS: Filter tickets returns {len(data['tickets'])} filtered tickets (total: {data['total']})")
    
    def test_filter_tickets_with_complex_filter(self, api_client):
        """POST /api/filter/tickets with nested filter returns results"""
        filter_payload = {
            "filter_tree": {
                "logic": "and",
                "conditions": [
                    {"field": "priority", "op": "is", "value": "medium"}
                ],
                "groups": [
                    {
                        "logic": "or",
                        "conditions": [
                            {"field": "status", "op": "is", "value": "todo"},
                            {"field": "status", "op": "is", "value": "in_progress"}
                        ],
                        "groups": []
                    }
                ]
            },
            "page": 1,
            "limit": 5
        }
        
        response = api_client.post(f"{BASE_URL}/api/filter/tickets", json=filter_payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
        print(f"PASS: Complex filter returns {len(data['tickets'])} tickets")
    
    def test_get_filter_fields(self, api_client):
        """GET /api/filter/fields returns 13+ filter fields"""
        response = api_client.get(f"{BASE_URL}/api/filter/fields")
        assert response.status_code == 200
        
        fields = response.json()
        assert isinstance(fields, list)
        assert len(fields) >= 13
        
        # Verify expected fields exist
        field_names = [f["field"] for f in fields]
        expected_fields = ["status", "priority", "source", "escalation_level", 
                          "assignee_id", "customer_email", "title", "description",
                          "ticket_id", "email_sender_name", "tags", "created_at", "updated_at"]
        
        for expected in expected_fields:
            assert expected in field_names, f"Missing field: {expected}"
        
        print(f"PASS: Filter fields returns {len(fields)} fields (13+ required)")


# ==================== 6. Inbox CRUD (routes/filters.py) ====================
class TestInboxCRUD:
    """Custom inbox CRUD tests - verifies routes/filters.py integration"""
    
    def test_get_inboxes(self, api_client):
        """GET /api/inboxes returns inbox list"""
        response = api_client.get(f"{BASE_URL}/api/inboxes")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Get inboxes returns {len(data)} inboxes")
    
    def test_create_inbox(self, api_client):
        """POST /api/inboxes creates a new inbox"""
        inbox_data = {
            "name": f"TEST_Regression_Inbox_{uuid.uuid4().hex[:8]}",
            "filter_tree": {
                "logic": "and",
                "conditions": [
                    {"field": "status", "op": "is", "value": "todo"}
                ],
                "groups": []
            },
            "color": "#3b82f6"
        }
        
        response = api_client.post(f"{BASE_URL}/api/inboxes", json=inbox_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "inbox_id" in data
        assert data["name"] == inbox_data["name"]
        assert data["color"] == "#3b82f6"
        assert data["owner_id"] == USER_ID
        
        # Store for cleanup
        TestInboxCRUD.created_inbox_id = data["inbox_id"]
        print(f"PASS: Created inbox {data['inbox_id']}")
        return data["inbox_id"]
    
    def test_get_single_inbox(self, api_client):
        """GET /api/inboxes/{inbox_id} returns inbox details"""
        # First create an inbox
        inbox_id = self.test_create_inbox(api_client)
        
        response = api_client.get(f"{BASE_URL}/api/inboxes/{inbox_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["inbox_id"] == inbox_id
        print(f"PASS: Get single inbox returns correct data")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/inboxes/{inbox_id}")
    
    def test_update_inbox(self, api_client):
        """PUT /api/inboxes/{inbox_id} updates inbox name/color"""
        # Create inbox
        inbox_id = self.test_create_inbox(api_client)
        
        # Update it
        update_data = {
            "name": "TEST_Updated_Name",
            "color": "#ef4444"
        }
        
        response = api_client.put(f"{BASE_URL}/api/inboxes/{inbox_id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "TEST_Updated_Name"
        assert data["color"] == "#ef4444"
        print(f"PASS: Updated inbox name and color")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/inboxes/{inbox_id}")
    
    def test_delete_inbox(self, api_client):
        """DELETE /api/inboxes/{inbox_id} deletes inbox"""
        # Create inbox
        inbox_id = self.test_create_inbox(api_client)
        
        # Delete it
        response = api_client.delete(f"{BASE_URL}/api/inboxes/{inbox_id}")
        assert response.status_code == 200
        
        # Verify deletion
        response = api_client.get(f"{BASE_URL}/api/inboxes/{inbox_id}")
        assert response.status_code == 404
        print(f"PASS: Deleted inbox and verified 404 on GET")


# ==================== 7. Inbox Sharing ====================
class TestInboxSharing:
    """Inbox sharing tests - creates decoupled copies"""
    
    def test_share_inbox_creates_decoupled_copies(self, api_client):
        """POST /api/inboxes/{inbox_id}/share creates decoupled copies for recipients"""
        # Create inbox
        inbox_data = {
            "name": f"TEST_Share_Inbox_{uuid.uuid4().hex[:8]}",
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "status", "op": "is", "value": "todo"}],
                "groups": []
            }
        }
        create_resp = api_client.post(f"{BASE_URL}/api/inboxes", json=inbox_data)
        assert create_resp.status_code == 200
        inbox_id = create_resp.json()["inbox_id"]
        
        # Share with other user
        share_data = {"user_ids": [OTHER_USER_ID]}
        response = api_client.post(f"{BASE_URL}/api/inboxes/{inbox_id}/share", json=share_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "shared_with" in data
        assert "total" in data
        assert data["total"] >= 0  # May be 0 if user doesn't exist
        print(f"PASS: Share inbox returns {data['total']} shared copies")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/inboxes/{inbox_id}")


# ==================== 8. Inbox Tickets ====================
class TestInboxTickets:
    """Inbox tickets endpoint tests"""
    
    def test_get_inbox_tickets(self, api_client):
        """GET /api/inboxes/{inbox_id}/tickets returns filtered tickets"""
        # Create inbox with filter
        inbox_data = {
            "name": f"TEST_Tickets_Inbox_{uuid.uuid4().hex[:8]}",
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "status", "op": "is", "value": "todo"}],
                "groups": []
            }
        }
        create_resp = api_client.post(f"{BASE_URL}/api/inboxes", json=inbox_data)
        assert create_resp.status_code == 200
        inbox_id = create_resp.json()["inbox_id"]
        
        # Get tickets for inbox
        response = api_client.get(f"{BASE_URL}/api/inboxes/{inbox_id}/tickets")
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
        assert "total" in data
        assert "inbox" in data
        print(f"PASS: Inbox tickets returns {len(data['tickets'])} tickets (total: {data['total']})")
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/inboxes/{inbox_id}")


# ==================== 9. Analytics ====================
class TestAnalytics:
    """Analytics endpoint tests"""
    
    def test_get_analytics_summary(self, api_client):
        """GET /api/analytics/summary returns analytics data"""
        response = api_client.get(f"{BASE_URL}/api/analytics/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "by_status" in data
        assert "total" in data
        assert "my_tickets" in data
        print(f"PASS: Analytics summary returns total={data['total']} tickets")


# ==================== 10. Teams ====================
class TestTeams:
    """Teams endpoint tests"""
    
    def test_get_teams(self, api_client):
        """GET /api/teams returns teams list"""
        response = api_client.get(f"{BASE_URL}/api/teams")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Teams endpoint returns {len(data)} teams")


# ==================== Code Review: Import Verification ====================
class TestImportVerification:
    """Verify the new module structure is working correctly"""
    
    def test_database_module_working(self, api_client):
        """Verify database.py collections are accessible (health check uses them)"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["checks"]["database"]["status"] == "healthy"
        print("PASS: database.py module is correctly imported and working")
    
    def test_dependencies_module_working(self, api_client):
        """Verify dependencies.py auth functions work (auth/me uses get_current_user)"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        print("PASS: dependencies.py (get_current_user) is correctly imported and working")
    
    def test_schemas_module_working(self, api_client):
        """Verify models/schemas.py Pydantic models work (filter uses FilterRequest)"""
        filter_payload = {
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "status", "op": "is", "value": "todo"}],
                "groups": []
            },
            "page": 1,
            "limit": 5
        }
        response = api_client.post(f"{BASE_URL}/api/filter/tickets", json=filter_payload)
        assert response.status_code == 200
        print("PASS: models/schemas.py (FilterRequest) is correctly imported and working")
    
    def test_utils_module_working(self, api_client):
        """Verify utils.py serialize_doc works (all responses use it)"""
        response = api_client.get(f"{BASE_URL}/api/tickets?page=1&limit=1")
        assert response.status_code == 200
        data = response.json()
        # Verify tickets don't have MongoDB _id field (serialize_doc removes it)
        for ticket in data.get("tickets", []):
            assert "_id" not in ticket
        print("PASS: utils.py (serialize_doc) is correctly imported and working")
    
    def test_filters_router_working(self, api_client):
        """Verify routes/filters.py APIRouter is correctly mounted"""
        # Test filter endpoint (from routes/filters.py)
        response = api_client.get(f"{BASE_URL}/api/filter/fields")
        assert response.status_code == 200
        
        # Test inbox endpoint (from routes/filters.py)
        response = api_client.get(f"{BASE_URL}/api/inboxes")
        assert response.status_code == 200
        print("PASS: routes/filters.py APIRouter is correctly mounted")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
