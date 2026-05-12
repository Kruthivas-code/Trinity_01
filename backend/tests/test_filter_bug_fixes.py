"""
Backend tests specifically for the filter bug fixes:
1. /api/users returns paginated object - frontend correctly extracts .items array
2. /api/filter/tickets handles empty field conditions gracefully (field='' should not crash)
3. Database indexes exist for scalable filtering (100K+ tickets)
"""

import pytest
import requests
import os
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://repo-builder-71.preview.emergentagent.com")
SESSION_TOKEN = "7N_TW_9vqeefrLlsBi_s9cZyXCYznDfSPaSt8iwcJic"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


@pytest.fixture
def auth_session():
    """Create authenticated session"""
    session = requests.Session()
    session.cookies.set("session_token", SESSION_TOKEN)
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestUsersEndpointPaginatedResponse:
    """Test that /api/users returns paginated object with .items array"""
    
    def test_users_returns_paginated_object(self, auth_session):
        """GET /api/users returns {items: [], total, skip, limit, has_more}"""
        response = auth_session.get(f"{BASE_URL}/api/users")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Must be a dict (not array) with paginated structure
        assert isinstance(data, dict), f"Expected dict, got {type(data).__name__}"
        assert "items" in data, "Response must have 'items' key"
        assert isinstance(data["items"], list), "'items' must be an array"
        assert "total" in data, "Response must have 'total' key"
        
        # Check users have expected structure
        if data["items"]:
            user = data["items"][0]
            assert "user_id" in user or "id" in user, "User must have user_id or id"
            assert "email" in user or "name" in user, "User must have email or name"
        
        print(f"SUCCESS: /api/users returns paginated object with {len(data['items'])} users")


class TestEmptyFieldConditionHandling:
    """Test that filter handles empty field conditions gracefully"""
    
    def test_empty_field_only_does_not_crash(self, auth_session):
        """Filter with only empty field condition should not crash"""
        payload = {
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "", "op": "is", "value": ""}],
                "groups": []
            },
            "page": 1,
            "limit": 10
        }
        
        response = auth_session.post(f"{BASE_URL}/api/filter/tickets", json=payload)
        
        # Should succeed, not crash with 500
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "tickets" in data, "Response must have 'tickets' key"
        
        print("SUCCESS: Empty field condition handled gracefully")
    
    def test_empty_field_mixed_with_valid(self, auth_session):
        """Filter with empty field mixed with valid conditions should work"""
        payload = {
            "filter_tree": {
                "logic": "and",
                "conditions": [
                    {"field": "status", "op": "is", "value": "todo"},
                    {"field": "", "op": "is", "value": "ignored"}
                ],
                "groups": []
            },
            "page": 1,
            "limit": 10
        }
        
        response = auth_session.post(f"{BASE_URL}/api/filter/tickets", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Should filter by status=todo only, ignoring empty field
        for ticket in data.get("tickets", []):
            assert ticket.get("status") == "todo", f"Expected status='todo', got {ticket.get('status')}"
        
        print(f"SUCCESS: Empty field ignored, valid filter applied ({len(data['tickets'])} tickets)")
    
    def test_empty_field_in_nested_group(self, auth_session):
        """Empty field in nested group should not crash"""
        payload = {
            "filter_tree": {
                "logic": "or",
                "conditions": [],
                "groups": [
                    {
                        "logic": "and",
                        "conditions": [{"field": "", "op": "is", "value": ""}],
                        "groups": []
                    },
                    {
                        "logic": "and",
                        "conditions": [{"field": "status", "op": "is", "value": "todo"}],
                        "groups": []
                    }
                ]
            },
            "page": 1,
            "limit": 10
        }
        
        response = auth_session.post(f"{BASE_URL}/api/filter/tickets", json=payload)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        print("SUCCESS: Empty field in nested group handled gracefully")


class TestDatabaseIndexes:
    """Verify required database indexes exist for scalable filtering"""
    
    def test_tickets_collection_indexes(self):
        """Check tickets collection has required indexes for filtering"""
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        indexes = list(db.tickets.list_indexes())
        index_keys = [dict(idx.get('key', {})) for idx in indexes]
        
        # Check single-field indexes
        required_single = ['source', 'tags', 'priority', 'status', 'assignee_id', 'created_at']
        for field in required_single:
            found = any(field in idx for idx in index_keys)
            assert found, f"Missing index on '{field}'"
        
        print(f"SUCCESS: All required single-field indexes present")
    
    def test_compound_indexes_for_filtering(self):
        """Check compound indexes for common filter patterns"""
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        indexes = list(db.tickets.list_indexes())
        
        # Check compound indexes
        has_priority_created = any(
            'priority' in idx.get('key', {}) and 'created_at' in idx.get('key', {})
            for idx in indexes
        )
        has_source_created = any(
            'source' in idx.get('key', {}) and 'created_at' in idx.get('key', {})
            for idx in indexes
        )
        has_status_priority_created = any(
            'status' in idx.get('key', {}) and 'priority' in idx.get('key', {}) and 'created_at' in idx.get('key', {})
            for idx in indexes
        )
        
        assert has_priority_created, "Missing compound index: priority + created_at"
        assert has_source_created, "Missing compound index: source + created_at"
        assert has_status_priority_created, "Missing compound index: status + priority + created_at"
        
        print("SUCCESS: All required compound indexes present")
    
    def test_custom_inboxes_indexes(self):
        """Check custom_inboxes collection has required indexes"""
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        
        indexes = list(db.custom_inboxes.list_indexes())
        index_keys = [dict(idx.get('key', {})) for idx in indexes]
        
        required = ['inbox_id', 'owner_id', 'shared_with']
        for field in required:
            found = any(field in idx for idx in index_keys)
            assert found, f"Missing index on custom_inboxes.{field}"
        
        print("SUCCESS: All custom_inboxes indexes present")


class TestFilterFieldsEndpoint:
    """Test /api/filter/fields returns correct field definitions"""
    
    def test_filter_fields_returns_array(self, auth_session):
        """GET /api/filter/fields returns array of field definitions"""
        response = auth_session.get(f"{BASE_URL}/api/filter/fields")
        
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), f"Expected list, got {type(data).__name__}"
        assert len(data) > 0, "Expected at least some fields"
        
        # Check structure of each field
        for field in data:
            assert "field" in field, "Each field must have 'field' key"
            assert "type" in field, "Each field must have 'type' key"
            assert "label" in field, "Each field must have 'label' key"
        
        print(f"SUCCESS: /api/filter/fields returns {len(data)} field definitions")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
