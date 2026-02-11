"""
Test suite for Custom Inbox CRUD and Sharing functionality.
Tests the following endpoints:
- POST /api/inboxes - Create a custom inbox
- GET /api/inboxes - List all inboxes for current user
- GET /api/inboxes/{inbox_id} - Get a single inbox
- PUT /api/inboxes/{inbox_id} - Update inbox name/color
- DELETE /api/inboxes/{inbox_id} - Delete an inbox
- POST /api/inboxes/{inbox_id}/share - Share inbox (creates decoupled copies)
- GET /api/inboxes/{inbox_id}/tickets - Get tickets matching inbox filter
- GET /api/users - Verify paginated response with items array
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
SESSION_TOKEN = "7N_TW_9vqeefrLlsBi_s9cZyXCYznDfSPaSt8iwcJic"
USER_ID = "user_5aeff57a3631"
OTHER_USER_IDS = ["b1bbdaf9-5ac0-47a9-ac7d-31b0b149010e", "test-user-1770831806742"]


@pytest.fixture(scope="session")
def api_client():
    """Shared requests session with auth cookie."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Cookie": f"session_token={SESSION_TOKEN}"
    })
    return session


@pytest.fixture(scope="function")
def test_inbox(api_client):
    """Create a test inbox and clean up after."""
    unique_suffix = uuid.uuid4().hex[:8]
    inbox_data = {
        "name": f"TEST_Inbox_{unique_suffix}",
        "filter_tree": {
            "logic": "and",
            "conditions": [{"field": "status", "op": "eq", "value": "todo"}],
            "groups": []
        },
        "color": "#3b82f6"
    }
    response = api_client.post(f"{BASE_URL}/api/inboxes", json=inbox_data)
    assert response.status_code == 200, f"Failed to create test inbox: {response.text}"
    inbox = response.json()
    yield inbox
    # Cleanup - delete the test inbox
    api_client.delete(f"{BASE_URL}/api/inboxes/{inbox['inbox_id']}")


class TestUsersEndpoint:
    """Verify /api/users returns paginated response with items array."""
    
    def test_users_returns_paginated_response(self, api_client):
        """Test that /api/users returns {items: [], total, skip, limit, has_more}."""
        response = api_client.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200
        
        data = response.json()
        # Verify paginated response structure
        assert "items" in data, "Response should have 'items' array"
        assert isinstance(data["items"], list), "'items' should be a list"
        assert "total" in data, "Response should have 'total'"
        assert "skip" in data, "Response should have 'skip'"
        assert "limit" in data, "Response should have 'limit'"
        assert "has_more" in data, "Response should have 'has_more'"
        
        # Verify items have user data
        if len(data["items"]) > 0:
            user = data["items"][0]
            assert "user_id" in user, "User should have 'user_id'"
            assert "email" in user, "User should have 'email'"
        
        print(f"✓ /api/users returns paginated response with {len(data['items'])} users, total={data['total']}")


class TestInboxCreate:
    """Test POST /api/inboxes - Create custom inbox."""
    
    def test_create_inbox_success(self, api_client):
        """Test creating a new inbox with filter_tree, name, color."""
        unique_suffix = uuid.uuid4().hex[:8]
        inbox_data = {
            "name": f"TEST_High Priority_{unique_suffix}",
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "priority", "op": "eq", "value": "high"}],
                "groups": []
            },
            "color": "#ef4444"
        }
        
        response = api_client.post(f"{BASE_URL}/api/inboxes", json=inbox_data)
        assert response.status_code == 200
        
        data = response.json()
        # Verify response structure
        assert "inbox_id" in data
        assert data["name"] == inbox_data["name"]
        assert data["color"] == "#ef4444"
        assert data["owner_id"] == USER_ID
        assert data["shared_with"] == []
        assert data["filter_tree"]["logic"] == "and"
        assert len(data["filter_tree"]["conditions"]) == 1
        assert data["filter_tree"]["conditions"][0]["field"] == "priority"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/inboxes/{data['inbox_id']}")
        print(f"✓ Created inbox {data['inbox_id']} with name '{data['name']}'")
    
    def test_create_inbox_with_complex_filter(self, api_client):
        """Test creating inbox with nested filter groups."""
        unique_suffix = uuid.uuid4().hex[:8]
        inbox_data = {
            "name": f"TEST_Complex_Filter_{unique_suffix}",
            "filter_tree": {
                "logic": "or",
                "conditions": [],
                "groups": [
                    {
                        "logic": "and",
                        "conditions": [
                            {"field": "status", "op": "eq", "value": "todo"},
                            {"field": "priority", "op": "eq", "value": "high"}
                        ],
                        "groups": []
                    },
                    {
                        "logic": "and",
                        "conditions": [
                            {"field": "source", "op": "eq", "value": "email"}
                        ],
                        "groups": []
                    }
                ]
            },
            "color": "#8b5cf6"
        }
        
        response = api_client.post(f"{BASE_URL}/api/inboxes", json=inbox_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["filter_tree"]["logic"] == "or"
        assert len(data["filter_tree"]["groups"]) == 2
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/inboxes/{data['inbox_id']}")
        print(f"✓ Created inbox with complex nested filter groups")
    
    def test_create_inbox_default_color(self, api_client):
        """Test that inbox gets default color if not specified."""
        unique_suffix = uuid.uuid4().hex[:8]
        inbox_data = {
            "name": f"TEST_Default_Color_{unique_suffix}",
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "status", "op": "eq", "value": "todo"}],
                "groups": []
            }
        }
        
        response = api_client.post(f"{BASE_URL}/api/inboxes", json=inbox_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["color"] == "#6b7280", "Default color should be #6b7280"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/inboxes/{data['inbox_id']}")
        print(f"✓ Inbox created with default color #6b7280")


class TestInboxRead:
    """Test GET /api/inboxes and GET /api/inboxes/{inbox_id}."""
    
    def test_get_all_inboxes(self, api_client, test_inbox):
        """Test listing all inboxes for current user."""
        response = api_client.get(f"{BASE_URL}/api/inboxes")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Find our test inbox
        inbox_ids = [i["inbox_id"] for i in data]
        assert test_inbox["inbox_id"] in inbox_ids, "Test inbox should be in list"
        print(f"✓ GET /api/inboxes returns {len(data)} inboxes")
    
    def test_get_single_inbox(self, api_client, test_inbox):
        """Test getting a single inbox by ID."""
        response = api_client.get(f"{BASE_URL}/api/inboxes/{test_inbox['inbox_id']}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["inbox_id"] == test_inbox["inbox_id"]
        assert data["name"] == test_inbox["name"]
        assert data["owner_id"] == USER_ID
        print(f"✓ GET /api/inboxes/{test_inbox['inbox_id']} returns correct inbox")
    
    def test_get_nonexistent_inbox(self, api_client):
        """Test getting a non-existent inbox returns 404."""
        response = api_client.get(f"{BASE_URL}/api/inboxes/inbox_nonexistent123")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
        print("✓ GET non-existent inbox returns 404")


class TestInboxUpdate:
    """Test PUT /api/inboxes/{inbox_id} - Update inbox."""
    
    def test_update_inbox_name(self, api_client, test_inbox):
        """Test updating inbox name."""
        new_name = f"TEST_Updated_Name_{uuid.uuid4().hex[:6]}"
        
        response = api_client.put(
            f"{BASE_URL}/api/inboxes/{test_inbox['inbox_id']}",
            json={"name": new_name}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == new_name
        assert data["color"] == test_inbox["color"], "Color should remain unchanged"
        
        # Verify persistence with GET
        get_response = api_client.get(f"{BASE_URL}/api/inboxes/{test_inbox['inbox_id']}")
        assert get_response.json()["name"] == new_name
        print(f"✓ Updated inbox name to '{new_name}'")
    
    def test_update_inbox_color(self, api_client, test_inbox):
        """Test updating inbox color."""
        new_color = "#22c55e"
        
        response = api_client.put(
            f"{BASE_URL}/api/inboxes/{test_inbox['inbox_id']}",
            json={"color": new_color}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["color"] == new_color
        
        # Verify persistence
        get_response = api_client.get(f"{BASE_URL}/api/inboxes/{test_inbox['inbox_id']}")
        assert get_response.json()["color"] == new_color
        print(f"✓ Updated inbox color to '{new_color}'")
    
    def test_update_inbox_name_and_color(self, api_client, test_inbox):
        """Test updating both name and color simultaneously."""
        updates = {
            "name": f"TEST_Both_Updated_{uuid.uuid4().hex[:6]}",
            "color": "#f59e0b"
        }
        
        response = api_client.put(
            f"{BASE_URL}/api/inboxes/{test_inbox['inbox_id']}",
            json=updates
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == updates["name"]
        assert data["color"] == updates["color"]
        print(f"✓ Updated both name and color simultaneously")
    
    def test_update_nonexistent_inbox(self, api_client):
        """Test updating a non-existent inbox returns 404."""
        response = api_client.put(
            f"{BASE_URL}/api/inboxes/inbox_nonexistent123",
            json={"name": "New Name"}
        )
        assert response.status_code == 404
        print("✓ PUT non-existent inbox returns 404")


class TestInboxDelete:
    """Test DELETE /api/inboxes/{inbox_id}."""
    
    def test_delete_inbox(self, api_client):
        """Test deleting an inbox."""
        # Create inbox to delete
        unique_suffix = uuid.uuid4().hex[:8]
        create_response = api_client.post(f"{BASE_URL}/api/inboxes", json={
            "name": f"TEST_To_Delete_{unique_suffix}",
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "status", "op": "eq", "value": "todo"}],
                "groups": []
            }
        })
        inbox_id = create_response.json()["inbox_id"]
        
        # Delete the inbox
        delete_response = api_client.delete(f"{BASE_URL}/api/inboxes/{inbox_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["message"] == "Inbox deleted"
        
        # Verify deletion with GET
        get_response = api_client.get(f"{BASE_URL}/api/inboxes/{inbox_id}")
        assert get_response.status_code == 404
        print(f"✓ Deleted inbox {inbox_id} and verified with GET 404")
    
    def test_delete_nonexistent_inbox(self, api_client):
        """Test deleting a non-existent inbox returns 404."""
        response = api_client.delete(f"{BASE_URL}/api/inboxes/inbox_nonexistent123")
        assert response.status_code == 404
        print("✓ DELETE non-existent inbox returns 404")


class TestInboxShare:
    """Test POST /api/inboxes/{inbox_id}/share - Share inbox (decoupled copies)."""
    
    def test_share_inbox_creates_decoupled_copy(self, api_client):
        """Test that sharing creates a decoupled copy for recipient."""
        # Create inbox to share
        unique_suffix = uuid.uuid4().hex[:8]
        create_response = api_client.post(f"{BASE_URL}/api/inboxes", json={
            "name": f"TEST_Shareable_{unique_suffix}",
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "priority", "op": "eq", "value": "medium"}],
                "groups": []
            },
            "color": "#10b981"
        })
        assert create_response.status_code == 200
        inbox = create_response.json()
        
        # Share with another user
        share_response = api_client.post(
            f"{BASE_URL}/api/inboxes/{inbox['inbox_id']}/share",
            json={"user_ids": [OTHER_USER_IDS[0]]}
        )
        assert share_response.status_code == 200
        
        share_data = share_response.json()
        assert "shared_with" in share_data
        assert "total" in share_data
        assert share_data["total"] == 1
        assert len(share_data["shared_with"]) == 1
        assert share_data["shared_with"][0]["user_id"] == OTHER_USER_IDS[0]
        assert "inbox_id" in share_data["shared_with"][0]
        
        # The copy inbox_id should be different from original
        copy_inbox_id = share_data["shared_with"][0]["inbox_id"]
        assert copy_inbox_id != inbox["inbox_id"], "Copy should have different inbox_id"
        
        # Cleanup - delete original inbox (copy belongs to other user)
        api_client.delete(f"{BASE_URL}/api/inboxes/{inbox['inbox_id']}")
        print(f"✓ Shared inbox created decoupled copy {copy_inbox_id} for user {OTHER_USER_IDS[0]}")
    
    def test_share_with_multiple_users(self, api_client):
        """Test sharing inbox with multiple users."""
        unique_suffix = uuid.uuid4().hex[:8]
        create_response = api_client.post(f"{BASE_URL}/api/inboxes", json={
            "name": f"TEST_Multi_Share_{unique_suffix}",
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "status", "op": "eq", "value": "todo"}],
                "groups": []
            }
        })
        inbox = create_response.json()
        
        # Share with two users
        share_response = api_client.post(
            f"{BASE_URL}/api/inboxes/{inbox['inbox_id']}/share",
            json={"user_ids": OTHER_USER_IDS}
        )
        assert share_response.status_code == 200
        
        share_data = share_response.json()
        assert share_data["total"] == 2, f"Expected 2 shares, got {share_data['total']}"
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/inboxes/{inbox['inbox_id']}")
        print(f"✓ Shared inbox with {share_data['total']} users")
    
    def test_share_inbox_skips_self(self, api_client):
        """Test that sharing with self is skipped."""
        unique_suffix = uuid.uuid4().hex[:8]
        create_response = api_client.post(f"{BASE_URL}/api/inboxes", json={
            "name": f"TEST_Self_Share_{unique_suffix}",
            "filter_tree": {
                "logic": "and",
                "conditions": [],
                "groups": []
            }
        })
        inbox = create_response.json()
        
        # Try to share with self and another user
        share_response = api_client.post(
            f"{BASE_URL}/api/inboxes/{inbox['inbox_id']}/share",
            json={"user_ids": [USER_ID, OTHER_USER_IDS[0]]}
        )
        assert share_response.status_code == 200
        
        share_data = share_response.json()
        # Should only create copy for other user, not self
        assert share_data["total"] == 1
        assert share_data["shared_with"][0]["user_id"] == OTHER_USER_IDS[0]
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/inboxes/{inbox['inbox_id']}")
        print("✓ Share correctly skips self-sharing")
    
    def test_share_nonexistent_inbox(self, api_client):
        """Test sharing a non-existent inbox returns 404."""
        response = api_client.post(
            f"{BASE_URL}/api/inboxes/inbox_nonexistent123/share",
            json={"user_ids": [OTHER_USER_IDS[0]]}
        )
        assert response.status_code == 404
        print("✓ Share non-existent inbox returns 404")
    
    def test_share_with_invalid_user(self, api_client):
        """Test sharing with non-existent user skips that user."""
        unique_suffix = uuid.uuid4().hex[:8]
        create_response = api_client.post(f"{BASE_URL}/api/inboxes", json={
            "name": f"TEST_Invalid_User_Share_{unique_suffix}",
            "filter_tree": {
                "logic": "and",
                "conditions": [],
                "groups": []
            }
        })
        inbox = create_response.json()
        
        # Share with invalid user and valid user
        share_response = api_client.post(
            f"{BASE_URL}/api/inboxes/{inbox['inbox_id']}/share",
            json={"user_ids": ["invalid_user_xyz", OTHER_USER_IDS[0]]}
        )
        assert share_response.status_code == 200
        
        share_data = share_response.json()
        # Should only create copy for valid user
        assert share_data["total"] == 1
        assert share_data["shared_with"][0]["user_id"] == OTHER_USER_IDS[0]
        
        # Cleanup
        api_client.delete(f"{BASE_URL}/api/inboxes/{inbox['inbox_id']}")
        print("✓ Share correctly skips invalid users")


class TestInboxTickets:
    """Test GET /api/inboxes/{inbox_id}/tickets - Get filtered tickets."""
    
    def test_get_inbox_tickets(self, api_client, test_inbox):
        """Test getting tickets matching inbox filter."""
        response = api_client.get(
            f"{BASE_URL}/api/inboxes/{test_inbox['inbox_id']}/tickets",
            params={"page": 1, "limit": 10}
        )
        assert response.status_code == 200
        
        data = response.json()
        # Verify response structure
        assert "tickets" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "has_more" in data
        assert "inbox" in data
        
        assert isinstance(data["tickets"], list)
        assert data["page"] == 1
        assert data["limit"] == 10
        
        # Verify inbox is included in response
        assert data["inbox"]["inbox_id"] == test_inbox["inbox_id"]
        print(f"✓ GET inbox tickets returns {len(data['tickets'])} tickets, total={data['total']}")
    
    def test_get_inbox_tickets_pagination(self, api_client, test_inbox):
        """Test pagination of inbox tickets."""
        # Get first page
        response1 = api_client.get(
            f"{BASE_URL}/api/inboxes/{test_inbox['inbox_id']}/tickets",
            params={"page": 1, "limit": 5}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Get second page
        response2 = api_client.get(
            f"{BASE_URL}/api/inboxes/{test_inbox['inbox_id']}/tickets",
            params={"page": 2, "limit": 5}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # If there are enough tickets, pages should have different results
        if data1["total"] > 5:
            ticket_ids_1 = [t["ticket_id"] for t in data1["tickets"]]
            ticket_ids_2 = [t["ticket_id"] for t in data2["tickets"]]
            # No overlap between pages
            assert set(ticket_ids_1).isdisjoint(set(ticket_ids_2)), "Pages should not overlap"
        
        print(f"✓ Pagination works: page 1 has {len(data1['tickets'])}, page 2 has {len(data2['tickets'])} tickets")
    
    def test_get_nonexistent_inbox_tickets(self, api_client):
        """Test getting tickets for non-existent inbox returns 404."""
        response = api_client.get(f"{BASE_URL}/api/inboxes/inbox_nonexistent123/tickets")
        assert response.status_code == 404
        print("✓ GET tickets for non-existent inbox returns 404")


class TestFullCRUDLifecycle:
    """Test the complete CRUD lifecycle: create -> get -> update -> share -> delete."""
    
    def test_full_inbox_lifecycle(self, api_client):
        """Test complete lifecycle of an inbox."""
        unique_suffix = uuid.uuid4().hex[:8]
        
        # 1. CREATE
        create_data = {
            "name": f"TEST_Lifecycle_{unique_suffix}",
            "filter_tree": {
                "logic": "and",
                "conditions": [{"field": "status", "op": "eq", "value": "todo"}],
                "groups": []
            },
            "color": "#3b82f6"
        }
        create_response = api_client.post(f"{BASE_URL}/api/inboxes", json=create_data)
        assert create_response.status_code == 200
        inbox = create_response.json()
        inbox_id = inbox["inbox_id"]
        print(f"  1. Created inbox: {inbox_id}")
        
        # 2. GET - Verify creation
        get_response = api_client.get(f"{BASE_URL}/api/inboxes/{inbox_id}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == create_data["name"]
        print(f"  2. Verified inbox exists via GET")
        
        # 3. UPDATE - Change name and color
        update_data = {"name": f"TEST_Updated_Lifecycle_{unique_suffix}", "color": "#22c55e"}
        update_response = api_client.put(f"{BASE_URL}/api/inboxes/{inbox_id}", json=update_data)
        assert update_response.status_code == 200
        assert update_response.json()["name"] == update_data["name"]
        assert update_response.json()["color"] == update_data["color"]
        print(f"  3. Updated inbox name and color")
        
        # 4. GET - Verify update persisted
        get_updated_response = api_client.get(f"{BASE_URL}/api/inboxes/{inbox_id}")
        assert get_updated_response.status_code == 200
        assert get_updated_response.json()["name"] == update_data["name"]
        print(f"  4. Verified update persisted via GET")
        
        # 5. SHARE - Create decoupled copy for another user
        share_response = api_client.post(
            f"{BASE_URL}/api/inboxes/{inbox_id}/share",
            json={"user_ids": [OTHER_USER_IDS[0]]}
        )
        assert share_response.status_code == 200
        share_data = share_response.json()
        assert share_data["total"] == 1
        copy_inbox_id = share_data["shared_with"][0]["inbox_id"]
        print(f"  5. Shared inbox, created copy: {copy_inbox_id}")
        
        # 6. GET TICKETS - Verify tickets endpoint works
        tickets_response = api_client.get(f"{BASE_URL}/api/inboxes/{inbox_id}/tickets")
        assert tickets_response.status_code == 200
        assert "tickets" in tickets_response.json()
        print(f"  6. Verified tickets endpoint works")
        
        # 7. DELETE
        delete_response = api_client.delete(f"{BASE_URL}/api/inboxes/{inbox_id}")
        assert delete_response.status_code == 200
        print(f"  7. Deleted inbox")
        
        # 8. GET - Verify deletion
        get_deleted_response = api_client.get(f"{BASE_URL}/api/inboxes/{inbox_id}")
        assert get_deleted_response.status_code == 404
        print(f"  8. Verified deletion via GET 404")
        
        print(f"✓ Full CRUD lifecycle completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
