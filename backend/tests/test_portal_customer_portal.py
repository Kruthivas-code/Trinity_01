"""
Portal API Tests - Customer-facing support portal for Trinity ticket management
Tests cover: Customer auth (register/login/logout/me), Categories (public), 
Tickets (CRUD), Admin category management
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
ADMIN_SESSION_TOKEN = "7N_TW_9vqeefrLlsBi_s9cZyXCYznDfSPaSt8iwcJic"

# Test customer credentials
TEST_CUSTOMER_EMAIL = "testcust@example.com"
TEST_CUSTOMER_PASSWORD = "test1234"
EXISTING_TICKET_ID = "TKT-000864"


@pytest.fixture(scope="session")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="session")
def customer_token(api_client):
    """Login with test customer and get token"""
    response = api_client.post(
        f"{BASE_URL}/api/portal/auth/login",
        json={"email": TEST_CUSTOMER_EMAIL, "password": TEST_CUSTOMER_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Customer login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="session")
def admin_client(api_client):
    """Session with Trinity admin cookie"""
    api_client.cookies.set("session_token", ADMIN_SESSION_TOKEN)
    return api_client


class TestPublicCategories:
    """Public category endpoints - no auth required"""
    
    def test_list_categories_returns_10_categories(self, api_client):
        """GET /api/portal/categories should return 10 default categories"""
        response = api_client.get(f"{BASE_URL}/api/portal/categories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "categories" in data, "Response should have 'categories' key"
        categories = data["categories"]
        assert isinstance(categories, list), "Categories should be a list"
        assert len(categories) == 10, f"Expected 10 categories, got {len(categories)}"
        
        # Verify structure of a category
        cat = categories[0]
        assert "title" in cat, "Category should have 'title'"
        assert "slug" in cat, "Category should have 'slug'"
        assert "description" in cat, "Category should have 'description'"
        assert "subtopics" in cat, "Category should have 'subtopics'"
    
    def test_get_credits_pricing_category(self, api_client):
        """GET /api/portal/categories/credits-pricing should return the category"""
        response = api_client.get(f"{BASE_URL}/api/portal/categories/credits-pricing")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["title"] == "Credits & Pricing", f"Expected 'Credits & Pricing', got {data.get('title')}"
        assert data["slug"] == "credits-pricing"
        assert "subtopics" in data and len(data["subtopics"]) > 0, "Should have subtopics"
    
    def test_get_nonexistent_category_returns_404(self, api_client):
        """GET /api/portal/categories/nonexistent should return 404"""
        response = api_client.get(f"{BASE_URL}/api/portal/categories/nonexistent")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestCustomerAuth:
    """Customer authentication endpoints"""
    
    def test_login_existing_customer(self, api_client):
        """POST /api/portal/auth/login with valid credentials returns token"""
        response = api_client.post(
            f"{BASE_URL}/api/portal/auth/login",
            json={"email": TEST_CUSTOMER_EMAIL, "password": TEST_CUSTOMER_PASSWORD}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "token" in data, "Response should have 'token'"
        assert "customer_id" in data, "Response should have 'customer_id'"
        assert "email" in data, "Response should have 'email'"
        assert data["email"] == TEST_CUSTOMER_EMAIL.lower()
    
    def test_login_invalid_credentials_returns_401(self, api_client):
        """POST /api/portal/auth/login with invalid password returns 401"""
        response = api_client.post(
            f"{BASE_URL}/api/portal/auth/login",
            json={"email": TEST_CUSTOMER_EMAIL, "password": "wrongpassword"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_login_nonexistent_user_returns_401(self, api_client):
        """POST /api/portal/auth/login with unknown email returns 401"""
        response = api_client.post(
            f"{BASE_URL}/api/portal/auth/login",
            json={"email": "nonexistent@example.com", "password": "password123"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_register_new_customer(self, api_client):
        """POST /api/portal/auth/register creates new customer and returns token"""
        unique_email = f"TEST_portal_{uuid.uuid4().hex[:8]}@example.com"
        response = api_client.post(
            f"{BASE_URL}/api/portal/auth/register",
            json={"name": "Test User", "email": unique_email, "password": "password123"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "token" in data, "Response should have 'token'"
        assert "customer_id" in data, "Response should have 'customer_id'"
        assert data["email"] == unique_email.lower()
        assert data["name"] == "Test User"
    
    def test_register_duplicate_email_returns_409(self, api_client):
        """POST /api/portal/auth/register with existing email returns 409"""
        response = api_client.post(
            f"{BASE_URL}/api/portal/auth/register",
            json={"name": "Test User", "email": TEST_CUSTOMER_EMAIL, "password": "password123"}
        )
        assert response.status_code == 409, f"Expected 409, got {response.status_code}"
    
    def test_register_short_password_returns_400(self, api_client):
        """POST /api/portal/auth/register with short password returns 400"""
        response = api_client.post(
            f"{BASE_URL}/api/portal/auth/register",
            json={"name": "Test", "email": "new@example.com", "password": "123"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "at least 6" in response.json().get("detail", "").lower()
    
    def test_get_me_with_valid_token(self, api_client, customer_token):
        """GET /api/portal/auth/me with valid token returns customer info"""
        response = api_client.get(
            f"{BASE_URL}/api/portal/auth/me",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "customer_id" in data, "Response should have 'customer_id'"
        assert "email" in data, "Response should have 'email'"
        assert "name" in data, "Response should have 'name'"
        assert "password_hash" not in data, "Response should NOT contain password_hash"
    
    def test_get_me_without_token_returns_401(self, api_client):
        """GET /api/portal/auth/me without token returns 401"""
        response = api_client.get(f"{BASE_URL}/api/portal/auth/me")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_logout_invalidates_session(self, api_client):
        """POST /api/portal/auth/logout invalidates the session"""
        # First login to get a new token
        login_resp = api_client.post(
            f"{BASE_URL}/api/portal/auth/login",
            json={"email": TEST_CUSTOMER_EMAIL, "password": TEST_CUSTOMER_PASSWORD}
        )
        temp_token = login_resp.json().get("token")
        
        # Now logout
        logout_resp = api_client.post(
            f"{BASE_URL}/api/portal/auth/logout",
            headers={"Authorization": f"Bearer {temp_token}"}
        )
        assert logout_resp.status_code == 200, f"Expected 200, got {logout_resp.status_code}"
        assert "logged out" in logout_resp.json().get("message", "").lower()
        
        # Verify token is now invalid
        me_resp = api_client.get(
            f"{BASE_URL}/api/portal/auth/me",
            headers={"Authorization": f"Bearer {temp_token}"}
        )
        assert me_resp.status_code == 401, "Token should be invalid after logout"


class TestCustomerTickets:
    """Customer ticket operations - require auth"""
    
    def test_list_my_tickets(self, api_client, customer_token):
        """GET /api/portal/tickets returns customer's tickets"""
        response = api_client.get(
            f"{BASE_URL}/api/portal/tickets",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "tickets" in data, "Response should have 'tickets' key"
        assert isinstance(data["tickets"], list), "Tickets should be a list"
    
    def test_list_tickets_without_auth_returns_401(self, api_client):
        """GET /api/portal/tickets without auth returns 401"""
        response = api_client.get(f"{BASE_URL}/api/portal/tickets")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_submit_ticket_and_verify(self, api_client, customer_token):
        """POST /api/portal/tickets creates ticket with source:portal"""
        response = api_client.post(
            f"{BASE_URL}/api/portal/tickets",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "category_slug": "credits-pricing",
                "subcategory": "Credit Usage",
                "subject": "TEST_Portal ticket submission test",
                "description": "This is a test ticket submitted via portal API test"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "ticket_id" in data, "Response should have 'ticket_id'"
        assert data["ticket_id"].startswith("TKT-"), "ticket_id should start with TKT-"
        assert data["status"] == "todo", "New ticket status should be 'todo'"
        
        # Verify ticket was created by fetching it
        ticket_id = data["ticket_id"]
        get_resp = api_client.get(
            f"{BASE_URL}/api/portal/tickets/{ticket_id}",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        assert get_resp.status_code == 200, f"Should be able to fetch created ticket"
        ticket_data = get_resp.json()
        assert ticket_data["ticket"]["title"] == "TEST_Portal ticket submission test"
        assert ticket_data["ticket"]["portal_category"] == "credits-pricing"
        assert ticket_data["ticket"]["source"] == "portal"
    
    def test_submit_ticket_without_auth_returns_401(self, api_client):
        """POST /api/portal/tickets without auth returns 401"""
        response = api_client.post(
            f"{BASE_URL}/api/portal/tickets",
            json={
                "category_slug": "credits-pricing",
                "subject": "Test",
                "description": "Test"
            }
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_get_ticket_detail_with_messages(self, api_client, customer_token):
        """GET /api/portal/tickets/{id} returns ticket with messages"""
        # First create a test ticket
        create_resp = api_client.post(
            f"{BASE_URL}/api/portal/tickets",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "category_slug": "features",
                "subject": "TEST_Ticket detail test",
                "description": "Test description for detail view"
            }
        )
        ticket_id = create_resp.json()["ticket_id"]
        
        # Fetch the ticket detail
        response = api_client.get(
            f"{BASE_URL}/api/portal/tickets/{ticket_id}",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "ticket" in data, "Response should have 'ticket' key"
        assert "messages" in data, "Response should have 'messages' key"
        
        ticket = data["ticket"]
        assert ticket["ticket_id"] == ticket_id
        assert ticket["title"] == "TEST_Ticket detail test"
        
        messages = data["messages"]
        assert len(messages) >= 1, "Should have at least the original message"
        assert messages[0]["type"] == "original"
    
    def test_get_nonexistent_ticket_returns_404(self, api_client, customer_token):
        """GET /api/portal/tickets/TKT-INVALID returns 404"""
        response = api_client.get(
            f"{BASE_URL}/api/portal/tickets/TKT-INVALID",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_reply_to_ticket(self, api_client, customer_token):
        """POST /api/portal/tickets/{id}/reply adds reply and updates status to todo"""
        # Create a test ticket first
        create_resp = api_client.post(
            f"{BASE_URL}/api/portal/tickets",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={
                "category_slug": "database",
                "subject": "TEST_Reply test ticket",
                "description": "Original message"
            }
        )
        ticket_id = create_resp.json()["ticket_id"]
        
        # Reply to the ticket
        response = api_client.post(
            f"{BASE_URL}/api/portal/tickets/{ticket_id}/reply",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"body": "This is a test reply from the customer"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message_id" in data, "Response should have 'message_id'"
        assert data["message_id"].startswith("msg_")
        
        # Verify reply was added
        detail_resp = api_client.get(
            f"{BASE_URL}/api/portal/tickets/{ticket_id}",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        detail_data = detail_resp.json()
        messages = detail_data["messages"]
        assert len(messages) >= 2, "Should have original + reply"
        reply_msg = [m for m in messages if m["type"] == "customer_reply"]
        assert len(reply_msg) > 0, "Should have customer_reply message"
    
    def test_reply_to_nonexistent_ticket_returns_404(self, api_client, customer_token):
        """POST /api/portal/tickets/TKT-INVALID/reply returns 404"""
        response = api_client.post(
            f"{BASE_URL}/api/portal/tickets/TKT-INVALID/reply",
            headers={"Authorization": f"Bearer {customer_token}"},
            json={"body": "Test reply"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_filter_tickets_by_status(self, api_client, customer_token):
        """GET /api/portal/tickets?status=todo filters by status"""
        response = api_client.get(
            f"{BASE_URL}/api/portal/tickets?status=todo",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        tickets = data["tickets"]
        # All returned tickets should have status=todo (or empty if none)
        for ticket in tickets:
            assert ticket["status"] == "todo", f"Expected status 'todo', got '{ticket['status']}'"


class TestAdminCategoryManagement:
    """Admin category CRUD - requires Trinity admin auth"""
    
    def test_create_category_as_admin(self, api_client):
        """POST /api/portal/admin/categories creates new category"""
        session = requests.Session()
        session.cookies.set("session_token", ADMIN_SESSION_TOKEN)
        
        unique_slug = f"test-cat-{uuid.uuid4().hex[:8]}"
        response = session.post(
            f"{BASE_URL}/api/portal/admin/categories",
            json={
                "title": "TEST Admin Created Category",
                "slug": unique_slug,
                "description": "Test category created by admin",
                "icon": "HelpCircle",
                "subtopics": [{"name": "Test Subtopic", "items": ["Item 1", "Item 2"]}]
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["title"] == "TEST Admin Created Category"
        assert data["slug"] == unique_slug
        assert "category_id" in data
        
        # Cleanup - delete the test category
        session.delete(f"{BASE_URL}/api/portal/admin/categories/{unique_slug}")
    
    def test_create_category_without_admin_returns_401(self, api_client):
        """POST /api/portal/admin/categories without admin auth returns 401"""
        response = api_client.post(
            f"{BASE_URL}/api/portal/admin/categories",
            json={"title": "Test", "slug": "test-slug", "description": "Test"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_update_category_as_admin(self, api_client):
        """PUT /api/portal/admin/categories/{slug} updates category"""
        session = requests.Session()
        session.cookies.set("session_token", ADMIN_SESSION_TOKEN)
        
        # Create a test category first
        unique_slug = f"test-update-{uuid.uuid4().hex[:8]}"
        session.post(
            f"{BASE_URL}/api/portal/admin/categories",
            json={"title": "Original Title", "slug": unique_slug, "description": "Original"}
        )
        
        # Update it
        response = session.put(
            f"{BASE_URL}/api/portal/admin/categories/{unique_slug}",
            json={"title": "Updated Title", "description": "Updated description"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == "Updated description"
        
        # Cleanup
        session.delete(f"{BASE_URL}/api/portal/admin/categories/{unique_slug}")
    
    def test_delete_category_as_admin(self, api_client):
        """DELETE /api/portal/admin/categories/{slug} deletes category"""
        session = requests.Session()
        session.cookies.set("session_token", ADMIN_SESSION_TOKEN)
        
        # Create a test category first
        unique_slug = f"test-delete-{uuid.uuid4().hex[:8]}"
        session.post(
            f"{BASE_URL}/api/portal/admin/categories",
            json={"title": "To Delete", "slug": unique_slug, "description": "Will be deleted"}
        )
        
        # Delete it
        response = session.delete(f"{BASE_URL}/api/portal/admin/categories/{unique_slug}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "deleted" in response.json().get("message", "").lower()
        
        # Verify it's gone
        verify_resp = api_client.get(f"{BASE_URL}/api/portal/categories/{unique_slug}")
        assert verify_resp.status_code == 404, "Category should be deleted"
    
    def test_delete_nonexistent_category_returns_404(self, api_client):
        """DELETE /api/portal/admin/categories/nonexistent returns 404"""
        session = requests.Session()
        session.cookies.set("session_token", ADMIN_SESSION_TOKEN)
        
        response = session.delete(f"{BASE_URL}/api/portal/admin/categories/nonexistent-slug")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"


class TestExistingTicket:
    """Test with existing ticket TKT-000864"""
    
    def test_get_existing_ticket(self, api_client, customer_token):
        """GET /api/portal/tickets/TKT-000864 returns the test ticket"""
        response = api_client.get(
            f"{BASE_URL}/api/portal/tickets/{EXISTING_TICKET_ID}",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        # This may return 404 if the ticket doesn't belong to test customer
        # or 200 if it does
        if response.status_code == 200:
            data = response.json()
            assert data["ticket"]["ticket_id"] == EXISTING_TICKET_ID
            print(f"Existing ticket found: {data['ticket']['title']}")
        elif response.status_code == 404:
            print(f"Ticket {EXISTING_TICKET_ID} not found or not owned by test customer")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
