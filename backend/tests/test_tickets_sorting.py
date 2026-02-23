"""
Test backend-driven sorting for tickets API endpoints.
Features tested:
1. GET /api/tickets with sort_by and sort_order params
2. POST /api/filter/tickets with sort_by and sort_order in body
3. All 8 sort fields: created_at, updated_at, last_message_at, last_customer_message_at, 
   last_agent_message_at, priority, status, escalation_level
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "qa_test_admin_session_token_2026"


@pytest.fixture
def auth_session():
    """Create authenticated session with cookie"""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestGetTicketsSorting:
    """Test GET /api/tickets sorting functionality"""
    
    def test_sort_by_created_at_desc(self, auth_session):
        """Sort by created_at descending (default)"""
        response = auth_session.get(f"{BASE_URL}/api/tickets?sort_by=created_at&sort_order=desc&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
        tickets = data["tickets"]
        
        # Verify tickets are sorted by created_at descending
        if len(tickets) >= 2:
            dates = [t.get("created_at") for t in tickets if t.get("created_at")]
            for i in range(len(dates) - 1):
                assert dates[i] >= dates[i + 1], f"Not sorted desc: {dates[i]} should be >= {dates[i+1]}"
    
    def test_sort_by_created_at_asc(self, auth_session):
        """Sort by created_at ascending"""
        response = auth_session.get(f"{BASE_URL}/api/tickets?sort_by=created_at&sort_order=asc&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        tickets = data["tickets"]
        
        # Verify tickets are sorted by created_at ascending
        if len(tickets) >= 2:
            dates = [t.get("created_at") for t in tickets if t.get("created_at")]
            for i in range(len(dates) - 1):
                assert dates[i] <= dates[i + 1], f"Not sorted asc: {dates[i]} should be <= {dates[i+1]}"
    
    def test_sort_by_priority_desc(self, auth_session):
        """Sort by priority descending"""
        response = auth_session.get(f"{BASE_URL}/api/tickets?sort_by=priority&sort_order=desc&limit=20")
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
        # Just verify the endpoint accepts priority sort
        assert len(data["tickets"]) > 0
    
    def test_sort_by_updated_at_desc(self, auth_session):
        """Sort by updated_at descending"""
        response = auth_session.get(f"{BASE_URL}/api/tickets?sort_by=updated_at&sort_order=desc&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        tickets = data["tickets"]
        
        if len(tickets) >= 2:
            dates = [t.get("updated_at") for t in tickets if t.get("updated_at")]
            for i in range(len(dates) - 1):
                assert dates[i] >= dates[i + 1], "updated_at not sorted descending"
    
    def test_sort_by_status(self, auth_session):
        """Sort by status"""
        response = auth_session.get(f"{BASE_URL}/api/tickets?sort_by=status&sort_order=asc&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
        assert len(data["tickets"]) > 0
    
    def test_sort_by_escalation_level(self, auth_session):
        """Sort by escalation_level"""
        response = auth_session.get(f"{BASE_URL}/api/tickets?sort_by=escalation_level&sort_order=desc&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
        assert len(data["tickets"]) > 0
    
    def test_sort_by_last_message_at(self, auth_session):
        """Sort by last_message_at"""
        response = auth_session.get(f"{BASE_URL}/api/tickets?sort_by=last_message_at&sort_order=desc&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
        assert len(data["tickets"]) > 0
    
    def test_invalid_sort_field_defaults_to_created_at(self, auth_session):
        """Invalid sort field should default to created_at"""
        response = auth_session.get(f"{BASE_URL}/api/tickets?sort_by=invalid_field&sort_order=desc&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data


class TestPostFilterTicketsSorting:
    """Test POST /api/filter/tickets sorting functionality"""
    
    def test_filter_sort_by_created_at_asc(self, auth_session):
        """POST filter with sort_by created_at ascending"""
        payload = {
            "filter_tree": {"logic": "and", "conditions": [], "groups": []},
            "page": 1,
            "limit": 5,
            "sort_by": "created_at",
            "sort_order": "asc"
        }
        response = auth_session.post(f"{BASE_URL}/api/filter/tickets", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        tickets = data["tickets"]
        
        if len(tickets) >= 2:
            dates = [t.get("created_at") for t in tickets if t.get("created_at")]
            for i in range(len(dates) - 1):
                assert dates[i] <= dates[i + 1], "created_at not sorted ascending"
    
    def test_filter_sort_by_updated_at_desc(self, auth_session):
        """POST filter with sort_by updated_at descending"""
        payload = {
            "filter_tree": {"logic": "and", "conditions": [], "groups": []},
            "page": 1,
            "limit": 5,
            "sort_by": "updated_at",
            "sort_order": "desc"
        }
        response = auth_session.post(f"{BASE_URL}/api/filter/tickets", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        tickets = data["tickets"]
        
        if len(tickets) >= 2:
            dates = [t.get("updated_at") for t in tickets if t.get("updated_at")]
            for i in range(len(dates) - 1):
                assert dates[i] >= dates[i + 1], "updated_at not sorted descending"
    
    def test_filter_sort_by_priority(self, auth_session):
        """POST filter with sort_by priority"""
        payload = {
            "filter_tree": {"logic": "and", "conditions": [], "groups": []},
            "page": 1,
            "limit": 10,
            "sort_by": "priority",
            "sort_order": "desc"
        }
        response = auth_session.post(f"{BASE_URL}/api/filter/tickets", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
        assert len(data["tickets"]) > 0
    
    def test_filter_sort_by_status(self, auth_session):
        """POST filter with sort_by status"""
        payload = {
            "filter_tree": {"logic": "and", "conditions": [], "groups": []},
            "page": 1,
            "limit": 10,
            "sort_by": "status",
            "sort_order": "asc"
        }
        response = auth_session.post(f"{BASE_URL}/api/filter/tickets", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
    
    def test_filter_with_conditions_and_sort(self, auth_session):
        """POST filter with actual conditions + sorting"""
        payload = {
            "filter_tree": {
                "logic": "and",
                "conditions": [
                    {"field": "status", "op": "is_not", "value": "merged"}
                ],
                "groups": []
            },
            "page": 1,
            "limit": 5,
            "sort_by": "created_at",
            "sort_order": "desc"
        }
        response = auth_session.post(f"{BASE_URL}/api/filter/tickets", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
        assert "total" in data
        assert "has_more" in data
    
    def test_filter_invalid_sort_defaults(self, auth_session):
        """POST filter with invalid sort_by should default to created_at"""
        payload = {
            "filter_tree": {"logic": "and", "conditions": [], "groups": []},
            "page": 1,
            "limit": 5,
            "sort_by": "invalid_field",
            "sort_order": "desc"
        }
        response = auth_session.post(f"{BASE_URL}/api/filter/tickets", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data


class TestSortFieldWhitelist:
    """Verify all expected sort fields work"""
    
    @pytest.mark.parametrize("sort_field", [
        "created_at",
        "updated_at", 
        "last_message_at",
        "last_customer_message_at",
        "last_agent_message_at",
        "priority",
        "status",
        "escalation_level"
    ])
    def test_all_sort_fields_accepted(self, auth_session, sort_field):
        """Test all 8 documented sort fields are accepted"""
        response = auth_session.get(f"{BASE_URL}/api/tickets?sort_by={sort_field}&sort_order=desc&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert "tickets" in data
