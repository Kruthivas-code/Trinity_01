"""
Regression Test Suite for Trinity Backend Refactoring Phase 2
==============================================================
Tests all critical endpoints after the major backend refactoring phase 2:
- routes/canned_responses.py: Canned responses CRUD (202 lines)
- routes/webhooks.py: Webhooks API + trigger-auto-close (325 lines)
- routes/customers.py: Customer CRUD (426 lines)
- routes/csat.py: CSAT system (545 lines)
- utils.py: Now 361 lines with serialize_doc, log_ticket_change, deliver_webhook, etc.
- server.py: Reduced from 10,708 to 6,774 lines

Routes that were accidentally moved and moved back to server.py:
- POST /api/tickets/bulk-update
- POST /api/tickets/{ticket_id}/merge-consecutive
- GET /api/notifications

Test areas:
1. Health check
2. Authentication (session cookie)
3. Tickets (paginated, filtered)
4. Users (paginated)
5. Filter routes (POST /api/filter/tickets, GET /api/filter/fields)
6. Inbox CRUD (GET, POST, PUT, DELETE /api/inboxes)
7. Canned responses (routes/canned_responses.py)
8. Webhooks (routes/webhooks.py)
9. Customers (routes/customers.py)
10. CSAT analytics (routes/csat.py)
11. Analytics summary
12. Admin auto-close status
13. Bulk update (server.py - was accidentally moved)
14. Notifications (server.py - was accidentally moved)
15. Import verification for all modules
"""
import pytest
import requests
import os
import uuid

# Use the public URL from frontend/.env for testing
BASE_URL = "https://kb-wysiwyg-upgrade.preview.emergentagent.com"

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
    
    def test_inbox_crud_lifecycle(self, api_client):
        """POST -> PUT -> DELETE inbox lifecycle"""
        # CREATE
        inbox_data = {
            "name": f"TEST_Phase2_Inbox_{uuid.uuid4().hex[:8]}",
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
        inbox_id = data["inbox_id"]
        print(f"PASS: Created inbox {inbox_id}")
        
        # UPDATE
        update_data = {"name": "TEST_Updated_Phase2", "color": "#ef4444"}
        response = api_client.put(f"{BASE_URL}/api/inboxes/{inbox_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TEST_Updated_Phase2"
        print(f"PASS: Updated inbox {inbox_id}")
        
        # DELETE
        response = api_client.delete(f"{BASE_URL}/api/inboxes/{inbox_id}")
        assert response.status_code == 200
        
        # Verify deletion
        response = api_client.get(f"{BASE_URL}/api/inboxes/{inbox_id}")
        assert response.status_code == 404
        print(f"PASS: Deleted inbox {inbox_id} and verified 404")


# ==================== 7. Canned Responses (routes/canned_responses.py) ====================
class TestCannedResponses:
    """Canned responses tests - verifies routes/canned_responses.py integration"""
    
    def test_get_canned_responses(self, api_client):
        """GET /api/canned-responses returns canned responses"""
        response = api_client.get(f"{BASE_URL}/api/canned-responses")
        assert response.status_code == 200
        
        data = response.json()
        # Response structure: {global: [], personal: [], all: []}
        assert "global" in data
        assert "personal" in data
        assert "all" in data
        print(f"PASS: Canned responses returns {len(data['all'])} total responses")
    
    def test_canned_responses_crud(self, api_client):
        """POST -> PUT -> DELETE canned response lifecycle"""
        # CREATE
        create_data = {
            "title": f"TEST_Phase2_Response_{uuid.uuid4().hex[:8]}",
            "shortcode": f"test{uuid.uuid4().hex[:6]}",
            "content": "This is a test canned response for phase 2 regression testing.",
            "scope": "personal"
        }
        
        response = api_client.post(f"{BASE_URL}/api/canned-responses", json=create_data)
        assert response.status_code == 200
        data = response.json()
        assert "response_id" in data
        response_id = data["response_id"]
        print(f"PASS: Created canned response {response_id}")
        
        # UPDATE
        update_data = {"title": "TEST_Updated_Response"}
        response = api_client.put(f"{BASE_URL}/api/canned-responses/{response_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "TEST_Updated_Response"
        print(f"PASS: Updated canned response {response_id}")
        
        # DELETE
        response = api_client.delete(f"{BASE_URL}/api/canned-responses/{response_id}")
        assert response.status_code == 200
        print(f"PASS: Deleted canned response {response_id}")


# ==================== 8. Webhooks (routes/webhooks.py) ====================
class TestWebhooks:
    """Webhooks tests - verifies routes/webhooks.py integration"""
    
    def test_get_webhook_events(self, api_client):
        """GET /api/webhooks/events returns 13 event types"""
        response = api_client.get(f"{BASE_URL}/api/webhooks/events")
        assert response.status_code == 200
        
        data = response.json()
        assert "events" in data
        assert "descriptions" in data
        
        events = data["events"]
        assert len(events) == 13
        
        # Verify expected events
        expected_events = [
            "ticket.created", "ticket.updated", "ticket.assigned",
            "ticket.status_changed", "ticket.resolved", "ticket.closed",
            "ticket.deleted", "ticket.reply_added", "ticket.note_added",
            "customer.created", "customer.updated", "sla.breach", "sla.warning"
        ]
        
        for expected in expected_events:
            assert expected in events, f"Missing event: {expected}"
        
        print(f"PASS: Webhook events returns {len(events)} event types (13 expected)")


# ==================== 9. Customers (routes/customers.py) ====================
class TestCustomers:
    """Customer tests - verifies routes/customers.py integration"""
    
    def test_get_customers(self, api_client):
        """GET /api/customers returns customer list"""
        response = api_client.get(f"{BASE_URL}/api/customers")
        assert response.status_code == 200
        
        data = response.json()
        assert "customers" in data
        assert "total" in data
        assert "limit" in data
        assert "skip" in data
        
        print(f"PASS: Customers endpoint returns {len(data['customers'])} customers (total: {data['total']})")
    
    def test_get_customers_with_search(self, api_client):
        """GET /api/customers with search filter"""
        response = api_client.get(f"{BASE_URL}/api/customers?search=test")
        assert response.status_code == 200
        
        data = response.json()
        assert "customers" in data
        print(f"PASS: Customer search returns {len(data['customers'])} results")


# ==================== 10. CSAT Analytics (routes/csat.py) ====================
class TestCSATAnalytics:
    """CSAT tests - verifies routes/csat.py integration"""
    
    def test_get_csat_analytics(self, api_client):
        """GET /api/csat/analytics returns CSAT data"""
        response = api_client.get(f"{BASE_URL}/api/csat/analytics")
        assert response.status_code == 200
        
        data = response.json()
        assert "period_days" in data
        assert "total_responses" in data
        assert "average_rating" in data or data["average_rating"] is None
        assert "rating_distribution" in data
        assert "satisfaction_rate" in data or data["satisfaction_rate"] is None
        assert "low_ratings" in data
        assert "by_agent" in data
        
        print(f"PASS: CSAT analytics returns data for {data['period_days']} days period")


# ==================== 11. Analytics Summary ====================
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


# ==================== 12. Admin Auto-Close Status ====================
class TestAdminAutoClose:
    """Admin auto-close status tests"""
    
    def test_get_auto_close_status(self, api_client):
        """GET /api/admin/auto-close-status returns auto-close status"""
        response = api_client.get(f"{BASE_URL}/api/admin/auto-close-status")
        assert response.status_code == 200
        
        data = response.json()
        # Response structure: {pending_auto_close: int, pending_tickets: [], recently_resolved_count: int, recently_auto_closed: []}
        assert "pending_auto_close" in data
        assert "pending_tickets" in data
        assert "recently_resolved_count" in data
        print(f"PASS: Auto-close status returns pending={data['pending_auto_close']}, recently_resolved={data['recently_resolved_count']}")


# ==================== 13. Bulk Update (server.py - was accidentally moved) ====================
class TestBulkUpdate:
    """Bulk update tests - verifies route is back in server.py"""
    
    def test_bulk_update_endpoint_exists(self, api_client):
        """POST /api/tickets/bulk-update endpoint exists and works correctly"""
        # First get a ticket ID to use for testing
        tickets_response = api_client.get(f"{BASE_URL}/api/tickets?page=1&limit=1")
        assert tickets_response.status_code == 200
        
        tickets = tickets_response.json().get("tickets", [])
        if tickets:
            ticket_id = tickets[0].get("ticket_id")
            current_status = tickets[0].get("status", "todo")
            
            # BulkUpdateRequest expects: {ticket_ids: [], updates: {}}
            bulk_data = {
                "ticket_ids": [ticket_id],
                "updates": {"status": current_status}  # Keep same status to avoid side effects
            }
            
            response = api_client.post(f"{BASE_URL}/api/tickets/bulk-update", json=bulk_data)
            assert response.status_code == 200
            
            data = response.json()
            # Response has: {matched: int, modified: int, message: str}
            assert "matched" in data or "modified" in data or "updated_count" in data
            print(f"PASS: Bulk update endpoint works, response: {data.get('message', 'OK')}")
        else:
            # Empty list returns 400, which is correct behavior
            bulk_data = {
                "ticket_ids": [],
                "updates": {"status": "todo"}
            }
            
            response = api_client.post(f"{BASE_URL}/api/tickets/bulk-update", json=bulk_data)
            # 400 is acceptable for empty ticket_ids
            assert response.status_code in [200, 400]
            print("PASS: Bulk update endpoint exists (no tickets to test with)")


# ==================== 14. Notifications (server.py - was accidentally moved) ====================
class TestNotifications:
    """Notifications tests - verifies route is back in server.py"""
    
    def test_get_notifications(self, api_client):
        """GET /api/notifications returns notifications list"""
        response = api_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Notifications endpoint returns {len(data)} notifications")


# ==================== 15. Teams ====================
class TestTeams:
    """Teams endpoint tests"""
    
    def test_get_teams(self, api_client):
        """GET /api/teams returns teams list"""
        response = api_client.get(f"{BASE_URL}/api/teams")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Teams endpoint returns {len(data)} teams")


# ==================== 16. Import Verification ====================
class TestImportVerification:
    """Verify all extracted modules are working correctly"""
    
    def test_database_module_working(self, api_client):
        """Verify database.py collections are accessible"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("PASS: database.py module is correctly imported and working")
    
    def test_dependencies_module_working(self, api_client):
        """Verify dependencies.py auth functions work"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        print("PASS: dependencies.py (get_current_user) is correctly imported and working")
    
    def test_utils_module_working(self, api_client):
        """Verify utils.py functions work (serialize_doc, log_ticket_change, etc.)"""
        response = api_client.get(f"{BASE_URL}/api/tickets?page=1&limit=1")
        assert response.status_code == 200
        data = response.json()
        # Verify tickets don't have MongoDB _id field (serialize_doc removes it)
        for ticket in data.get("tickets", []):
            assert "_id" not in ticket
        print("PASS: utils.py is correctly imported and working")
    
    def test_filters_router_working(self, api_client):
        """Verify routes/filters.py APIRouter is correctly mounted"""
        response = api_client.get(f"{BASE_URL}/api/filter/fields")
        assert response.status_code == 200
        response = api_client.get(f"{BASE_URL}/api/inboxes")
        assert response.status_code == 200
        print("PASS: routes/filters.py APIRouter is correctly mounted")
    
    def test_canned_responses_router_working(self, api_client):
        """Verify routes/canned_responses.py APIRouter is correctly mounted"""
        response = api_client.get(f"{BASE_URL}/api/canned-responses")
        assert response.status_code == 200
        print("PASS: routes/canned_responses.py APIRouter is correctly mounted")
    
    def test_webhooks_router_working(self, api_client):
        """Verify routes/webhooks.py APIRouter is correctly mounted"""
        response = api_client.get(f"{BASE_URL}/api/webhooks/events")
        assert response.status_code == 200
        print("PASS: routes/webhooks.py APIRouter is correctly mounted")
    
    def test_customers_router_working(self, api_client):
        """Verify routes/customers.py APIRouter is correctly mounted"""
        response = api_client.get(f"{BASE_URL}/api/customers")
        assert response.status_code == 200
        print("PASS: routes/customers.py APIRouter is correctly mounted")
    
    def test_csat_router_working(self, api_client):
        """Verify routes/csat.py APIRouter is correctly mounted"""
        response = api_client.get(f"{BASE_URL}/api/csat/analytics")
        assert response.status_code == 200
        print("PASS: routes/csat.py APIRouter is correctly mounted")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
