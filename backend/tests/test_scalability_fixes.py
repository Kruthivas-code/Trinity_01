"""
Test suite for Trinity scalability/production-readiness fixes:
1. GET /api/tickets - pagination format {tickets, total, page, limit, has_more}
2. GET /api/tickets - multiple status params support
3. GET /api/analytics/summary - single aggregation response
4. GET /api/analytics/overview - full analytics structure
5. GET /api/tickets/{id}/notes - paginated {messages, total, page, has_more}
6. GET /api/export?format=json - streaming JSON array
7. GET /api/export?format=csv - streaming CSV
8. GET /api/email/status - IMAP connection status
9. GET /api/health - health check
"""

import pytest
import requests
import os
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = os.environ.get('TEST_SESSION_TOKEN', 'test_session_1770831806742')


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session with auth header"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SESSION_TOKEN}"
    })
    return session


class TestHealthEndpoint:
    """Health check endpoint tests"""
    
    def test_health_returns_healthy(self, api_client):
        """GET /api/health returns healthy status"""
        response = api_client.get(f"{BASE_URL}/api/health")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Response should have 'status' field"
        assert data["status"] == "healthy", f"Expected 'healthy', got {data['status']}"
        assert "timestamp" in data, "Response should have 'timestamp' field"


class TestTicketsPagination:
    """Tests for GET /api/tickets endpoint with new pagination format"""
    
    def test_tickets_returns_paginated_format(self, api_client):
        """GET /api/tickets returns {tickets, total, page, limit, has_more}"""
        response = api_client.get(f"{BASE_URL}/api/tickets?page=1&limit=3")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify required fields exist
        assert "tickets" in data, "Response should have 'tickets' array"
        assert "total" in data, "Response should have 'total' count"
        assert "page" in data, "Response should have 'page' number"
        assert "limit" in data, "Response should have 'limit' value"
        assert "has_more" in data, "Response should have 'has_more' boolean"
        
        # Verify types
        assert isinstance(data["tickets"], list), "'tickets' should be a list"
        assert isinstance(data["total"], int), "'total' should be an integer"
        assert isinstance(data["page"], int), "'page' should be an integer"
        assert isinstance(data["limit"], int), "'limit' should be an integer"
        assert isinstance(data["has_more"], bool), "'has_more' should be a boolean"
        
        # Verify values
        assert data["page"] == 1, f"Expected page=1, got {data['page']}"
        assert data["limit"] == 3, f"Expected limit=3, got {data['limit']}"
        assert len(data["tickets"]) <= 3, "Should return at most 'limit' tickets"
        
        print(f"✅ Tickets pagination: total={data['total']}, page={data['page']}, limit={data['limit']}, has_more={data['has_more']}")

    def test_tickets_has_more_flag(self, api_client):
        """Verify has_more flag is correct when more tickets exist"""
        response = api_client.get(f"{BASE_URL}/api/tickets?page=1&limit=3")
        
        assert response.status_code == 200
        data = response.json()
        
        # If total > limit, has_more should be True
        if data["total"] > data["limit"]:
            assert data["has_more"] is True, "has_more should be True when total > limit"
            print(f"✅ has_more=True correctly (total={data['total']} > limit={data['limit']})")
        else:
            assert data["has_more"] is False, "has_more should be False when total <= limit"
            print(f"✅ has_more=False correctly (total={data['total']} <= limit={data['limit']})")

    def test_tickets_multiple_status_params(self, api_client):
        """GET /api/tickets?status=todo&status=in_progress supports multiple status values"""
        response = api_client.get(f"{BASE_URL}/api/tickets?status=todo&status=in_progress&limit=10")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "tickets" in data, "Response should have 'tickets' array"
        
        # Verify all returned tickets have one of the requested statuses
        for ticket in data["tickets"]:
            assert ticket.get("status") in ["todo", "in_progress"], \
                f"Ticket status '{ticket.get('status')}' not in ['todo', 'in_progress']"
        
        print(f"✅ Multiple status filter: returned {len(data['tickets'])} tickets with todo/in_progress status")

    def test_tickets_single_status_param(self, api_client):
        """GET /api/tickets?status=todo works with single status value"""
        response = api_client.get(f"{BASE_URL}/api/tickets?status=todo&limit=10")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "tickets" in data, "Response should have 'tickets' array"
        
        # Verify all returned tickets have the requested status
        for ticket in data["tickets"]:
            assert ticket.get("status") == "todo", \
                f"Ticket status '{ticket.get('status')}' should be 'todo'"
        
        print(f"✅ Single status filter: returned {len(data['tickets'])} 'todo' tickets")


class TestAnalyticsSummary:
    """Tests for GET /api/analytics/summary endpoint"""
    
    def test_analytics_summary_structure(self, api_client):
        """GET /api/analytics/summary returns {by_status, by_assignee, my_tickets, total}"""
        response = api_client.get(f"{BASE_URL}/api/analytics/summary")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify required fields exist
        assert "by_status" in data, "Response should have 'by_status'"
        assert "by_assignee" in data, "Response should have 'by_assignee'"
        assert "my_tickets" in data, "Response should have 'my_tickets'"
        assert "total" in data, "Response should have 'total'"
        
        # Verify by_status structure
        expected_statuses = ["todo", "in_progress", "waiting", "review", "resolved"]
        for status in expected_statuses:
            assert status in data["by_status"], f"'by_status' should have '{status}'"
            assert isinstance(data["by_status"][status], int), f"'{status}' count should be integer"
        
        # Verify by_assignee is a list
        assert isinstance(data["by_assignee"], list), "'by_assignee' should be a list"
        
        # Verify my_tickets is integer
        assert isinstance(data["my_tickets"], int), "'my_tickets' should be integer"
        
        # Verify total is integer
        assert isinstance(data["total"], int), "'total' should be integer"
        
        print(f"✅ Analytics summary: total={data['total']}, my_tickets={data['my_tickets']}, by_status={data['by_status']}")


class TestAnalyticsOverview:
    """Tests for GET /api/analytics/overview endpoint"""
    
    def test_analytics_overview_structure(self, api_client):
        """GET /api/analytics/overview returns correct structure with all required fields"""
        response = api_client.get(f"{BASE_URL}/api/analytics/overview?days=30")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify top-level structure
        assert "period_days" in data, "Response should have 'period_days'"
        assert "summary" in data, "Response should have 'summary'"
        assert "priority_breakdown" in data, "Response should have 'priority_breakdown'"
        assert "status_breakdown" in data, "Response should have 'status_breakdown'"
        assert "volume_trend" in data, "Response should have 'volume_trend'"
        assert "top_assignees" in data, "Response should have 'top_assignees'"
        
        # Verify period_days
        assert data["period_days"] == 30, f"Expected period_days=30, got {data['period_days']}"
        
        # Verify summary sub-structure
        summary = data["summary"]
        expected_summary_fields = [
            "total_tickets", "open_tickets", "tickets_in_period", 
            "resolved_in_period", "avg_resolution_hours", "sla_compliance_percent"
        ]
        for field in expected_summary_fields:
            assert field in summary, f"'summary' should have '{field}'"
        
        # Verify priority_breakdown structure
        priority = data["priority_breakdown"]
        expected_priorities = ["urgent", "high", "medium", "low"]
        for p in expected_priorities:
            assert p in priority, f"'priority_breakdown' should have '{p}'"
        
        # Verify status_breakdown structure
        status = data["status_breakdown"]
        expected_statuses = ["todo", "in_progress", "waiting", "review", "resolved"]
        for s in expected_statuses:
            assert s in status, f"'status_breakdown' should have '{s}'"
        
        # Verify volume_trend is a list
        assert isinstance(data["volume_trend"], list), "'volume_trend' should be a list"
        
        # Verify top_assignees is a list
        assert isinstance(data["top_assignees"], list), "'top_assignees' should be a list"
        
        print(f"✅ Analytics overview: period={data['period_days']} days, summary={summary}")


class TestTicketNotesPagination:
    """Tests for GET /api/tickets/{id}/notes endpoint"""
    
    def test_notes_returns_paginated_format(self, api_client):
        """GET /api/tickets/{id}/notes returns {messages, total, page, has_more}"""
        # First, get a ticket ID to test with
        tickets_response = api_client.get(f"{BASE_URL}/api/tickets?limit=1")
        assert tickets_response.status_code == 200
        
        tickets_data = tickets_response.json()
        if not tickets_data.get("tickets"):
            pytest.skip("No tickets available to test notes endpoint")
        
        ticket_id = tickets_data["tickets"][0].get("ticket_id")
        
        # Now test the notes endpoint
        response = api_client.get(f"{BASE_URL}/api/tickets/{ticket_id}/notes")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify required fields exist
        assert "messages" in data, "Response should have 'messages' array"
        assert "total" in data, "Response should have 'total' count"
        assert "page" in data, "Response should have 'page' number"
        assert "has_more" in data, "Response should have 'has_more' boolean"
        
        # Verify types
        assert isinstance(data["messages"], list), "'messages' should be a list"
        assert isinstance(data["total"], int), "'total' should be an integer"
        assert isinstance(data["page"], int), "'page' should be an integer"
        assert isinstance(data["has_more"], bool), "'has_more' should be a boolean"
        
        print(f"✅ Notes pagination for {ticket_id}: total={data['total']}, page={data['page']}, has_more={data['has_more']}")

    def test_activity_returns_paginated_format(self, api_client):
        """GET /api/tickets/{id}/activity also returns {messages, total, page, has_more}"""
        # First, get a ticket ID to test with
        tickets_response = api_client.get(f"{BASE_URL}/api/tickets?limit=1")
        assert tickets_response.status_code == 200
        
        tickets_data = tickets_response.json()
        if not tickets_data.get("tickets"):
            pytest.skip("No tickets available to test activity endpoint")
        
        ticket_id = tickets_data["tickets"][0].get("ticket_id")
        
        # Now test the activity endpoint
        response = api_client.get(f"{BASE_URL}/api/tickets/{ticket_id}/activity")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify required fields exist
        assert "messages" in data, "Response should have 'messages' array"
        assert "total" in data, "Response should have 'total' count"
        assert "page" in data, "Response should have 'page' number"
        assert "has_more" in data, "Response should have 'has_more' boolean"
        
        print(f"✅ Activity pagination for {ticket_id}: total={data['total']}, page={data['page']}, has_more={data['has_more']}")


class TestExportStreaming:
    """Tests for GET /api/export streaming endpoints"""
    
    def test_export_json_streaming(self, api_client):
        """GET /api/export?format=json returns valid streaming JSON array"""
        response = api_client.get(f"{BASE_URL}/api/export?format=json", stream=True)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify content type
        content_type = response.headers.get("Content-Type", "")
        assert "application/json" in content_type, f"Expected application/json, got {content_type}"
        
        # Verify Content-Disposition header
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disposition, "Should have attachment disposition"
        assert "tickets.json" in content_disposition, "Filename should be tickets.json"
        
        # Read and parse the JSON to verify it's valid
        content = response.content.decode('utf-8')
        try:
            data = json.loads(content)
            assert isinstance(data, list), "JSON export should be an array"
            print(f"✅ JSON export streaming: valid JSON array with {len(data)} tickets")
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON in export: {e}")

    def test_export_csv_streaming(self, api_client):
        """GET /api/export?format=csv returns valid streaming CSV"""
        response = api_client.get(f"{BASE_URL}/api/export?format=csv", stream=True)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify content type
        content_type = response.headers.get("Content-Type", "")
        assert "text/csv" in content_type, f"Expected text/csv, got {content_type}"
        
        # Verify Content-Disposition header
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disposition, "Should have attachment disposition"
        assert "tickets.csv" in content_disposition, "Filename should be tickets.csv"
        
        # Read content and verify it's valid CSV with header
        content = response.content.decode('utf-8')
        lines = content.strip().split('\n')
        
        assert len(lines) >= 1, "CSV should have at least a header row"
        
        # Verify expected fields in header
        header = lines[0]
        expected_fields = ["ticket_id", "title", "status"]
        for field in expected_fields:
            assert field in header, f"CSV header should contain '{field}'"
        
        print(f"✅ CSV export streaming: valid CSV with {len(lines)} lines (including header)")


class TestEmailStatus:
    """Tests for GET /api/email/status endpoint"""
    
    def test_email_status_structure(self, api_client):
        """GET /api/email/status returns IMAP connection status"""
        response = api_client.get(f"{BASE_URL}/api/email/status")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Response should have 'connected' field
        assert "connected" in data, "Response should have 'connected' field"
        assert isinstance(data["connected"], bool), "'connected' should be boolean"
        
        # If connected, should have email and inbox_count
        if data["connected"]:
            assert "email" in data, "Connected response should have 'email'"
            assert "inbox_count" in data, "Connected response should have 'inbox_count'"
            print(f"✅ Email status: connected=True, email={data['email']}, inbox_count={data['inbox_count']}")
        else:
            # If not connected, should have error
            assert "error" in data or "email" in data, "Not connected should have 'error' or 'email'"
            print(f"✅ Email status: connected=False, error={data.get('error', 'N/A')}")


class TestTicketCreationAndVerification:
    """Test ticket creation with the new response format"""
    
    def test_create_ticket_and_verify_in_list(self, api_client):
        """Create a ticket and verify it appears in the paginated list"""
        import time
        
        # Create a unique ticket
        unique_title = f"TEST_Scalability_Test_{int(time.time())}"
        create_payload = {
            "title": unique_title,
            "description": "Testing new pagination format",
            "status": "todo",
            "priority": "medium"
        }
        
        create_response = api_client.post(f"{BASE_URL}/api/tickets", json=create_payload)
        assert create_response.status_code == 200, f"Create failed: {create_response.text}"
        
        created_ticket = create_response.json()
        ticket_id = created_ticket.get("ticket_id")
        assert ticket_id, "Created ticket should have ticket_id"
        
        # Verify it appears in the list (new paginated format)
        list_response = api_client.get(f"{BASE_URL}/api/tickets?limit=100")
        assert list_response.status_code == 200
        
        list_data = list_response.json()
        assert "tickets" in list_data, "List should have 'tickets' array"
        
        # Find the created ticket
        found = any(t.get("ticket_id") == ticket_id for t in list_data["tickets"])
        assert found, f"Created ticket {ticket_id} not found in list"
        
        print(f"✅ Created ticket {ticket_id} verified in paginated list")
        
        # Cleanup - delete the test ticket
        api_client.delete(f"{BASE_URL}/api/tickets/{ticket_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
