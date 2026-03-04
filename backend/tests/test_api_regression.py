"""
API regression tests for tickets and portal categories endpoints.
Tests:
- GET /api/tickets returns tickets correctly with session auth
- GET /api/portal/categories returns categories with kb_group_key field
"""
import sys
import os

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
import requests

# Use the public URL for API tests
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://columns-rebuild.preview.emergentagent.com').rstrip('/')
SESSION_TOKEN = "test_kb_session_token"


class TestTicketsEndpoint:
    """Test GET /api/tickets endpoint."""
    
    def test_tickets_endpoint_requires_auth(self):
        """Verify /api/tickets requires authentication."""
        response = requests.get(f"{BASE_URL}/api/tickets")
        # Should return 401 or redirect without auth
        assert response.status_code in [401, 403, 302], f"Expected auth required, got {response.status_code}"
    
    def test_tickets_endpoint_returns_200_with_auth(self):
        """Verify /api/tickets returns 200 with valid session token."""
        response = requests.get(
            f"{BASE_URL}/api/tickets",
            cookies={"session_token": SESSION_TOKEN}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
    
    def test_tickets_endpoint_returns_list(self):
        """Verify /api/tickets returns a tickets list."""
        response = requests.get(
            f"{BASE_URL}/api/tickets",
            cookies={"session_token": SESSION_TOKEN}
        )
        data = response.json()
        assert "tickets" in data, f"Expected 'tickets' key in response, got: {list(data.keys())}"
        assert isinstance(data["tickets"], list), "Expected tickets to be a list"
    
    def test_tickets_have_required_fields(self):
        """Verify tickets have required fields."""
        response = requests.get(
            f"{BASE_URL}/api/tickets",
            cookies={"session_token": SESSION_TOKEN}
        )
        data = response.json()
        
        if data["tickets"]:
            ticket = data["tickets"][0]
            required_fields = [
                "ticket_id", "title", "status", "priority", 
                "created_at", "updated_at"
            ]
            for field in required_fields:
                assert field in ticket, f"Missing field: {field}"


class TestPortalCategoriesEndpoint:
    """Test GET /api/portal/categories endpoint."""
    
    def test_categories_endpoint_returns_200(self):
        """Verify /api/portal/categories returns 200."""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_categories_returns_list(self):
        """Verify /api/portal/categories returns a categories list."""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        data = response.json()
        assert "categories" in data, f"Expected 'categories' key in response, got: {list(data.keys())}"
        assert isinstance(data["categories"], list), "Expected categories to be a list"
    
    def test_categories_have_kb_group_key_field(self):
        """Verify categories include kb_group_key field."""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        data = response.json()
        
        assert len(data["categories"]) > 0, "Expected at least one category"
        
        # Check that all categories have kb_group_key field (even if null/None)
        for category in data["categories"]:
            assert "kb_group_key" in category, f"Category missing kb_group_key: {category.get('title', 'unknown')}"
    
    def test_categories_have_required_fields(self):
        """Verify categories have all required fields."""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        data = response.json()
        
        if data["categories"]:
            category = data["categories"][0]
            required_fields = ["title", "slug", "kb_group_key"]
            for field in required_fields:
                assert field in category, f"Category missing field: {field}"
    
    def test_some_categories_have_kb_group_key_value(self):
        """Verify at least one category has a non-null kb_group_key value."""
        response = requests.get(f"{BASE_URL}/api/portal/categories")
        data = response.json()
        
        # At least one category should have a KB group linked
        has_kb_group = any(
            cat.get("kb_group_key") is not None and cat.get("kb_group_key") != ""
            for cat in data["categories"]
        )
        assert has_kb_group, "Expected at least one category to have kb_group_key linked"
