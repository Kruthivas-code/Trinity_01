"""
Backend tests for the ticket filter and custom inboxes feature.
Tests:
- GET /api/filter/fields - returns all available filter fields
- POST /api/filter/tickets - various filter scenarios (simple, AND, OR, nested, date, etc.)
- CRUD /api/inboxes - create, list, get, update, delete custom inboxes
- POST /api/inboxes/{id}/share - share inbox with other users
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://thread-sync-1.preview.emergentagent.com")

# MongoDB connection for direct setup/cleanup
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
mongo_client = MongoClient(MONGO_URL)
db = mongo_client[DB_NAME]


class TestSetup:
    """Shared fixtures for testing"""
    
    @staticmethod
    def create_test_user_session():
        """Create a test user and session in MongoDB for authentication"""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        session_token = f"test_session_{uuid.uuid4().hex[:32]}"
        
        user_doc = {
            "user_id": user_id,
            "email": f"{user_id}@test.local",
            "name": "Test User",
            "role": "agent",
            "created_at": datetime.utcnow(),
        }
        db.users.insert_one(user_doc)
        
        session_doc = {
            "session_token": session_token,
            "user_id": user_id,
            "expires_at": datetime.utcnow() + timedelta(hours=24),
            "created_at": datetime.utcnow(),
        }
        db.user_sessions.insert_one(session_doc)
        
        return {"user_id": user_id, "session_token": session_token}
    
    @staticmethod
    def cleanup_test_data(user_id, session_token):
        """Clean up test user and session"""
        db.users.delete_one({"user_id": user_id})
        db.user_sessions.delete_one({"session_token": session_token})
        db.custom_inboxes.delete_many({"owner_id": user_id})


@pytest.fixture(scope="module")
def auth_session():
    """Create authenticated session for tests"""
    test_data = TestSetup.create_test_user_session()
    session = requests.Session()
    session.cookies.set("session_token", test_data["session_token"])
    session.headers.update({"Content-Type": "application/json"})
    
    yield {"session": session, "user_id": test_data["user_id"], "session_token": test_data["session_token"]}
    
    # Cleanup
    TestSetup.cleanup_test_data(test_data["user_id"], test_data["session_token"])


@pytest.fixture(scope="module")
def second_user():
    """Create a second user for sharing tests"""
    test_data = TestSetup.create_test_user_session()
    yield test_data
    TestSetup.cleanup_test_data(test_data["user_id"], test_data["session_token"])


class TestFilterFields:
    """Test GET /api/filter/fields endpoint"""
    
    def test_get_filter_fields_success(self, auth_session):
        """GET /api/filter/fields returns all available filter fields"""
        response = auth_session["session"].get(f"{BASE_URL}/api/filter/fields")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        fields = response.json()
        assert isinstance(fields, list), "Expected list of fields"
        assert len(fields) > 0, "Expected at least some fields"
        
        # Check expected base fields exist
        field_names = [f["field"] for f in fields]
        expected_fields = ["status", "priority", "source", "assignee_id", "created_at", "title"]
        for expected in expected_fields:
            assert expected in field_names, f"Expected field '{expected}' in filter fields"
        
        # Check field structure
        status_field = next((f for f in fields if f["field"] == "status"), None)
        assert status_field is not None
        assert "type" in status_field
        assert "label" in status_field
        assert status_field["type"] == "select"
        assert "options" in status_field
        assert "todo" in status_field["options"]
        
        print(f"SUCCESS: GET /api/filter/fields returns {len(fields)} fields")


class TestFilterTickets:
    """Test POST /api/filter/tickets endpoint with various filter scenarios"""
    
    def test_simple_status_filter(self, auth_session):
        """Simple filter: status=todo returns correct results"""
        payload = {
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "status", "op": "is", "value": "todo"}],
                "groups": []
            },
            "page": 1,
            "limit": 50
        }
        
        response = auth_session["session"].post(f"{BASE_URL}/api/filter/tickets", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "tickets" in data, "Expected 'tickets' in response"
        assert "total" in data, "Expected 'total' in response"
        assert isinstance(data["tickets"], list)
        
        # All returned tickets should have status=todo
        for ticket in data["tickets"]:
            assert ticket.get("status") == "todo", f"Expected status='todo', got {ticket.get('status')}"
        
        print(f"SUCCESS: Simple status filter returned {len(data['tickets'])} tickets, total={data['total']}")
    
    def test_simple_priority_filter(self, auth_session):
        """Simple filter: priority=medium returns correct results"""
        payload = {
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "priority", "op": "is", "value": "medium"}],
                "groups": []
            },
            "page": 1,
            "limit": 50
        }
        
        response = auth_session["session"].post(f"{BASE_URL}/api/filter/tickets", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        for ticket in data["tickets"]:
            assert ticket.get("priority") == "medium", f"Expected priority='medium', got {ticket.get('priority')}"
        
        print(f"SUCCESS: Priority filter returned {len(data['tickets'])} tickets")
    
    def test_and_filter_multiple_conditions(self, auth_session):
        """AND filter: status=todo AND priority=medium"""
        payload = {
            "filter_tree": {
                "logic": "and",
                "conditions": [
                    {"field": "status", "op": "is", "value": "todo"},
                    {"field": "priority", "op": "is", "value": "medium"}
                ],
                "groups": []
            },
            "page": 1,
            "limit": 50
        }
        
        response = auth_session["session"].post(f"{BASE_URL}/api/filter/tickets", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        for ticket in data["tickets"]:
            assert ticket.get("status") == "todo", f"AND filter failed: expected status='todo'"
            assert ticket.get("priority") == "medium", f"AND filter failed: expected priority='medium'"
        
        print(f"SUCCESS: AND filter (status=todo AND priority=medium) returned {len(data['tickets'])} tickets")
    
    def test_or_filter(self, auth_session):
        """OR filter: status=todo OR status=in_progress"""
        payload = {
            "filter_tree": {
                "logic": "or",
                "conditions": [
                    {"field": "status", "op": "is", "value": "todo"},
                    {"field": "status", "op": "is", "value": "in_progress"}
                ],
                "groups": []
            },
            "page": 1,
            "limit": 50
        }
        
        response = auth_session["session"].post(f"{BASE_URL}/api/filter/tickets", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        for ticket in data["tickets"]:
            assert ticket.get("status") in ["todo", "in_progress"], \
                f"OR filter failed: expected status in ['todo', 'in_progress'], got {ticket.get('status')}"
        
        print(f"SUCCESS: OR filter returned {len(data['tickets'])} tickets")
    
    def test_nested_groups(self, auth_session):
        """Nested groups: (status=todo AND priority=medium) OR (status=resolved)"""
        payload = {
            "filter_tree": {
                "logic": "or",
                "conditions": [],
                "groups": [
                    {
                        "logic": "and",
                        "conditions": [
                            {"field": "status", "op": "is", "value": "todo"},
                            {"field": "priority", "op": "is", "value": "medium"}
                        ],
                        "groups": []
                    },
                    {
                        "logic": "and",
                        "conditions": [
                            {"field": "status", "op": "is", "value": "resolved"}
                        ],
                        "groups": []
                    }
                ]
            },
            "page": 1,
            "limit": 50
        }
        
        response = auth_session["session"].post(f"{BASE_URL}/api/filter/tickets", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        for ticket in data["tickets"]:
            is_todo_medium = ticket.get("status") == "todo" and ticket.get("priority") == "medium"
            is_resolved = ticket.get("status") == "resolved"
            assert is_todo_medium or is_resolved, \
                f"Nested groups failed: ticket status={ticket.get('status')}, priority={ticket.get('priority')}"
        
        print(f"SUCCESS: Nested groups filter returned {len(data['tickets'])} tickets")
    
    def test_text_contains_filter(self, auth_session):
        """Text contains filter: title contains 'Test' (case insensitive)"""
        payload = {
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "title", "op": "contains", "value": "Re:"}],
                "groups": []
            },
            "page": 1,
            "limit": 50
        }
        
        response = auth_session["session"].post(f"{BASE_URL}/api/filter/tickets", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        for ticket in data["tickets"]:
            assert "re:" in ticket.get("title", "").lower(), \
                f"Text contains filter failed: 'Re:' not found in title '{ticket.get('title')}'"
        
        print(f"SUCCESS: Text contains filter returned {len(data['tickets'])} tickets")
    
    def test_date_after_filter(self, auth_session):
        """Date filter: created_at after a specific date"""
        # Filter for tickets created after 7 days ago
        past_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
        
        payload = {
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "created_at", "op": "after", "value": past_date}],
                "groups": []
            },
            "page": 1,
            "limit": 50
        }
        
        response = auth_session["session"].post(f"{BASE_URL}/api/filter/tickets", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # All tickets should be created after the date
        past_dt = datetime.fromisoformat(past_date)
        for ticket in data["tickets"]:
            created = datetime.fromisoformat(ticket["created_at"].replace("Z", "+00:00").replace("+00:00", ""))
            assert created > past_dt, f"Date filter failed: {created} is not after {past_dt}"
        
        print(f"SUCCESS: Date after filter returned {len(data['tickets'])} tickets")
    
    def test_is_none_operator(self, auth_session):
        """is_none operator: assignee_id is_none (unassigned tickets)"""
        payload = {
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "assignee_id", "op": "is_none"}],
                "groups": []
            },
            "page": 1,
            "limit": 50
        }
        
        response = auth_session["session"].post(f"{BASE_URL}/api/filter/tickets", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        for ticket in data["tickets"]:
            assert ticket.get("assignee_id") is None, \
                f"is_none operator failed: assignee_id={ticket.get('assignee_id')}"
        
        print(f"SUCCESS: is_none operator returned {len(data['tickets'])} unassigned tickets")
    
    def test_is_not_none_operator(self, auth_session):
        """is_not_none operator: assignee_id is_not_none (assigned tickets)"""
        payload = {
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "assignee_id", "op": "is_not_none"}],
                "groups": []
            },
            "page": 1,
            "limit": 50
        }
        
        response = auth_session["session"].post(f"{BASE_URL}/api/filter/tickets", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        for ticket in data["tickets"]:
            assert ticket.get("assignee_id") is not None, \
                f"is_not_none operator failed: assignee_id={ticket.get('assignee_id')}"
        
        print(f"SUCCESS: is_not_none operator returned {len(data['tickets'])} assigned tickets")
    
    def test_is_one_of_operator(self, auth_session):
        """is_one_of operator: priority in [low, high]"""
        payload = {
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "priority", "op": "is_one_of", "value": ["low", "high"]}],
                "groups": []
            },
            "page": 1,
            "limit": 50
        }
        
        response = auth_session["session"].post(f"{BASE_URL}/api/filter/tickets", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        for ticket in data["tickets"]:
            assert ticket.get("priority") in ["low", "high"], \
                f"is_one_of failed: priority={ticket.get('priority')}"
        
        print(f"SUCCESS: is_one_of operator returned {len(data['tickets'])} tickets")
    
    def test_pagination(self, auth_session):
        """Test pagination parameters work correctly"""
        # Get first page
        payload = {
            "filter_tree": {"logic": "and", "conditions": [], "groups": []},
            "page": 1,
            "limit": 10
        }
        
        response1 = auth_session["session"].post(f"{BASE_URL}/api/filter/tickets", json=payload)
        assert response1.status_code == 200
        data1 = response1.json()
        
        assert data1["page"] == 1
        assert data1["limit"] == 10
        assert len(data1["tickets"]) <= 10
        
        # Check has_more logic
        if data1["total"] > 10:
            assert data1["has_more"] == True
            
            # Get second page
            payload["page"] = 2
            response2 = auth_session["session"].post(f"{BASE_URL}/api/filter/tickets", json=payload)
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Should have different tickets
            ids1 = set(t["ticket_id"] for t in data1["tickets"])
            ids2 = set(t["ticket_id"] for t in data2["tickets"])
            assert ids1.isdisjoint(ids2), "Page 1 and Page 2 should have different tickets"
        
        print(f"SUCCESS: Pagination works correctly (total={data1['total']}, has_more={data1.get('has_more')})")
    
    def test_empty_filter_returns_all(self, auth_session):
        """Empty filter tree returns all non-merged tickets"""
        payload = {
            "filter_tree": {"logic": "and", "conditions": [], "groups": []},
            "page": 1,
            "limit": 100
        }
        
        response = auth_session["session"].post(f"{BASE_URL}/api/filter/tickets", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should exclude merged tickets
        for ticket in data["tickets"]:
            assert ticket.get("status") != "merged", "Merged tickets should be excluded"
        
        print(f"SUCCESS: Empty filter returned {len(data['tickets'])} tickets (excluding merged)")


class TestCustomInboxes:
    """Test custom inboxes CRUD endpoints"""
    
    def test_create_inbox(self, auth_session):
        """POST /api/inboxes creates a new custom inbox"""
        payload = {
            "name": "TEST_High Priority Unassigned",
            "filter_tree": {
                "logic": "and",
                "conditions": [
                    {"field": "priority", "op": "is_one_of", "value": ["high", "urgent"]},
                    {"field": "assignee_id", "op": "is_none"}
                ],
                "groups": []
            },
            "color": "#ef4444"
        }
        
        response = auth_session["session"].post(f"{BASE_URL}/api/inboxes", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "inbox_id" in data, "Expected 'inbox_id' in response"
        assert data["name"] == "TEST_High Priority Unassigned"
        assert data["color"] == "#ef4444"
        assert data["filter_tree"] is not None
        assert data["owner_id"] == auth_session["user_id"]
        
        # Store for later tests
        auth_session["test_inbox_id"] = data["inbox_id"]
        
        print(f"SUCCESS: Created inbox {data['inbox_id']}")
    
    def test_list_inboxes(self, auth_session):
        """GET /api/inboxes returns user's inboxes"""
        response = auth_session["session"].get(f"{BASE_URL}/api/inboxes")
        
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Should contain the inbox we created
        inbox_ids = [i["inbox_id"] for i in data]
        assert auth_session.get("test_inbox_id") in inbox_ids, "Created inbox should be in list"
        
        print(f"SUCCESS: Listed {len(data)} inboxes")
    
    def test_get_single_inbox(self, auth_session):
        """GET /api/inboxes/{id} returns a single inbox"""
        inbox_id = auth_session.get("test_inbox_id")
        assert inbox_id, "Test inbox ID not found"
        
        response = auth_session["session"].get(f"{BASE_URL}/api/inboxes/{inbox_id}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["inbox_id"] == inbox_id
        assert data["name"] == "TEST_High Priority Unassigned"
        
        print(f"SUCCESS: Got inbox {inbox_id}")
    
    def test_get_inbox_tickets(self, auth_session):
        """GET /api/inboxes/{id}/tickets returns filtered tickets"""
        inbox_id = auth_session.get("test_inbox_id")
        assert inbox_id, "Test inbox ID not found"
        
        response = auth_session["session"].get(f"{BASE_URL}/api/inboxes/{inbox_id}/tickets")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
        assert "total" in data
        assert "inbox" in data
        
        # Verify filter was applied
        for ticket in data["tickets"]:
            # Should match: (high OR urgent priority) AND unassigned
            assert ticket.get("priority") in ["high", "urgent"] or ticket.get("assignee_id") is None
        
        print(f"SUCCESS: Got {len(data['tickets'])} tickets for inbox")
    
    def test_update_inbox(self, auth_session):
        """PUT /api/inboxes/{id} updates inbox"""
        inbox_id = auth_session.get("test_inbox_id")
        assert inbox_id, "Test inbox ID not found"
        
        payload = {
            "name": "TEST_Updated Inbox Name",
            "color": "#3b82f6"
        }
        
        response = auth_session["session"].put(f"{BASE_URL}/api/inboxes/{inbox_id}", json=payload)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "TEST_Updated Inbox Name"
        assert data["color"] == "#3b82f6"
        
        # Verify with GET
        verify_response = auth_session["session"].get(f"{BASE_URL}/api/inboxes/{inbox_id}")
        verify_data = verify_response.json()
        assert verify_data["name"] == "TEST_Updated Inbox Name"
        
        print(f"SUCCESS: Updated inbox {inbox_id}")
    
    def test_update_inbox_filters(self, auth_session):
        """PUT /api/inboxes/{id} can update filter_tree"""
        inbox_id = auth_session.get("test_inbox_id")
        assert inbox_id, "Test inbox ID not found"
        
        payload = {
            "filter_tree": {
                "logic": "and",
                "conditions": [
                    {"field": "status", "op": "is", "value": "todo"}
                ],
                "groups": []
            }
        }
        
        response = auth_session["session"].put(f"{BASE_URL}/api/inboxes/{inbox_id}", json=payload)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["filter_tree"]["conditions"][0]["field"] == "status"
        assert data["filter_tree"]["conditions"][0]["value"] == "todo"
        
        print(f"SUCCESS: Updated inbox filters")
    
    def test_share_inbox(self, auth_session, second_user):
        """POST /api/inboxes/{id}/share creates decoupled copies"""
        inbox_id = auth_session.get("test_inbox_id")
        assert inbox_id, "Test inbox ID not found"
        
        payload = {
            "user_ids": [second_user["user_id"]]
        }
        
        response = auth_session["session"].post(f"{BASE_URL}/api/inboxes/{inbox_id}/share", json=payload)
        
        assert response.status_code == 200
        
        data = response.json()
        assert "shared_with" in data
        assert "total" in data
        assert data["total"] >= 1
        
        # Verify the copy was created for second user
        if data["shared_with"]:
            copy_inbox_id = data["shared_with"][0]["inbox_id"]
            
            # Second user should be able to see it
            second_session = requests.Session()
            second_session.cookies.set("session_token", second_user["session_token"])
            
            verify_response = second_session.get(f"{BASE_URL}/api/inboxes/{copy_inbox_id}")
            assert verify_response.status_code == 200
            
            copy_data = verify_response.json()
            assert copy_data["owner_id"] == second_user["user_id"]
            assert "shared_from" in copy_data
            assert copy_data["shared_from"]["shared_by"] == auth_session["user_id"]
        
        print(f"SUCCESS: Shared inbox with {data['total']} user(s)")
    
    def test_delete_inbox(self, auth_session):
        """DELETE /api/inboxes/{id} deletes inbox"""
        inbox_id = auth_session.get("test_inbox_id")
        assert inbox_id, "Test inbox ID not found"
        
        response = auth_session["session"].delete(f"{BASE_URL}/api/inboxes/{inbox_id}")
        
        assert response.status_code == 200
        
        # Verify deletion
        verify_response = auth_session["session"].get(f"{BASE_URL}/api/inboxes/{inbox_id}")
        assert verify_response.status_code == 404, "Deleted inbox should return 404"
        
        print(f"SUCCESS: Deleted inbox {inbox_id}")
    
    def test_inbox_not_found(self, auth_session):
        """GET/PUT/DELETE for non-existent inbox returns 404"""
        fake_id = "inbox_nonexistent123"
        
        response = auth_session["session"].get(f"{BASE_URL}/api/inboxes/{fake_id}")
        assert response.status_code == 404
        
        response = auth_session["session"].put(f"{BASE_URL}/api/inboxes/{fake_id}", json={"name": "Test"})
        assert response.status_code == 404
        
        response = auth_session["session"].delete(f"{BASE_URL}/api/inboxes/{fake_id}")
        assert response.status_code == 404
        
        print("SUCCESS: Non-existent inbox returns 404")


class TestUnauthorized:
    """Test authentication is required for filter endpoints"""
    
    def test_filter_fields_unauthorized(self):
        """GET /api/filter/fields requires authentication"""
        response = requests.get(f"{BASE_URL}/api/filter/fields")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("SUCCESS: /api/filter/fields requires auth")
    
    def test_filter_tickets_unauthorized(self):
        """POST /api/filter/tickets requires authentication"""
        response = requests.post(f"{BASE_URL}/api/filter/tickets", json={
            "filter_tree": {"logic": "and", "conditions": [], "groups": []}
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("SUCCESS: /api/filter/tickets requires auth")
    
    def test_inboxes_unauthorized(self):
        """Inbox endpoints require authentication"""
        response = requests.get(f"{BASE_URL}/api/inboxes")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("SUCCESS: /api/inboxes requires auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
