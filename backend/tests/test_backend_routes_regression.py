"""
Comprehensive Backend Routes Regression Test Suite
===================================================
Tests all 19 route modules after major backend refactoring:

Route Modules:
1. routes/auth.py - Auth endpoints
2. routes/users.py - User endpoints
3. routes/teams.py - Team endpoints
4. routes/shifts.py - Shift endpoints
5. routes/tickets.py - Core ticket CRUD
6. routes/ticket_ops.py - Bulk/merge/link/split
7. routes/email.py - IMAP + Gmail
8. routes/admin.py - Admin endpoints
9. routes/sla.py - SLA endpoints
10. routes/analytics.py - Analytics endpoints
11. routes/search_presence.py - Search + presence
12. routes/leaves.py - Leave management
13. routes/feature_requests.py - Feature requests
14. routes/exports.py - Data exports
15. routes/filters.py - Filter/inbox routes
16. routes/webhooks.py - Webhook routes
17. routes/customers.py - Customer routes
18. routes/canned_responses.py - Canned response routes
19. routes/csat.py - CSAT routes

Supporting Modules:
- database.py - DB connection + collections
- dependencies.py - Auth dependencies
- utils.py - Shared utilities
- ticket_helpers.py - Ticket routing/assignment helpers
- rate_limiter.py - Shared rate limiter
- models/schemas.py - Pydantic models
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

# Use the public URL from frontend/.env for testing
BASE_URL = "https://data-integrity-fix-37.preview.emergentagent.com"

# Test credentials - create new session for each test run
SESSION_TOKEN = "test_session_regression_1770873791877"
USER_ID = "test-user-regression-1770873791877"


@pytest.fixture
def api_client():
    """Shared requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Cookie": f"session_token={SESSION_TOKEN}"
    })
    return session


# ==================== 1. Health Check (server.py) ====================
class TestHealthCheck:
    """Health endpoint - no auth required"""
    
    def test_health_endpoint_returns_healthy(self):
        """GET /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"
        assert data["checks"]["database"]["status"] == "healthy"
        print("PASS: Health endpoint returns healthy with version 2.0.0")


# ==================== 2. Auth Routes (routes/auth.py) ====================
class TestAuthRoutes:
    """Authentication endpoint tests"""
    
    def test_auth_me_with_session(self, api_client):
        """GET /api/auth/me returns user data"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        print(f"PASS: Auth/me returns user {data['user_id']}")
    
    def test_auth_me_without_session_returns_401(self):
        """GET /api/auth/me without session returns 401"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401
        print("PASS: Auth/me returns 401 without session")
    
    def test_auth_logout(self, api_client):
        """POST /api/auth/logout clears session"""
        # Use a new session to avoid affecting main test session
        temp_session = requests.Session()
        temp_session.headers.update({
            "Content-Type": "application/json",
            "Cookie": f"session_token=temp_test_{uuid.uuid4().hex}"
        })
        response = temp_session.post(f"{BASE_URL}/api/auth/logout")
        assert response.status_code == 200
        print("PASS: Auth/logout endpoint works")
    
    def test_get_api_keys(self, api_client):
        """GET /api/auth/api-keys returns list"""
        response = api_client.get(f"{BASE_URL}/api/auth/api-keys")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Auth/api-keys returns {len(data)} keys")


# ==================== 3. User Routes (routes/users.py) ====================
class TestUserRoutes:
    """User endpoint tests"""
    
    def test_get_users_me(self, api_client):
        """GET /api/users/me returns current user"""
        response = api_client.get(f"{BASE_URL}/api/users/me")
        assert response.status_code == 200
        
        data = response.json()
        assert "user_id" in data
        print("PASS: Users/me returns user data")
    
    def test_get_users_paginated(self, api_client):
        """GET /api/users returns paginated users"""
        response = api_client.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "has_more" in data
        print(f"PASS: Users returns {len(data['items'])} users (total: {data['total']})")


# ==================== 4. Team Routes (routes/teams.py) ====================
class TestTeamRoutes:
    """Team endpoint tests"""
    
    def test_get_teams(self, api_client):
        """GET /api/teams returns teams list"""
        response = api_client.get(f"{BASE_URL}/api/teams")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Teams endpoint returns {len(data)} teams")
    
    def test_create_and_delete_team(self, api_client):
        """POST /api/teams creates team, DELETE removes it"""
        team_data = {
            "name": f"TEST_Team_{uuid.uuid4().hex[:8]}",
            "escalation_level": "L1",
            "description": "Test team for regression"
        }
        
        response = api_client.post(f"{BASE_URL}/api/teams", json=team_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "team_id" in data
        team_id = data["team_id"]
        print(f"PASS: Created team {team_id}")
        
        # Cleanup
        del_response = api_client.delete(f"{BASE_URL}/api/teams/{team_id}")
        assert del_response.status_code == 200
        print(f"PASS: Deleted team {team_id}")


# ==================== 5. Shift Routes (routes/shifts.py) ====================
class TestShiftRoutes:
    """Shift endpoint tests"""
    
    def test_get_all_shifts(self, api_client):
        """GET /api/shifts returns shifts list"""
        response = api_client.get(f"{BASE_URL}/api/shifts")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Shifts endpoint returns {len(data)} shifts")


# ==================== 6. Ticket Routes (routes/tickets.py) ====================
class TestTicketRoutes:
    """Core ticket CRUD tests"""
    
    def test_get_tickets_paginated(self, api_client):
        """GET /api/tickets returns paginated tickets"""
        response = api_client.get(f"{BASE_URL}/api/tickets?page=1&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
        assert "total" in data
        assert "has_more" in data
        print(f"PASS: Tickets returns {len(data['tickets'])} tickets (total: {data['total']})")
    
    def test_get_tickets_with_status_filter(self, api_client):
        """GET /api/tickets with status filter"""
        response = api_client.get(f"{BASE_URL}/api/tickets?status=todo&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        for ticket in data.get("tickets", []):
            assert ticket.get("status") == "todo"
        print(f"PASS: Tickets filtered by status=todo")
    
    def test_get_starred_tickets(self, api_client):
        """GET /api/tickets/starred returns starred tickets"""
        response = api_client.get(f"{BASE_URL}/api/tickets/starred")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Starred tickets returns {len(data)} tickets")
    
    def test_get_escalation_counts(self, api_client):
        """GET /api/tickets/escalation-counts returns counts"""
        response = api_client.get(f"{BASE_URL}/api/tickets/escalation-counts")
        assert response.status_code == 200
        
        data = response.json()
        assert "L1" in data
        print(f"PASS: Escalation counts returns L1: {data.get('L1', {}).get('total', 0)}")
    
    def test_ticket_crud(self, api_client):
        """Create, get, update, delete ticket"""
        # Create
        ticket_data = {
            "title": f"TEST_Ticket_{uuid.uuid4().hex[:8]}",
            "description": "Regression test ticket",
            "status": "todo",
            "priority": "medium"
        }
        
        response = api_client.post(f"{BASE_URL}/api/tickets", json=ticket_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "ticket_id" in data
        ticket_id = data["ticket_id"]
        print(f"PASS: Created ticket {ticket_id}")
        
        # Get
        response = api_client.get(f"{BASE_URL}/api/tickets/{ticket_id}")
        assert response.status_code == 200
        print(f"PASS: Got ticket {ticket_id}")
        
        # Update
        response = api_client.put(f"{BASE_URL}/api/tickets/{ticket_id}", json={"priority": "high"})
        assert response.status_code == 200
        print(f"PASS: Updated ticket {ticket_id}")
        
        # Delete
        response = api_client.delete(f"{BASE_URL}/api/tickets/{ticket_id}")
        assert response.status_code == 200
        print(f"PASS: Deleted ticket {ticket_id}")


# ==================== 7. Ticket Operations (routes/ticket_ops.py) ====================
class TestTicketOpsRoutes:
    """Bulk operations tests"""
    
    def test_bulk_update_endpoint_exists(self, api_client):
        """POST /api/tickets/bulk-update endpoint exists"""
        response = api_client.post(
            f"{BASE_URL}/api/tickets/bulk-update",
            json={"ticket_ids": [], "updates": {"status": "todo"}}
        )
        assert response.status_code == 400  # Expected: no ticket IDs provided
        print("PASS: Bulk update endpoint accessible")
    
    def test_bulk_tag_endpoint_exists(self, api_client):
        """POST /api/tickets/bulk-tag endpoint exists"""
        response = api_client.post(
            f"{BASE_URL}/api/tickets/bulk-tag",
            json={"ticket_ids": [], "tags_to_add": ["test"]}
        )
        assert response.status_code == 400  # Expected: no ticket IDs provided
        print("PASS: Bulk tag endpoint accessible")


# ==================== 8. Email Routes (routes/email.py) ====================
class TestEmailRoutes:
    """Email integration tests"""
    
    def test_email_status(self, api_client):
        """GET /api/email/status returns IMAP status"""
        response = api_client.get(f"{BASE_URL}/api/email/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "connected" in data
        print(f"PASS: Email status: connected={data['connected']}")
    
    def test_gmail_status(self, api_client):
        """GET /api/gmail/status returns Gmail status"""
        response = api_client.get(f"{BASE_URL}/api/gmail/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "connected" in data
        assert "configured" in data
        print(f"PASS: Gmail status: connected={data['connected']}, configured={data['configured']}")


# ==================== 9. Admin Routes (routes/admin.py) ====================
class TestAdminRoutes:
    """Admin endpoint tests"""
    
    def test_get_admin_settings(self, api_client):
        """GET /api/admin/settings returns settings"""
        response = api_client.get(f"{BASE_URL}/api/admin/settings")
        assert response.status_code == 200
        
        data = response.json()
        assert "company_name" in data or "auto_assignment" in data
        print("PASS: Admin settings accessible")
    
    def test_get_custom_fields(self, api_client):
        """GET /api/admin/custom-fields returns fields"""
        response = api_client.get(f"{BASE_URL}/api/admin/custom-fields")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Custom fields returns {len(data)} fields")
    
    def test_get_routing_rules(self, api_client):
        """GET /api/admin/routing-rules returns rules"""
        response = api_client.get(f"{BASE_URL}/api/admin/routing-rules")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Routing rules returns {len(data)} rules")
    
    def test_get_sla_policies_admin(self, api_client):
        """GET /api/admin/sla-policies returns policies"""
        response = api_client.get(f"{BASE_URL}/api/admin/sla-policies")
        assert response.status_code == 200
        
        data = response.json()
        assert "default_first_response_hours" in data or "priority_slas" in data
        print("PASS: Admin SLA policies accessible")
    
    def test_get_sla_escalation_rules(self, api_client):
        """GET /api/admin/sla-escalation-rules returns rules"""
        response = api_client.get(f"{BASE_URL}/api/admin/sla-escalation-rules")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: SLA escalation rules returns {len(data)} rules")
    
    def test_auto_close_status(self, api_client):
        """GET /api/admin/auto-close-status returns status"""
        response = api_client.get(f"{BASE_URL}/api/admin/auto-close-status")
        assert response.status_code == 200
        
        data = response.json()
        assert "enabled" in data
        assert "auto_close_hours" in data
        print(f"PASS: Auto-close status: {data['auto_close_hours']} hours")


# ==================== 10. SLA Routes (routes/sla.py) ====================
class TestSLARoutes:
    """SLA endpoint tests"""
    
    def test_list_sla_policies(self, api_client):
        """GET /api/sla-policies returns policies"""
        response = api_client.get(f"{BASE_URL}/api/sla-policies")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: SLA policies returns {len(data)} policies")


# ==================== 11. Analytics Routes (routes/analytics.py) ====================
class TestAnalyticsRoutes:
    """Analytics endpoint tests"""
    
    def test_analytics_summary(self, api_client):
        """GET /api/analytics/summary returns summary"""
        response = api_client.get(f"{BASE_URL}/api/analytics/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "by_status" in data
        assert "total" in data
        print(f"PASS: Analytics summary: total={data['total']}")
    
    def test_analytics_overview(self, api_client):
        """GET /api/analytics/overview returns overview"""
        response = api_client.get(f"{BASE_URL}/api/analytics/overview?period=7d")
        assert response.status_code == 200
        
        data = response.json()
        assert "period" in data
        assert "total_tickets" in data
        print(f"PASS: Analytics overview: {data['total_tickets']} total tickets")
    
    def test_analytics_agents(self, api_client):
        """GET /api/analytics/agents returns agent metrics"""
        response = api_client.get(f"{BASE_URL}/api/analytics/agents?period=7d")
        assert response.status_code == 200
        
        data = response.json()
        assert "period" in data
        assert "agents" in data
        print(f"PASS: Analytics agents: {len(data['agents'])} agents")


# ==================== 12. Search & Presence (routes/search_presence.py) ====================
class TestSearchPresenceRoutes:
    """Search and presence tests"""
    
    def test_search_suggestions(self, api_client):
        """GET /api/search/suggestions returns suggestions"""
        response = api_client.get(f"{BASE_URL}/api/search/suggestions?q=test")
        assert response.status_code == 200
        
        data = response.json()
        assert "suggestions" in data
        print("PASS: Search suggestions accessible")
    
    def test_presence_stats(self, api_client):
        """GET /api/presence/stats returns stats"""
        response = api_client.get(f"{BASE_URL}/api/presence/stats")
        assert response.status_code == 200
        print("PASS: Presence stats accessible")
    
    def test_notifications(self, api_client):
        """GET /api/notifications returns notifications"""
        response = api_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Notifications returns {len(data)} items")


# ==================== 13. Leave Routes (routes/leaves.py) ====================
class TestLeaveRoutes:
    """Leave management tests"""
    
    def test_get_leaves(self, api_client):
        """GET /api/leaves returns leaves"""
        response = api_client.get(f"{BASE_URL}/api/leaves")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"PASS: Leaves returns {len(data)} leaves")


# ==================== 14. Feature Requests (routes/feature_requests.py) ====================
class TestFeatureRequestRoutes:
    """Feature requests tests"""
    
    def test_list_feature_requests(self, api_client):
        """GET /api/feature-requests returns list"""
        response = api_client.get(f"{BASE_URL}/api/feature-requests")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        print(f"PASS: Feature requests returns {len(data['items'])} items")
    
    def test_create_and_delete_feature_request(self, api_client):
        """Create and delete feature request"""
        fr_data = {
            "title": f"TEST_FR_{uuid.uuid4().hex[:8]}",
            "description": "Test feature request",
            "request_type": "feature"
        }
        
        response = api_client.post(f"{BASE_URL}/api/feature-requests", json=fr_data)
        assert response.status_code == 200
        
        data = response.json()
        fr_id = data["feature_request_id"]
        print(f"PASS: Created feature request {fr_id}")
        
        # Delete
        response = api_client.delete(f"{BASE_URL}/api/feature-requests/{fr_id}")
        assert response.status_code == 200
        print(f"PASS: Deleted feature request {fr_id}")


# ==================== 15. Export Routes (routes/exports.py) ====================
class TestExportRoutes:
    """Export endpoint tests"""
    
    def test_export_tickets(self, api_client):
        """POST /api/admin/export/tickets returns export"""
        export_request = {
            "format": "json",
            "include_notes": False,
            "include_changelog": False
        }
        
        response = api_client.post(f"{BASE_URL}/api/admin/export/tickets", json=export_request)
        assert response.status_code == 200
        print("PASS: Export tickets accessible")
    
    def test_export_customers(self, api_client):
        """GET /api/admin/export/customers returns export"""
        response = api_client.get(f"{BASE_URL}/api/admin/export/customers?format=json")
        assert response.status_code == 200
        print("PASS: Export customers accessible")


# ==================== 16. Filter Routes (routes/filters.py) ====================
class TestFilterRoutes:
    """Filter and inbox tests"""
    
    def test_filter_tickets(self, api_client):
        """POST /api/filter/tickets filters tickets"""
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
        
        data = response.json()
        assert "tickets" in data
        assert "total" in data
        print(f"PASS: Filter tickets returns {len(data['tickets'])} tickets")
    
    def test_filter_fields(self, api_client):
        """GET /api/filter/fields returns fields"""
        response = api_client.get(f"{BASE_URL}/api/filter/fields")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 13
        print(f"PASS: Filter fields returns {len(data)} fields")
    
    def test_inbox_crud(self, api_client):
        """Create, get, delete inbox"""
        inbox_data = {
            "name": f"TEST_Inbox_{uuid.uuid4().hex[:8]}",
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "status", "op": "is", "value": "todo"}],
                "groups": []
            },
            "color": "#3b82f6"
        }
        
        response = api_client.post(f"{BASE_URL}/api/inboxes", json=inbox_data)
        assert response.status_code == 200
        
        data = response.json()
        inbox_id = data["inbox_id"]
        print(f"PASS: Created inbox {inbox_id}")
        
        # Delete
        response = api_client.delete(f"{BASE_URL}/api/inboxes/{inbox_id}")
        assert response.status_code == 200
        print(f"PASS: Deleted inbox {inbox_id}")


# ==================== 17. Webhook Routes (routes/webhooks.py) ====================
class TestWebhookRoutes:
    """Webhook endpoint tests"""
    
    def test_webhook_events(self, api_client):
        """GET /api/webhooks/events returns events"""
        response = api_client.get(f"{BASE_URL}/api/webhooks/events")
        assert response.status_code == 200
        
        data = response.json()
        assert "events" in data
        assert len(data["events"]) >= 10
        print(f"PASS: Webhook events returns {len(data['events'])} events")


# ==================== 18. Customer Routes (routes/customers.py) ====================
class TestCustomerRoutes:
    """Customer endpoint tests"""
    
    def test_list_customers(self, api_client):
        """GET /api/customers returns customers"""
        response = api_client.get(f"{BASE_URL}/api/customers")
        assert response.status_code == 200
        
        data = response.json()
        assert "customers" in data
        assert "total" in data
        print(f"PASS: Customers returns {len(data['customers'])} customers")
    
    def test_search_customers(self, api_client):
        """GET /api/customers?search=test searches customers"""
        response = api_client.get(f"{BASE_URL}/api/customers?search=test")
        assert response.status_code == 200
        
        data = response.json()
        assert "customers" in data
        print(f"PASS: Customer search returns {len(data['customers'])} results")


# ==================== 19. Canned Responses (routes/canned_responses.py) ====================
class TestCannedResponseRoutes:
    """Canned response tests"""
    
    def test_get_canned_responses(self, api_client):
        """GET /api/canned-responses returns responses"""
        response = api_client.get(f"{BASE_URL}/api/canned-responses")
        assert response.status_code == 200
        
        data = response.json()
        assert "global" in data
        assert "personal" in data
        assert "all" in data
        print(f"PASS: Canned responses returns {len(data['all'])} items")
    
    def test_canned_response_crud(self, api_client):
        """Create and delete canned response"""
        cr_data = {
            "title": f"TEST_Response_{uuid.uuid4().hex[:8]}",
            "shortcode": f"test{uuid.uuid4().hex[:4]}",
            "content": "This is a test response",
            "scope": "personal"
        }
        
        response = api_client.post(f"{BASE_URL}/api/canned-responses", json=cr_data)
        assert response.status_code == 200
        
        data = response.json()
        cr_id = data["response_id"]
        print(f"PASS: Created canned response {cr_id}")
        
        # Delete
        response = api_client.delete(f"{BASE_URL}/api/canned-responses/{cr_id}")
        assert response.status_code == 200
        print(f"PASS: Deleted canned response {cr_id}")


# ==================== 20. CSAT Routes (routes/csat.py) ====================
class TestCSATRoutes:
    """CSAT endpoint tests"""
    
    def test_csat_analytics(self, api_client):
        """GET /api/csat/analytics returns analytics"""
        response = api_client.get(f"{BASE_URL}/api/csat/analytics?days=30")
        assert response.status_code == 200
        
        data = response.json()
        assert "period_days" in data
        assert "total_responses" in data
        print(f"PASS: CSAT analytics: {data['total_responses']} responses")


# ==================== Module Import Verification ====================
class TestModuleImports:
    """Verify all module imports work correctly"""
    
    def test_database_module(self):
        """database.py is working"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        assert response.json()["checks"]["database"]["status"] == "healthy"
        print("PASS: database.py module working")
    
    def test_dependencies_module(self, api_client):
        """dependencies.py auth functions work"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200
        print("PASS: dependencies.py module working")
    
    def test_utils_module(self, api_client):
        """utils.py serialize_doc works (no _id in responses)"""
        response = api_client.get(f"{BASE_URL}/api/tickets?limit=1")
        assert response.status_code == 200
        for ticket in response.json().get("tickets", []):
            assert "_id" not in ticket
        print("PASS: utils.py module working")
    
    def test_schemas_module(self, api_client):
        """models/schemas.py Pydantic models work"""
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
        print("PASS: models/schemas.py module working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
