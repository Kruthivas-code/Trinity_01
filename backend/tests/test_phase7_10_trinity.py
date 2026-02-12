"""
Phase 7-10 Trinity Testing:
- Phase 7: Leave Management (CRUD, conflict detection, calendar)
- Phase 8: Admin - Custom Fields, Routing Rules, SLA, Settings, Exports
- Phase 9: Search, Ticket Assignment, Notes, Star/Unstar
- Phase 10: Full Ticket Lifecycle, CSAT Survey, Export Verification

Bug fixes to verify:
- leaves.py: await leave_mgr.create_leave(leave_data)
- feature_requests.py: default status 'new' not 'proposed'
- FeatureRequestsPage.js: use fr.request_type || fr.category
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_COOKIE = "test_filter_session"
ADMIN_USER_ID = "b1bbdaf9-5ac0-47a9-ac7d-31b0b149010e"

# Existing data from previous tests
EXISTING_LEAVE_ID = "leave_816f972970d1"
EXISTING_CUSTOM_FIELD_ID = "field_8d4e058dd436"
EXISTING_FEATURE_REQUEST_ID = "fr_6660ff835e30"
EXISTING_CANNED_RESPONSE_ID = "cr_49e973059af9"
EXISTING_CUSTOMER_ID = "CUST-000001"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth cookie"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    session.cookies.set("session_token", SESSION_COOKIE)
    return session


class TestPhase7LeaveManagement:
    """Phase 7: Leave Management CRUD and conflict detection"""
    
    created_leave_id = None
    
    def test_list_leaves(self, api_client):
        """Test GET /api/leaves - List all leaves"""
        response = api_client.get(f"{BASE_URL}/api/leaves")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        # Response should be a list
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"Found {len(data)} leaves in system")
    
    def test_create_leave_bug_fix_verification(self, api_client):
        """Test POST /api/leaves - Bug fix: await leave_mgr.create_leave(leave_data)"""
        # Create leave for Feb 20-21
        leave_data = {
            "user_id": ADMIN_USER_ID,
            "start_date": "2026-02-20",
            "end_date": "2026-02-21",
            "leave_type": "vacation",
            "reason": "TEST_Phase7_Leave_Creation"
        }
        response = api_client.post(f"{BASE_URL}/api/leaves", json=leave_data)
        assert response.status_code == 200, f"Leave creation failed with {response.status_code}: {response.text}"
        
        data = response.json()
        assert "leave_id" in data, "Response should contain leave_id"
        TestPhase7LeaveManagement.created_leave_id = data.get("leave_id")
        print(f"Created leave: {TestPhase7LeaveManagement.created_leave_id}")
    
    def test_get_leave_by_id(self, api_client):
        """Test GET /api/leaves/{leave_id} - Retrieve specific leave"""
        leave_id = TestPhase7LeaveManagement.created_leave_id or EXISTING_LEAVE_ID
        response = api_client.get(f"{BASE_URL}/api/leaves/{leave_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("leave_id") == leave_id
    
    def test_update_leave(self, api_client):
        """Test PUT /api/leaves/{leave_id} - Update leave"""
        leave_id = TestPhase7LeaveManagement.created_leave_id
        if not leave_id:
            pytest.skip("No leave created in previous test")
        
        update_data = {"reason": "TEST_Phase7_Updated_Reason"}
        response = api_client.put(f"{BASE_URL}/api/leaves/{leave_id}", json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify update persisted
        get_response = api_client.get(f"{BASE_URL}/api/leaves/{leave_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert "Updated" in data.get("reason", ""), f"Update not persisted: {data}"
    
    def test_delete_leave(self, api_client):
        """Test DELETE /api/leaves/{leave_id} - Delete leave"""
        leave_id = TestPhase7LeaveManagement.created_leave_id
        if not leave_id:
            pytest.skip("No leave created in previous test")
        
        response = api_client.delete(f"{BASE_URL}/api/leaves/{leave_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify deletion
        get_response = api_client.get(f"{BASE_URL}/api/leaves/{leave_id}")
        assert get_response.status_code == 404, "Leave should be deleted"


class TestPhase8AdminCustomFields:
    """Phase 8: Admin - Custom Fields CRUD"""
    
    created_field_id = None
    
    def test_list_custom_fields(self, api_client):
        """Test GET /api/admin/custom-fields"""
        response = api_client.get(f"{BASE_URL}/api/admin/custom-fields")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} custom fields")
        # Verify existing field exists
        field_ids = [f.get("field_id") for f in data]
        if EXISTING_CUSTOM_FIELD_ID:
            assert EXISTING_CUSTOM_FIELD_ID in field_ids, f"Existing field {EXISTING_CUSTOM_FIELD_ID} not found"
    
    def test_create_custom_field(self, api_client):
        """Test POST /api/admin/custom-fields"""
        field_data = {
            "name": "TEST_Phase8_Field",
            "field_type": "text",
            "entity_type": "ticket",
            "required": False,
            "description": "Test field for Phase 8"
        }
        response = api_client.post(f"{BASE_URL}/api/admin/custom-fields", json=field_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "field_id" in data
        TestPhase8AdminCustomFields.created_field_id = data.get("field_id")
        print(f"Created custom field: {TestPhase8AdminCustomFields.created_field_id}")
    
    def test_delete_custom_field(self, api_client):
        """Test DELETE /api/admin/custom-fields/{field_id}"""
        field_id = TestPhase8AdminCustomFields.created_field_id
        if not field_id:
            pytest.skip("No field created")
        
        response = api_client.delete(f"{BASE_URL}/api/admin/custom-fields/{field_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"


class TestPhase8AdminRoutingRules:
    """Phase 8: Admin - Routing Rules CRUD"""
    
    created_rule_id = None
    
    def test_list_routing_rules(self, api_client):
        """Test GET /api/admin/routing-rules"""
        response = api_client.get(f"{BASE_URL}/api/admin/routing-rules")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} routing rules")
    
    def test_create_routing_rule(self, api_client):
        """Test POST /api/admin/routing-rules"""
        rule_data = {
            "name": "TEST_Phase8_Routing_Rule",
            "description": "Test routing rule",
            "conditions": [{"field": "priority", "operator": "equals", "value": "urgent"}],
            "actions": [{"type": "set_priority", "value": "high"}],
            "priority": 10,
            "is_active": True
        }
        response = api_client.post(f"{BASE_URL}/api/admin/routing-rules", json=rule_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "rule_id" in data
        TestPhase8AdminRoutingRules.created_rule_id = data.get("rule_id")
        print(f"Created routing rule: {TestPhase8AdminRoutingRules.created_rule_id}")
    
    def test_delete_routing_rule(self, api_client):
        """Test DELETE /api/admin/routing-rules/{rule_id}"""
        rule_id = TestPhase8AdminRoutingRules.created_rule_id
        if not rule_id:
            pytest.skip("No rule created")
        
        response = api_client.delete(f"{BASE_URL}/api/admin/routing-rules/{rule_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"


class TestPhase8AdminSLA:
    """Phase 8: Admin - SLA Policies (4 should exist)"""
    
    def test_get_sla_policies(self, api_client):
        """Test GET /api/admin/sla-policies - Should have 4 priority SLAs"""
        response = api_client.get(f"{BASE_URL}/api/admin/sla-policies")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check priority_slas structure
        priority_slas = data.get("priority_slas", {})
        assert len(priority_slas) == 4, f"Expected 4 SLA policies, got {len(priority_slas)}: {list(priority_slas.keys())}"
        
        # Verify all priorities exist
        expected_priorities = ["low", "medium", "high", "urgent"]
        for priority in expected_priorities:
            assert priority in priority_slas, f"Missing SLA for {priority}"
        print(f"SLA Policies: {list(priority_slas.keys())}")
    
    def test_update_sla_policies(self, api_client):
        """Test PUT /api/admin/sla-policies"""
        update_data = {
            "default_first_response_hours": 4,
            "default_resolution_hours": 24
        }
        response = api_client.put(f"{BASE_URL}/api/admin/sla-policies", json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


class TestPhase8AdminSettings:
    """Phase 8: Admin - General Settings"""
    
    def test_get_settings(self, api_client):
        """Test GET /api/admin/settings"""
        response = api_client.get(f"{BASE_URL}/api/admin/settings")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Check required fields exist
        expected_fields = ["company_name", "default_priority", "auto_assignment"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        print(f"Settings: company={data.get('company_name')}, auto_assignment={data.get('auto_assignment')}")
    
    def test_update_settings(self, api_client):
        """Test PUT /api/admin/settings"""
        update_data = {"company_name": "Trinity Test Company"}
        response = api_client.put(f"{BASE_URL}/api/admin/settings", json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


class TestPhase8DataExport:
    """Phase 8: Settings - Data Export"""
    
    def test_get_tickets_for_export(self, api_client):
        """Test GET /api/tickets - Returns tickets for export"""
        response = api_client.get(f"{BASE_URL}/api/tickets?limit=5")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Handle both {tickets: []} and [] formats
        tickets = data.get("tickets", data) if isinstance(data, dict) else data
        print(f"Got {len(tickets)} tickets for export")
    
    def test_get_users_for_export(self, api_client):
        """Test GET /api/users - Returns users for export"""
        response = api_client.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Handle {items: []} format
        users = data.get("items", data) if isinstance(data, dict) else data
        print(f"Got {len(users)} users for export")
    
    def test_get_teams_for_export(self, api_client):
        """Test GET /api/teams - Returns teams for export"""
        response = api_client.get(f"{BASE_URL}/api/teams")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        # Handle both list and dict formats
        teams = data if isinstance(data, list) else data.get("items", [])
        print(f"Got {len(teams)} teams for export")
    
    def test_admin_export_tickets(self, api_client):
        """Test POST /api/admin/export/tickets"""
        export_request = {
            "format": "json",
            "include_notes": True,
            "include_changelog": False,
            "include_csat": False
        }
        response = api_client.post(f"{BASE_URL}/api/admin/export/tickets", json=export_request)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("Ticket export endpoint working")


class TestPhase8Shifts:
    """Phase 8: Admin - Shifts & Schedules"""
    
    def test_get_shifts(self, api_client):
        """Test GET /api/shifts"""
        response = api_client.get(f"{BASE_URL}/api/shifts")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list)
        print(f"Found {len(data)} shifts")


class TestPhase9Search:
    """Phase 9: Search functionality"""
    
    def test_search_tickets(self, api_client):
        """Test POST /api/search - Search for billing tickets"""
        search_data = {"query": "billing", "limit": 10}
        response = api_client.post(f"{BASE_URL}/api/search", json=search_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        print(f"Search returned: {data}")
    
    def test_search_suggestions(self, api_client):
        """Test GET /api/search/suggestions"""
        response = api_client.get(f"{BASE_URL}/api/search/suggestions?q=test")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "suggestions" in data


class TestPhase9TicketOperations:
    """Phase 9: Ticket assignment, status change, notes, star/unstar"""
    
    test_ticket_id = None
    
    def test_get_tickets_list(self, api_client):
        """Get ticket list to find a ticket for testing"""
        response = api_client.get(f"{BASE_URL}/api/tickets?limit=5")
        assert response.status_code == 200
        data = response.json()
        tickets = data.get("tickets", [])
        if tickets:
            TestPhase9TicketOperations.test_ticket_id = tickets[0].get("ticket_id")
            print(f"Using ticket {TestPhase9TicketOperations.test_ticket_id} for testing")
    
    def test_update_ticket_status(self, api_client):
        """Test PUT /api/tickets/{id} - Update status"""
        ticket_id = TestPhase9TicketOperations.test_ticket_id
        if not ticket_id:
            pytest.skip("No ticket available")
        
        update_data = {"status": "in_progress"}
        response = api_client.put(f"{BASE_URL}/api/tickets/{ticket_id}", json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_assign_ticket(self, api_client):
        """Test PUT /api/tickets/{id} - Assign ticket"""
        ticket_id = TestPhase9TicketOperations.test_ticket_id
        if not ticket_id:
            pytest.skip("No ticket available")
        
        update_data = {"assignee_id": ADMIN_USER_ID}
        response = api_client.put(f"{BASE_URL}/api/tickets/{ticket_id}", json=update_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_add_internal_note(self, api_client):
        """Test POST /api/tickets/{id}/notes - Add internal note"""
        ticket_id = TestPhase9TicketOperations.test_ticket_id
        if not ticket_id:
            pytest.skip("No ticket available")
        
        note_data = {
            "content": "TEST_Phase9_Internal_Note",
            "type": "internal"
        }
        response = api_client.post(f"{BASE_URL}/api/tickets/{ticket_id}/notes", json=note_data)
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
        print("Internal note added successfully")
    
    def test_star_ticket(self, api_client):
        """Test POST /api/tickets/{id}/star - Star ticket"""
        ticket_id = TestPhase9TicketOperations.test_ticket_id
        if not ticket_id:
            pytest.skip("No ticket available")
        
        response = api_client.post(f"{BASE_URL}/api/tickets/{ticket_id}/star")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_get_starred_tickets(self, api_client):
        """Test GET /api/tickets/starred - List starred tickets"""
        response = api_client.get(f"{BASE_URL}/api/tickets/starred")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_unstar_ticket(self, api_client):
        """Test DELETE /api/tickets/{id}/star - Unstar ticket"""
        ticket_id = TestPhase9TicketOperations.test_ticket_id
        if not ticket_id:
            pytest.skip("No ticket available")
        
        response = api_client.delete(f"{BASE_URL}/api/tickets/{ticket_id}/star")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"


class TestPhase10TicketLifecycle:
    """Phase 10: Full ticket lifecycle E2E"""
    
    lifecycle_ticket_id = None
    
    def test_create_ticket(self, api_client):
        """Create a new ticket"""
        ticket_data = {
            "title": "TEST_Phase10_Lifecycle_Ticket",
            "description": "Testing full ticket lifecycle",
            "customer_name": "Test Customer",
            "customer_email": "test.lifecycle@example.com",
            "priority": "medium",
            "queue_id": "L1-Basic"
        }
        response = api_client.post(f"{BASE_URL}/api/tickets", json=ticket_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "ticket_id" in data
        TestPhase10TicketLifecycle.lifecycle_ticket_id = data.get("ticket_id")
        print(f"Created lifecycle ticket: {TestPhase10TicketLifecycle.lifecycle_ticket_id}")
    
    def test_assign_ticket(self, api_client):
        """Assign the ticket"""
        ticket_id = TestPhase10TicketLifecycle.lifecycle_ticket_id
        if not ticket_id:
            pytest.skip("No ticket created")
        
        response = api_client.put(f"{BASE_URL}/api/tickets/{ticket_id}", json={"assignee_id": ADMIN_USER_ID})
        assert response.status_code == 200
    
    def test_update_status_in_progress(self, api_client):
        """Move ticket to in_progress"""
        ticket_id = TestPhase10TicketLifecycle.lifecycle_ticket_id
        if not ticket_id:
            pytest.skip("No ticket created")
        
        response = api_client.put(f"{BASE_URL}/api/tickets/{ticket_id}", json={"status": "in_progress"})
        assert response.status_code == 200
    
    def test_resolve_ticket(self, api_client):
        """Resolve the ticket"""
        ticket_id = TestPhase10TicketLifecycle.lifecycle_ticket_id
        if not ticket_id:
            pytest.skip("No ticket created")
        
        response = api_client.put(f"{BASE_URL}/api/tickets/{ticket_id}", json={"status": "resolved"})
        assert response.status_code == 200
        
        # Verify status changed
        get_response = api_client.get(f"{BASE_URL}/api/tickets/{ticket_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data.get("status") == "resolved"
        print(f"Ticket {ticket_id} resolved successfully")


class TestPhase10CSATSurvey:
    """Phase 10: CSAT Survey functionality"""
    
    def test_send_csat_survey(self, api_client):
        """Test POST /api/csat/send - Send CSAT survey for resolved ticket"""
        # Use the resolved ticket from lifecycle test or any resolved ticket
        ticket_id = TestPhase10TicketLifecycle.lifecycle_ticket_id
        if not ticket_id:
            # Get any resolved ticket
            response = api_client.get(f"{BASE_URL}/api/tickets?status=resolved&limit=1")
            if response.status_code == 200:
                data = response.json()
                tickets = data.get("tickets", [])
                if tickets:
                    ticket_id = tickets[0].get("ticket_id")
        
        if not ticket_id:
            pytest.skip("No resolved ticket available")
        
        response = api_client.post(f"{BASE_URL}/api/csat/send/{ticket_id}")
        # Accept 200 (success) or 400 (already sent)
        assert response.status_code in [200, 400], f"Expected 200/400, got {response.status_code}: {response.text}"
        print(f"CSAT survey API response: {response.status_code}")


class TestBugFixVerification:
    """Verify all bug fixes from the main agent"""
    
    def test_feature_request_default_status_new(self, api_client):
        """Bug fix: feature_requests.py line 35 - default status 'new' not 'proposed'"""
        fr_data = {
            "title": "TEST_BugFix_FeatureRequest_Status",
            "description": "Testing default status is 'new'",
            "request_type": "feature",
            "priority": "medium"
        }
        response = api_client.post(f"{BASE_URL}/api/feature-requests", json=fr_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "new", f"Expected status 'new', got '{data.get('status')}'"
        
        # Cleanup
        fr_id = data.get("feature_request_id")
        if fr_id:
            api_client.delete(f"{BASE_URL}/api/feature-requests/{fr_id}")
        print("Bug fix verified: feature request default status is 'new'")
    
    def test_feature_request_category_field(self, api_client):
        """Verify feature request uses 'category' field (from request_type)"""
        response = api_client.get(f"{BASE_URL}/api/feature-requests")
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", [])
        
        # If we have feature requests, verify they have category field
        if items:
            fr = items[0]
            # Should have either request_type or category
            has_type = "request_type" in fr or "category" in fr
            assert has_type, f"Feature request missing type field: {fr.keys()}"
            print(f"Feature request type field: category={fr.get('category')}, request_type={fr.get('request_type')}")


class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_lifecycle_ticket(self, api_client):
        """Remove test ticket"""
        ticket_id = TestPhase10TicketLifecycle.lifecycle_ticket_id
        if ticket_id:
            # Just update status, don't delete to keep audit trail
            response = api_client.put(f"{BASE_URL}/api/tickets/{ticket_id}", json={"status": "resolved"})
            print(f"Cleaned up ticket {ticket_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
